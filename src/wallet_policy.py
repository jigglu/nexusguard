"""
NexusGuard – Policy-Bound Wallet & Function-Call Access Key Engine
=================================================================

Models a NEAR **Function-Call Access Key** scoped strictly to an escrow /
settlement contract plus an **OutLayer / Agent-API policy engine** that
enforces:

* Total task budget cap (default $25.00 USDC).
* Single-payout human-approval gate threshold (default $10.00 USDC).
* Explicit deny-list of privileged actions an autonomous agent cannot
  perform without human co-signature.

No raw ``FullAccess`` keys are ever used; every operation is validated
against the policy before reaching the chain adapter.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Access-Key modelling ────────────────────────────────────────────

class AccessKeyPermission(str, Enum):
    """NEAR access-key permission types."""
    FULL_ACCESS = "FullAccess"
    FUNCTION_CALL = "FunctionCall"


@dataclass(frozen=True)
class FunctionCallPermission:
    """Scoped Function-Call Access Key descriptor (NEP-standard)."""
    receiver_id: str               # e.g. "escrow.nexusguard.testnet"
    method_names: list[str]        # empty = all methods on receiver
    allowance_yocto: int | None    # optional gas allowance in yoctoNEAR

    def to_dict(self) -> dict:
        return {
            "permission": "FunctionCall",
            "receiver_id": self.receiver_id,
            "method_names": self.method_names,
            "allowance_yocto": self.allowance_yocto,
        }


# ── Policy definition ──────────────────────────────────────────────

class PolicyAction(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_HUMAN_APPROVAL = "REQUIRE_HUMAN_APPROVAL"


PRIVILEGED_METHODS = frozenset([
    "delete_account",
    "add_key",
    "delete_key",
    "deploy_contract",
    "stake",
])


class WalletPolicy(BaseModel):
    """OutLayer-style agent wallet policy."""
    budget_cap_usdc: float = Field(default=25.00, description="Maximum cumulative spend in USDC")
    single_payout_gate_usdc: float = Field(default=10.00, description="Amount above which human approval is required")
    approved_receiver_ids: list[str] = Field(default_factory=lambda: ["escrow.nexusguard.testnet"])
    denied_methods: list[str] = Field(default_factory=lambda: list(PRIVILEGED_METHODS))
    denied_recipient_addresses: list[str] = Field(default_factory=list)

    def describe_constraints(self) -> dict[str, Any]:
        """Return a human-readable summary of policy constraints."""
        return {
            "budget_cap_usdc": f"${self.budget_cap_usdc:.2f}",
            "single_payout_human_approval_above": f"${self.single_payout_gate_usdc:.2f}",
            "approved_contracts": self.approved_receiver_ids,
            "agent_CANNOT_do_without_human": [
                f"Call `{m}` on any contract" for m in sorted(self.denied_methods)
            ] + [
                f"Exceed total budget of ${self.budget_cap_usdc:.2f} USDC",
                f"Transfer funds to unapproved contracts",
            ],
        }


# ── Policy evaluation ──────────────────────────────────────────────

@dataclass
class PolicyVerdict:
    action: PolicyAction
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


# ── RPC Telemetry Cache ───────────────────────────────────────────
_RPC_CACHE: dict[str, Any] = {"result": None, "timestamp": 0.0}
_RPC_CACHE_TTL: float = 60.0


class PolicyBoundWallet:
    """
    Wraps a Function-Call Access Key with a runtime policy engine.

    Every outgoing transaction is evaluated against the policy *before*
    it is signed or broadcast.  In ``--dry-run`` mode the "broadcast"
    step is a no-op; the policy evaluation is always real.
    """

    def __init__(
        self,
        account_id: str = "nexusguard.testnet",
        escrow_contract: str = "escrow.nexusguard.testnet",
        policy: WalletPolicy | None = None,
    ):
        self.account_id = account_id
        self.escrow_contract = escrow_contract
        self.policy = policy or WalletPolicy()
        self._spent_usdc: float = 0.0
        self._audit_log: list[dict[str, Any]] = []

        # Create the scoped Function-Call Access Key (never FullAccess)
        self.access_key = FunctionCallPermission(
            receiver_id=escrow_contract,
            method_names=["release_escrow", "fund_escrow", "cancel_escrow", "get_escrow_status"],
            allowance_yocto=int(5e24),  # 5 NEAR gas allowance
        )

    # ── Public API ──────────────────────────────────────────────

    @property
    def total_spent_usdc(self) -> float:
        return self._spent_usdc

    @property
    def remaining_budget_usdc(self) -> float:
        return max(0.0, self.policy.budget_cap_usdc - self._spent_usdc)

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)

    def probe_near_testnet_rpc(self) -> dict[str, Any]:
        """
        Probe the NEAR testnet RPC to fetch live chain telemetry.

        Returns a dict with ``chain_id`` and ``latest_block_height``
        from the ``status`` method.  Falls back to a clean offline
        sentinel dict if the RPC is unreachable (CI / air-gapped
        environments).
        Results are cached for 60 seconds to avoid repetitive network overhead.
        """
        global _RPC_CACHE
        now = time.time()
        if _RPC_CACHE["result"] is not None and (now - _RPC_CACHE["timestamp"]) < _RPC_CACHE_TTL:
            return dict(_RPC_CACHE["result"])

        import requests as _requests
        RPC_URL = "https://rpc.testnet.near.org"
        payload = {
            "jsonrpc": "2.0",
            "id": "nexusguard",
            "method": "status",
            "params": [],
        }
        res: dict[str, Any]
        try:
            resp = _requests.post(RPC_URL, json=payload, timeout=5)
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                res = {
                    "rpc_reachable": True,
                    "rpc_url": RPC_URL,
                    "chain_id": result.get("chain_id", "testnet"),
                    "latest_block_height": result.get("sync_info", {}).get("latest_block_height"),
                }
            else:
                res = {
                    "rpc_reachable": False,
                    "rpc_url": RPC_URL,
                    "chain_id": "testnet",
                    "latest_block_height": None,
                }
        except Exception:  # noqa: BLE001
            res = {
                "rpc_reachable": False,
                "rpc_url": RPC_URL,
                "chain_id": "testnet",
                "latest_block_height": None,
            }

        _RPC_CACHE["result"] = res
        _RPC_CACHE["timestamp"] = now
        return dict(res)

    def get_access_key_info(self) -> dict:
        """Return the scoped access-key descriptor (never FullAccess) with live RPC telemetry."""
        rpc = self.probe_near_testnet_rpc()
        return {
            "account_id": self.account_id,
            "key_type": AccessKeyPermission.FUNCTION_CALL.value,
            "scope": self.access_key.to_dict(),
            "near_testnet_rpc": rpc,
        }

    def evaluate_transaction(
        self,
        receiver_id: str,
        method_name: str,
        amount_usdc: float,
        *,
        recipient_address: str | None = None,
    ) -> PolicyVerdict:
        """
        Evaluate a proposed transaction against the policy.
        Returns a PolicyVerdict with ALLOW / DENY / REQUIRE_HUMAN_APPROVAL.
        """
        # 1. Blocked methods
        if method_name in self.policy.denied_methods:
            verdict = PolicyVerdict(
                action=PolicyAction.DENY,
                reason=f"Method `{method_name}` is on the privileged deny-list. Human co-signature required.",
                details={"blocked_method": method_name},
            )
            self._record(receiver_id, method_name, amount_usdc, verdict)
            return verdict

        # 2. Receiver allow-list
        if receiver_id not in self.policy.approved_receiver_ids:
            verdict = PolicyVerdict(
                action=PolicyAction.DENY,
                reason=f"Receiver `{receiver_id}` is not in the approved contracts list.",
                details={"receiver_id": receiver_id, "approved": self.policy.approved_receiver_ids},
            )
            self._record(receiver_id, method_name, amount_usdc, verdict)
            return verdict

        # 3. Denied recipient addresses (cross-chain drain protection)
        if recipient_address and recipient_address in self.policy.denied_recipient_addresses:
            verdict = PolicyVerdict(
                action=PolicyAction.DENY,
                reason=f"Recipient address `{recipient_address}` is on the blocklist.",
                details={"blocked_address": recipient_address},
            )
            self._record(receiver_id, method_name, amount_usdc, verdict)
            return verdict

        # 4. Budget cap
        if self._spent_usdc + amount_usdc > self.policy.budget_cap_usdc:
            verdict = PolicyVerdict(
                action=PolicyAction.DENY,
                reason=(
                    f"Transaction of ${amount_usdc:.2f} would exceed budget cap "
                    f"(${self._spent_usdc:.2f} spent of ${self.policy.budget_cap_usdc:.2f})."
                ),
                details={
                    "requested": amount_usdc,
                    "spent": self._spent_usdc,
                    "cap": self.policy.budget_cap_usdc,
                },
            )
            self._record(receiver_id, method_name, amount_usdc, verdict)
            return verdict

        # 5. Human-approval gate
        if amount_usdc > self.policy.single_payout_gate_usdc:
            verdict = PolicyVerdict(
                action=PolicyAction.REQUIRE_HUMAN_APPROVAL,
                reason=(
                    f"Amount ${amount_usdc:.2f} exceeds the single-payout gate "
                    f"(${self.policy.single_payout_gate_usdc:.2f}). Requires human approval."
                ),
                details={"amount": amount_usdc, "gate": self.policy.single_payout_gate_usdc},
            )
            self._record(receiver_id, method_name, amount_usdc, verdict)
            return verdict

        # 6. Allowed
        verdict = PolicyVerdict(
            action=PolicyAction.ALLOW,
            reason="Transaction passes all policy checks.",
        )
        self._record(receiver_id, method_name, amount_usdc, verdict)
        return verdict

    def execute_transaction(
        self,
        receiver_id: str,
        method_name: str,
        amount_usdc: float,
        *,
        dry_run: bool = True,
        recipient_address: str | None = None,
    ) -> dict[str, Any]:
        """
        Evaluate and (in non-dry-run mode) execute a transaction.
        Returns a transaction receipt dict.
        """
        verdict = self.evaluate_transaction(
            receiver_id, method_name, amount_usdc,
            recipient_address=recipient_address,
        )

        receipt: dict[str, Any] = {
            "account_id": self.account_id,
            "receiver_id": receiver_id,
            "method_name": method_name,
            "amount_usdc": amount_usdc,
            "verdict": verdict.action.value,
            "reason": verdict.reason,
            "dry_run": dry_run,
            "tx_hash": None,
        }

        if verdict.action == PolicyAction.ALLOW:
            self._spent_usdc += amount_usdc
            if dry_run:
                receipt["tx_hash"] = self._deterministic_hash(receipt)
                receipt["status"] = "DRY_RUN_OK"
            else:
                receipt["tx_hash"] = self._deterministic_hash(receipt)
                receipt["status"] = "SIMULATED_BROADCAST"
        else:
            receipt["status"] = "BLOCKED"

        return receipt

    # ── Internals ───────────────────────────────────────────────

    def _record(
        self,
        receiver_id: str,
        method_name: str,
        amount_usdc: float,
        verdict: PolicyVerdict,
    ) -> None:
        self._audit_log.append({
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "receiver_id": receiver_id,
            "method_name": method_name,
            "amount_usdc": amount_usdc,
            "verdict": verdict.action.value,
            "reason": verdict.reason,
        })

    @staticmethod
    def _deterministic_hash(data: dict) -> str:
        payload = json.dumps(
            {k: v for k, v in sorted(data.items()) if k != "tx_hash"},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode()).hexdigest()[:16]
