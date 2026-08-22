"""
Runs every scenario in scenarios.json through CheckoutAgent (dry_run mode,
no real API keys needed) and writes RESULTS.md with pass/fail + audit
trail stats, in the same spirit as the agent-harness-benchmark RESULTS.md.

Run: python eval/run_eval.py
"""

import sys
import os
import json
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent.core import CheckoutAgent, SessionState
from agent.audit import clear_log, read_log

SCENARIOS_PATH = os.path.join(os.path.dirname(__file__), "scenarios.json")
RESULTS_PATH = os.path.join(os.path.dirname(__file__), "..", "RESULTS.md")


def run_scenario(agent, scenario):
    state = SessionState()
    responses = []
    start = time.time()
    for turn in scenario["turns"]:
        reply, state = agent.handle_message(turn, state)
        responses.append({"user": turn, "agent": reply})
    elapsed = time.time() - start

    passed = state.stage == scenario["expected_stage"]
    return {
        "id": scenario["id"],
        "description": scenario["description"],
        "expected_stage": scenario["expected_stage"],
        "actual_stage": state.stage,
        "passed": passed,
        "turns": len(scenario["turns"]),
        "elapsed_sec": round(elapsed, 4),
        "responses": responses,
    }


def main():
    clear_log()
    with open(SCENARIOS_PATH) as f:
        scenarios = json.load(f)

    agent = CheckoutAgent(razorpay_client=None, dry_run=True)

    results = [run_scenario(agent, s) for s in scenarios]
    audit_events = read_log()

    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)

    lines = []
    lines.append("# Eval Results — Checkout Mandate Agent\n")
    lines.append(f"**Pass rate: {passed_count}/{total}**\n")
    lines.append("Run mode: dry-run (no live Razorpay/Groq calls — LLM extraction "
                  "falls back to rule-based parsing when GROQ_API_KEY is unset).\n")
    lines.append("| Scenario | Description | Expected | Actual | Result | Turns | Time (s) |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        mark = "PASS" if r["passed"] else "FAIL"
        lines.append(
            f"| {r['id']} | {r['description']} | {r['expected_stage']} | "
            f"{r['actual_stage']} | {mark} | {r['turns']} | {r['elapsed_sec']} |"
        )

    lines.append("\n## Audit trail summary\n")
    lines.append(f"Total logged events across all scenarios: **{len(audit_events)}**\n")
    stage_counts = {}
    for e in audit_events:
        stage_counts[e["stage"]] = stage_counts.get(e["stage"], 0) + 1
    lines.append("| Stage | Event count |")
    lines.append("|---|---|")
    for stage, count in sorted(stage_counts.items()):
        lines.append(f"| {stage} | {count} |")

    lines.append("\n## Per-scenario transcripts\n")
    for r in results:
        lines.append(f"### {r['id']} — {'PASS' if r['passed'] else 'FAIL'}")
        lines.append(f"_{r['description']}_\n")
        for turn in r["responses"]:
            lines.append(f"- **User:** {turn['user']}")
            lines.append(f"  **Agent:** {turn['agent']}")
        lines.append("")

        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    print(f"Pass rate: {passed_count}/{total}")
    print(f"Full results written to {RESULTS_PATH}")
    if passed_count < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
