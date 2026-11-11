#!/usr/bin/env python3
"""
NexusGuard CLI – Rich terminal runner.

Usage
-----
    python main.py --dry-run           # Full pipeline (no real funds)
    python main.py --attack-demo       # Prompt-injection attack simulation
    python main.py --dry-run --attack-demo  # Both
"""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import argparse
import json
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from src.crew_studio import DEFAULT_SPEC

console = Console()


def _banner() -> None:
    console.print(
        Panel(
            Text.from_markup(
                "[bold cyan]NexusGuard[/bold cyan]\n"
                "[dim]Autonomous General-Contractor Studio, Security Swarm\n"
                "& Cross-Chain Bounty Protocol on NEAR[/dim]"
            ),
            title="🛡️  NexusGuard v1.0",
            border_style="cyan",
            expand=False,
        )
    )


def _print_policy(result: dict) -> None:
    wp = result.get("wallet_policy", {})
    constraints = wp.get("constraints", {})

    console.print("\n[bold green]━━━ Policy-Bound Wallet ━━━[/bold green]")
    ak = wp.get("access_key", {})
    console.print(f"  Account:    {ak.get('account_id', 'N/A')}")
    console.print(f"  Key Type:   {ak.get('key_type', 'N/A')} (never FullAccess)")
    scope = ak.get("scope", {})
    console.print(f"  Receiver:   {scope.get('receiver_id', 'N/A')}")
    console.print(f"  Methods:    {scope.get('method_names', [])}")

    console.print(f"\n  Budget Cap:         {constraints.get('budget_cap_usdc', 'N/A')}")
    console.print(f"  Human-Approval Gate: {constraints.get('single_payout_human_approval_above', 'N/A')}")

    cannot = constraints.get("agent_CANNOT_do_without_human", [])
    console.print("\n  [bold red]Agent CANNOT do without human:[/bold red]")
    for c in cannot:
        console.print(f"    ✗ {c}")


def _print_decomposition(result: dict) -> None:
    dec = result.get("decomposition", {})
    console.print(f"\n[bold green]━━━ Task Decomposition ({dec.get('decomposition_mode', '?')}) ━━━[/bold green]")

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Task", style="cyan")
    table.add_column("Strategy", style="yellow")
    table.add_column("Assigned To", style="magenta")
    table.add_column("Budget", justify="right", style="green")
    table.add_column("Status", style="white")

    for t in dec.get("tasks", []):
        table.add_row(
            t["task_id"],
            t["strategy"],
            t["assigned_to"],
            f"${t['budget_usdc']:.2f}",
            t["status"],
        )
    console.print(table)


def _print_negotiations(result: dict) -> None:
    negs = result.get("negotiations", [])
    console.print("\n[bold green]━━━ 1-Round Counter-Offer Negotiations ━━━[/bold green]")

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Task", style="cyan")
    table.add_column("Provider", style="magenta")
    table.add_column("Initial Quote", justify="right")
    table.add_column("Final Price", justify="right")
    table.add_column("Outcome", style="bold")

    for n in negs:
        outcome = n["outcome"]
        if outcome == "ACCEPTED_INITIAL":
            style = "green"
        elif outcome == "ACCEPTED_COUNTER":
            style = "yellow"
        else:
            style = "red"

        final = f"${n['final_price']:.2f}" if n["final_price"] is not None else "—"
        table.add_row(
            n["subtask_id"],
            n["provider_id"],
            f"${n['initial_quote']:.2f}",
            final,
            f"[{style}]{outcome}[/{style}]",
        )
    console.print(table)

    for n in negs:
        console.print(f"  📋 {n['summary']}")


def _print_settlements(result: dict) -> None:
    setts = result.get("settlements", [])
    console.print("\n[bold green]━━━ Cross-Chain Settlements (NEAR Intents dry=true) ━━━[/bold green]")

    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("Receipt ID", style="cyan")
    table.add_column("Task", style="yellow")
    table.add_column("From", style="magenta")
    table.add_column("Chain", style="blue")
    table.add_column("Amount", justify="right", style="green")
    table.add_column("Verified", style="white")

    for s in setts:
        table.add_row(
            s["receipt_id"],
            s["task_id"],
            s["bought_from"],
            s["recipient_chain"],
            f"${s['price_usdc']:.2f}",
            "✅" if s["verification_passed"] else "❌",
        )
    console.print(table)


def _print_attack_demo(demo: dict) -> None:
    console.print("\n[bold red]━━━ 🚨 ATTACK SIMULATION 🚨 ━━━[/bold red]")
    scenario = demo.get("attack_scenario", {})
    console.print(f"  Attacker:       {scenario.get('attacker', 'N/A')}")
    console.print(f"  Attack Vector:  {scenario.get('attack_vector', 'N/A')}")
    console.print(f"  Target Amount:  ${scenario.get('target_amount_usdc', 0):.2f} USDC")
    console.print(f"  Target Address: {scenario.get('target_address', 'N/A')}")

    attack = demo.get("attack_result", {})
    console.print(f"\n  [bold]Blocked: {'✅ YES' if attack.get('blocked') else '❌ NO'}[/bold]")

    risk = attack.get("risk_report", {})
    console.print(f"  Risk Level:   [bold red]{risk.get('overall_risk', 'N/A')}[/bold red]")
    signals = risk.get("signals", [])
    for sig in signals:
        console.print(f"    ⚠️  [{sig['severity']}] {sig['description']}")

    incident = attack.get("incident_receipt")
    if incident:
        console.print(f"\n  [bold]Cryptographic Incident Receipt:[/bold]")
        console.print(f"    Incident ID:  {incident['incident_id']}")
        console.print(f"    Threat Type:  {incident['threat_type']}")
        console.print(f"    Receipt Hash: {incident['receipt_hash'][:32]}...")

    # Legitimate comparison
    legit = demo.get("legitimate_comparison", {})
    console.print(f"\n  [bold green]Legitimate Transaction Comparison:[/bold green]")
    console.print(f"    Agent: trusted-builder.near")
    console.print(f"    Blocked: {'Yes' if legit.get('blocked') else '✅ No — allowed through'}")

    console.print(f"\n  Total incidents blocked: {demo.get('total_incidents_blocked', 0)}")


def _print_delivered_output(result: dict) -> None:
    output = result.get("delivered_output")
    if not output:
        return
    console.print("\n[bold green]━━━ 📦 Final Delivered Output ━━━[/bold green]")
    console.print(f"  [bold cyan]Project:[/bold cyan]       {output.get('project_title')}")
    console.print(f"  [bold]Budget Cap:[/bold]    ${output.get('total_budget_usdc', 0):.2f} USDC")
    console.print(f"  [bold green]Total Spent:[/bold green]   ${output.get('total_spent_usdc', 0):.2f} USDC")
    console.print(f"  [bold yellow]Net Savings:[/bold yellow]   ${output.get('savings_usdc', 0):.2f} USDC")
    console.print(f"\n  [dim]{output.get('architecture_summary')}[/dim]\n")

    for art in output.get("deliverable_artifacts", []):
        preview = art.get("artifact_preview") or ""
        console.print(Panel(
            Text(preview or "Artifact verified.", style="cyan"),
            title=f"Deliverable: {art.get('task_id')} — {art.get('title')}",
            subtitle=f"Hash: {art.get('deliverable_hash', '')[:16]} │ Status: {art.get('status')}",
            border_style="green",
            expand=False,
        ))


def run_pipeline(spec: str = DEFAULT_SPEC, budget: float = 25.0) -> dict:
    """Run the full NexusGuard pipeline."""
    from src.pipeline import NexusGuardPipeline
    pipeline = NexusGuardPipeline(specification=spec, budget_cap_usdc=budget)
    return pipeline.run()


def run_attack() -> dict:
    """Run the attack demo."""
    from src.security_swarm import run_attack_demo
    return run_attack_demo()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="NexusGuard: Autonomous General-Contractor Studio on NEAR",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode (no real funds; default: True)",
    )
    parser.add_argument(
        "--attack-demo",
        action="store_true",
        help="Run the prompt-injection & malicious drain attack simulation",
    )
    parser.add_argument(
        "--spec",
        type=str,
        default=DEFAULT_SPEC,
        help="Custom task specification for the Manager AI",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=25.0,
        help="Total budget cap in USDC (default: 25.0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of Rich formatted output",
    )
    args = parser.parse_args()

    if args.json:
        output: dict = {}
        if args.dry_run:
            output["pipeline"] = run_pipeline(spec=args.spec, budget=args.budget)
        if args.attack_demo:
            output["attack_demo"] = run_attack()
        print(json.dumps(output, indent=2))
        return

    _banner()

    if args.dry_run:
        console.print("\n[bold]Running full pipeline in dry-run mode...[/bold]\n")
        result = run_pipeline(spec=args.spec, budget=args.budget)
        _print_policy(result)
        _print_decomposition(result)
        _print_negotiations(result)
        _print_settlements(result)
        _print_delivered_output(result)
        console.print(f"\n  📄 Receipts:  {result['exports']['receipts_json']}")
        console.print(f"  📊 Ledger:    {result['exports']['accounting_ledger_csv']}")

    if args.attack_demo:
        demo = run_attack()
        _print_attack_demo(demo)

    console.print("\n[bold green]✅ NexusGuard pipeline completed successfully.[/bold green]\n")


if __name__ == "__main__":
    main()
