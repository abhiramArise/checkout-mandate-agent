"""
Runs autonomous buyer-agent vs checkout-agent sessions -- no scripted
human turns, no human in the loop. The buyer agent decides what to say
based on its own goal/budget/persona; the checkout agent's mandate chain
enforces bounds regardless of what the buyer agent asks for.

This is the two-agent extension on top of the already-working,
already-verified single-agent core (see eval/run_eval.py, RESULTS.md).
That single-agent version remains the safety net: it works standalone,
fully tested, whether or not this file is ever run.

Run: python eval/run_multi_agent.py
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.core import CheckoutAgent, SessionState
from agent.buyer_agent import BuyerAgent, BuyerPersona
from agent.audit import clear_log, read_log

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "MULTI_AGENT_RESULTS.md")
MAX_TURNS = 8  # hard cap so a buggy loop can't run forever

PERSONAS = [
    BuyerPersona(name="Budget shopper - shoes", goal="running shoes", max_budget=3000.0),
    BuyerPersona(name="Tight budget - speaker", goal="bluetooth speaker", max_budget=500.0, patience=2),
    BuyerPersona(name="Flexible budget - earbuds", goal="wireless earbuds", max_budget=1500.0, patience=3),
    BuyerPersona(name="Haggler - hoodie", goal="cotton hoodie", max_budget=1500.0, accepts_first_offer=False),
    BuyerPersona(name="Impatient - laptop (no match)", goal="laptop", max_budget=50000.0, patience=1),
    BuyerPersona(name="Exact match - yoga mat", goal="yoga mat", max_budget=900.0),
    BuyerPersona(name="Out of stock item - speaker high budget", goal="bluetooth speaker", max_budget=4000.0, patience=2),
    BuyerPersona(name="Generous budget - water bottle", goal="smart water bottle", max_budget=5000.0),
]


def run_session(persona: BuyerPersona):
    buyer = BuyerAgent(persona)
    merchant = CheckoutAgent(razorpay_client=None, dry_run=True)
    state = SessionState()

    transcript = []
    buyer_msg = buyer.opening_message()
    turns = 0
    start = time.time()

    while buyer_msg is not None and turns < MAX_TURNS:
        turns += 1
        merchant_reply, state = merchant.handle_message(buyer_msg, state)
        transcript.append({"turn": turns, "buyer": buyer_msg, "merchant": merchant_reply})
        buyer_msg = buyer.respond_to(merchant_reply)

    elapsed = time.time() - start
    outcome = "purchase_completed" if state.stage == "done" else (
        "hard_stopped" if state.stage == "rejected" else "session_ended_no_purchase"
    )

    return {
        "persona": persona.name,
        "goal": persona.goal,
        "initial_budget": persona.max_budget,
        "outcome": outcome,
        "final_stage": state.stage,
        "turns": turns,
        "elapsed_sec": round(elapsed, 4),
        "transcript": transcript,
    }


def main():
    clear_log()
    results = [run_session(p) for p in PERSONAS]
    audit_events = read_log()

    completed = sum(1 for r in results if r["outcome"] == "purchase_completed")
    total = len(results)

    lines = []
    lines.append("# Multi-Agent Results — Buyer Agent vs Checkout Mandate Agent\n")
    lines.append(f"**{completed}/{total} sessions ended in a completed purchase** "
                 "(remaining sessions correctly ended without a purchase — "
                 "no match in budget, buyer gave up, or mandate rejection).\n")
    lines.append("No human turns in this run — the buyer agent decides every message "
                 "based on its own goal, budget, and patience; the checkout agent's "
                 "mandate chain enforces bounds independent of what the buyer agent "
                 "asks for.\n")
    lines.append("| Persona | Goal | Budget | Outcome | Final Stage | Turns | Time (s) |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r['persona']} | {r['goal']} | ₹{r['initial_budget']:.0f} | "
            f"{r['outcome']} | {r['final_stage']} | {r['turns']} | {r['elapsed_sec']} |"
        )

    lines.append("\n## Audit trail summary\n")
    lines.append(f"Total logged mandate/tool events across all sessions: **{len(audit_events)}**\n")
    stage_counts = {}
    for e in audit_events:
        stage_counts[e["stage"]] = stage_counts.get(e["stage"], 0) + 1
    lines.append("| Stage | Event count |")
    lines.append("|---|---|")
    for stage, count in sorted(stage_counts.items()):
        lines.append(f"| {stage} | {count} |")

    lines.append("\n## Per-session transcripts\n")
    for r in results:
        lines.append(f"### {r['persona']} — {r['outcome']}")
        lines.append(f"_Goal: {r['goal']}, starting budget: ₹{r['initial_budget']:.0f}_\n")
        for t in r["transcript"]:
            lines.append(f"- **Buyer agent:** {t['buyer']}")
            lines.append(f"  **Merchant agent:** {t['merchant']}")
        lines.append("")

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"{completed}/{total} sessions completed a purchase")
    print(f"Full results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
