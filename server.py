#!/usr/bin/env python3
"""
NexusGuard – FastAPI Backend & Mission Control UI Server.

Usage
-----
    python server.py                   # Start on http://localhost:8000
    uvicorn server:app --reload        # Development mode

Endpoints
---------
    GET  /                  → Mission Control Dashboard (Tailwind UI)
    GET  /api/health        → Health check
    POST /api/pipeline/run  → Execute full pipeline (dry-run)
    POST /api/attack/demo   → Run attack simulation
    GET  /api/policy        → Get wallet policy constraints
    GET  /api/disclosure    → Agent market architectural disclosure
    GET  /api/receipts      → Get settlement receipts
"""

from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.crew_studio import DEFAULT_SPEC, CrewStudio
from src.integrations.agent_market import LocalBidSimulator
from src.integrations.near_intents import NearIntentsAdapter
from src.negotiation import run_demo_negotiations
from src.pipeline import NexusGuardPipeline
from src.security_swarm import SecuritySwarm, run_attack_demo
from src.wallet_policy import PolicyBoundWallet, WalletPolicy

app = FastAPI(
    title="NexusGuard API",
    description="Autonomous General-Contractor Studio, Security Swarm & Cross-Chain Bounty Protocol on NEAR",
    version="1.0.0",
)


@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    """Debug 404 handler that reveals the exact ASGI path and query received."""
    return JSONResponse(
        status_code=404,
        content={
            "detail": "Not Found",
            "scope_path": request.scope.get("path"),
            "scope_query": request.scope.get("query_string", b"").decode("utf-8"),
            "x_matched_path": request.headers.get("x-matched-path"),
            "x_invoke_path": request.headers.get("x-invoke-path"),
        },
    )


class PipelineRunRequest(BaseModel):
    specification: str = DEFAULT_SPEC
    budget_usdc: float = 25.00

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── State ───────────────────────────────────────────────────────────

_pipeline_result: dict | None = None


# ── Routes ──────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def landing():
    """Serve the public Web3 startup landing page."""
    no_cache = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    landing_path = static_dir / "landing.html"
    if landing_path.exists():
        return HTMLResponse(content=landing_path.read_text(), headers=no_cache)
    # Fallback to index.html if landing.html is not found
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(), headers=no_cache)
    return HTMLResponse(content="<h1>NexusGuard</h1><p>static files not found</p>", headers=no_cache)


@app.get("/app", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
@app.get("/console", response_class=HTMLResponse)
async def mission_control():
    """Serve the Mission Control operational dashboard."""
    no_cache = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache", "Expires": "0"}
    index_path = static_dir / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(), headers=no_cache)
    return HTMLResponse(content="<h1>NexusGuard Mission Control</h1><p>static/index.html not found</p>", headers=no_cache)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "NexusGuard", "version": "1.0.0"}


@app.post("/api/pipeline/run")
async def run_pipeline(req: Optional[PipelineRunRequest] = None):
    """Execute the full NexusGuard pipeline in dry-run mode."""
    global _pipeline_result
    if req is None:
        req = PipelineRunRequest()
    pipeline = NexusGuardPipeline(
        specification=req.specification,
        budget_cap_usdc=req.budget_usdc,
    )
    _pipeline_result = pipeline.run()
    return JSONResponse(content=_pipeline_result)


@app.post("/api/attack/demo")
async def attack_demo():
    """Run the prompt-injection & malicious drain attack simulation."""
    result = run_attack_demo()
    return JSONResponse(content=result)


@app.get("/api/policy")
async def get_policy():
    """Return wallet policy constraints."""
    wallet = PolicyBoundWallet(
        policy=WalletPolicy(budget_cap_usdc=25.00, single_payout_gate_usdc=10.00),
    )
    return {
        "access_key": wallet.get_access_key_info(),
        "constraints": wallet.policy.describe_constraints(),
    }


@app.get("/api/disclosure")
async def get_disclosure():
    """Return agent market architectural disclosure."""
    sim = LocalBidSimulator()
    return sim.get_disclosure()


@app.get("/api/receipts")
async def get_receipts():
    """Return settlement receipts from the last pipeline run."""
    if _pipeline_result and "settlements" in _pipeline_result:
        return {"receipts": _pipeline_result["settlements"]}
    return {"receipts": [], "note": "Run the pipeline first via POST /api/pipeline/run"}


@app.get("/api/negotiations")
async def get_negotiations():
    """Return negotiation demo results."""
    results = run_demo_negotiations()
    return {
        "negotiations": [
            {
                "subtask_id": n.subtask_id,
                "provider_id": n.provider_id,
                "outcome": n.outcome.value,
                "initial_quote": n.initial_quote_usdc,
                "final_price": n.final_price_usdc,
                "counter_offer": n.counter_offer_usdc,
                "summary": n.negotiation_summary,
                "reasoning": n.reasoning,
            }
            for n in results
        ]
    }


@app.get("/api/ledger.csv")
async def download_ledger():
    """Serve accounting_ledger.csv as a downloadable file."""
    ledger_path = Path(__file__).parent / "accounting_ledger.csv"
    # If ledger doesn't exist yet, run the pipeline first
    if not ledger_path.exists():
        pipeline = NexusGuardPipeline()
        pipeline.run()
    return FileResponse(
        path=str(ledger_path),
        media_type="text/csv",
        filename="nexusguard_accounting_ledger.csv",
    )


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
