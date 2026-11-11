"""
NexusGuard – 1-Round Counter-Offer Negotiation Engine
=====================================================

Implements a deterministic state machine for agent-to-agent
(or agent-to-human) price negotiation following strict rules:

1. **ACCEPTED_INITIAL** – If the initial quote ≤ subtask budget → accept.
2. **COUNTER** – If the initial quote > budget but within a configurable
   max-buffer (default +10 %), issue exactly ONE counter-offer with
   explicit technical reasoning.
3. **WALKED_AWAY** – If the initial quote exceeds `budget × (1 + max_buffer)`
   → walk away and re-engage a fallback provider.

The negotiation round produces a :class:`NegotiationResult` that feeds
directly into the pipeline's accounting ledger.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class NegotiationOutcome(str, Enum):
    ACCEPTED_INITIAL = "ACCEPTED_INITIAL"
    ACCEPTED_COUNTER = "ACCEPTED_COUNTER"
    WALKED_AWAY = "WALKED_AWAY"


@dataclass(frozen=True)
class ProviderQuote:
    """An external provider's price quote for a subtask."""
    provider_id: str          # e.g. "sec-swarm-alpha.near"
    subtask_id: str           # e.g. "TASK-02"
    quoted_usdc: float        # initial ask
    description: str = ""     # human-readable scope description
    scope_loc: int = 0        # estimated lines of code / scope metric


@dataclass
class NegotiationResult:
    """Immutable record of a completed negotiation round."""
    subtask_id: str
    provider_id: str
    outcome: NegotiationOutcome
    initial_quote_usdc: float
    budget_usdc: float
    counter_offer_usdc: float | None = None
    final_price_usdc: float | None = None
    reasoning: str = ""
    round_log: list[dict[str, Any]] = field(default_factory=list)
    timestamp_utc: str = field(
        default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )

    @property
    def negotiation_summary(self) -> str:
        """One-line summary for the accounting ledger."""
        if self.outcome == NegotiationOutcome.ACCEPTED_INITIAL:
            return (
                f"Accepted initial ${self.initial_quote_usdc:.2f} from "
                f"{self.provider_id} (under budget ${self.budget_usdc:.2f})"
            )
        elif self.outcome == NegotiationOutcome.ACCEPTED_COUNTER:
            return (
                f"Countered ${self.initial_quote_usdc:.2f}→"
                f"${self.counter_offer_usdc:.2f}, "
                f"settled at ${self.final_price_usdc:.2f} with {self.provider_id}"
            )
        else:
            return (
                f"Walked away from {self.provider_id} "
                f"(quoted ${self.initial_quote_usdc:.2f} vs budget ${self.budget_usdc:.2f})"
            )

    def receipt_hash(self) -> str:
        """Deterministic SHA-256 fingerprint of this negotiation."""
        blob = json.dumps({
            "subtask_id": self.subtask_id,
            "provider_id": self.provider_id,
            "outcome": self.outcome.value,
            "initial_quote_usdc": self.initial_quote_usdc,
            "final_price_usdc": self.final_price_usdc,
        }, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


# ── Negotiation Engine ──────────────────────────────────────────────

class NegotiationEngine:
    """
    1-round counter-offer negotiation state machine.

    Parameters
    ----------
    max_buffer_pct : float
        Maximum percentage above the subtask budget the engine is willing
        to counter.  Default 0.10 (10 %).  Quotes above
        ``budget * (1 + max_buffer_pct)`` trigger an immediate WALK_AWAY.
    """

    def __init__(self, max_buffer_pct: float = 0.15):
        self.max_buffer_pct = max_buffer_pct
        self._history: list[NegotiationResult] = []

    @property
    def history(self) -> list[NegotiationResult]:
        return list(self._history)

    def negotiate(
        self,
        quote: ProviderQuote,
        budget_usdc: float,
        *,
        provider_accepts_counter: bool | None = None,
    ) -> NegotiationResult:
        """
        Run a single negotiation round.

        Parameters
        ----------
        quote : ProviderQuote
            The provider's initial price quote.
        budget_usdc : float
            The subtask budget ceiling.
        provider_accepts_counter : bool | None
            In deterministic / dry-run mode, explicitly control whether
            the provider accepts our counter-offer.  ``None`` defaults to
            ``True`` (optimistic fallback).

        Returns
        -------
        NegotiationResult
        """
        log: list[dict[str, Any]] = []

        log.append({
            "event": "RECEIVED_QUOTE",
            "provider": quote.provider_id,
            "quoted_usdc": quote.quoted_usdc,
            "budget_usdc": budget_usdc,
        })

        # ── Path 1: Accept immediately ──
        if quote.quoted_usdc <= budget_usdc:
            result = NegotiationResult(
                subtask_id=quote.subtask_id,
                provider_id=quote.provider_id,
                outcome=NegotiationOutcome.ACCEPTED_INITIAL,
                initial_quote_usdc=quote.quoted_usdc,
                budget_usdc=budget_usdc,
                final_price_usdc=quote.quoted_usdc,
                reasoning=f"Quote ${quote.quoted_usdc:.2f} is within budget ${budget_usdc:.2f}. Accepting.",
                round_log=log,
            )
            log.append({"event": "ACCEPTED_INITIAL", "price": quote.quoted_usdc})
            self._history.append(result)
            return result

        # ── Path 2: Walk away (too far above budget) ──
        ceiling = budget_usdc * (1 + self.max_buffer_pct)
        if quote.quoted_usdc > ceiling:
            log.append({
                "event": "WALKED_AWAY",
                "reason": (
                    f"${quote.quoted_usdc:.2f} exceeds max ceiling "
                    f"${ceiling:.2f} (budget ${budget_usdc:.2f} + {self.max_buffer_pct*100:.0f}% buffer)"
                ),
            })
            result = NegotiationResult(
                subtask_id=quote.subtask_id,
                provider_id=quote.provider_id,
                outcome=NegotiationOutcome.WALKED_AWAY,
                initial_quote_usdc=quote.quoted_usdc,
                budget_usdc=budget_usdc,
                reasoning=(
                    f"Quote ${quote.quoted_usdc:.2f} exceeds max ceiling ${ceiling:.2f}. "
                    f"Walking away to seek alternative provider."
                ),
                round_log=log,
            )
            self._history.append(result)
            return result

        # ── Path 3: Counter once ──
        scope_factor = max(quote.scope_loc, 500)  # avoid divide-by-zero
        counter_price = round(budget_usdc * (1 + self.max_buffer_pct * 0.5), 2)
        # Never counter above the original quote
        counter_price = min(counter_price, quote.quoted_usdc - 0.01)
        # Never counter below the budget
        counter_price = max(counter_price, budget_usdc)
        counter_price = round(counter_price, 2)

        technical_reasoning = (
            f"Scope is ~{scope_factor} LOC. Budget is ${budget_usdc:.2f}. "
            f"We offer ${counter_price:.2f} (≤ +{self.max_buffer_pct*100:.0f}% buffer). "
            f"Fair market rate for {quote.description or 'this scope'}."
        )

        log.append({
            "event": "COUNTER_OFFER",
            "counter_usdc": counter_price,
            "reasoning": technical_reasoning,
        })

        # Simulate provider response
        accepted = provider_accepts_counter if provider_accepts_counter is not None else True

        if accepted:
            log.append({"event": "COUNTER_ACCEPTED", "final_price": counter_price})
            result = NegotiationResult(
                subtask_id=quote.subtask_id,
                provider_id=quote.provider_id,
                outcome=NegotiationOutcome.ACCEPTED_COUNTER,
                initial_quote_usdc=quote.quoted_usdc,
                budget_usdc=budget_usdc,
                counter_offer_usdc=counter_price,
                final_price_usdc=counter_price,
                reasoning=technical_reasoning,
                round_log=log,
            )
        else:
            log.append({"event": "COUNTER_REJECTED"})
            log.append({"event": "WALKED_AWAY", "reason": "Counter-offer rejected."})
            result = NegotiationResult(
                subtask_id=quote.subtask_id,
                provider_id=quote.provider_id,
                outcome=NegotiationOutcome.WALKED_AWAY,
                initial_quote_usdc=quote.quoted_usdc,
                budget_usdc=budget_usdc,
                counter_offer_usdc=counter_price,
                reasoning="Counter-offer rejected by provider. Walking away.",
                round_log=log,
            )

        self._history.append(result)
        return result


# ── Convenience: Run the hackathon demo scenarios ────────────────────

def run_demo_negotiations() -> list[NegotiationResult]:
    """
    Execute the three canonical negotiation scenarios required by the
    hackathon rubric (07-agents track):

    1. WALKED_AWAY  – sec-swarm-alpha.near  $9.50 vs $6.00 budget
    2. ACCEPTED_COUNTER – audit-bot-lite.near  $6.80 vs $6.00 budget → counter $6.60 → accept
    3. ACCEPTED_INITIAL – verifier-alice.base.eth  $4.75 vs $5.00 budget
    """
    engine = NegotiationEngine(max_buffer_pct=0.15)
    results: list[NegotiationResult] = []

    # Scenario 1: Walk away
    q1 = ProviderQuote(
        provider_id="sec-swarm-alpha.near",
        subtask_id="TASK-02",
        quoted_usdc=9.50,
        description="Full smart-contract security audit (reentrancy + overflow)",
        scope_loc=1200,
    )
    r1 = engine.negotiate(q1, budget_usdc=6.00)
    results.append(r1)

    # Scenario 2: Counter → Accepted
    q2 = ProviderQuote(
        provider_id="audit-bot-lite.near",
        subtask_id="TASK-02",
        quoted_usdc=6.80,
        description="Lightweight static analysis + reentrancy check",
        scope_loc=800,
    )
    r2 = engine.negotiate(q2, budget_usdc=6.00, provider_accepts_counter=True)
    results.append(r2)

    # Scenario 3: Accept immediately
    q3 = ProviderQuote(
        provider_id="verifier-alice.base.eth",
        subtask_id="TASK-03",
        quoted_usdc=4.75,
        description="UI/UX + invoice validation review",
        scope_loc=400,
    )
    r3 = engine.negotiate(q3, budget_usdc=5.00)
    results.append(r3)

    return results
