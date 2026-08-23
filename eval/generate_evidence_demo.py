"""
Runs one real checkout conversation, then generates a dispute evidence
package from it -- proof the evidence generator works against actual
session data, not a hand-crafted example.

Run: python eval/generate_evidence_demo.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from agent.core import CheckoutAgent, SessionState
from agent.audit import clear_log
from agent.evidence import build_evidence_package, format_evidence_report

EVIDENCE_PATH = os.path.join(os.path.dirname(__file__), "..", "EVIDENCE_SAMPLE.md")


def main():
    clear_log()
    agent = CheckoutAgent(dry_run=True)  # dry-run: no live keys needed to prove this works
    state = SessionState()

    reply, state = agent.handle_message("running shoes under 3000", state)
    print(f"[User]     running shoes under 3000")
    print(f"[Agent]    {reply}\n")

    reply, state = agent.handle_message("yes", state)
    print(f"[User]     yes")
    print(f"[Agent]    {reply}\n")

    package = build_evidence_package(state.session_id)
    report = format_evidence_report(package)

    print("=" * 60)
    print(report)
    print("=" * 60)

    with open(EVIDENCE_PATH, "w", encoding="utf-8") as f:
        f.write("# Sample dispute evidence package\n\n```\n" + report + "\n```\n")

    print(f"\nWritten to {EVIDENCE_PATH}")


if __name__ == "__main__":
    main()