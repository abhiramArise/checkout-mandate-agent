"""
Live demo: watch the buyer agent and the checkout (merchant) agent
transact in real time, with real Groq LLM understanding on the merchant
side. Built for recording the pitch video -- paced output, clear
speaker labels, and an audit-trail summary at the end.

Usage:
    python demo_live.py                       # pick a persona interactively
    python demo_live.py --persona 1            # run persona #1 directly
    python demo_live.py --persona 1 --live     # use REAL Razorpay (not dry-run)
    python demo_live.py --persona 1 --fast     # skip the pacing delay

Requires GROQ_API_KEY in .env for real LLM understanding (falls back to
the rule-based mock parser otherwise, clearly labeled below).
Requires RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in .env only if --live is used.
"""

import argparse
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

from agent.core import CheckoutAgent, SessionState
from agent.buyer_agent import BuyerAgent, BuyerPersona
from agent.audit import clear_log, read_log
from tools.razorpay_client import RazorpayClient

PERSONAS = [
    BuyerPersona(name="Budget shopper - running shoes", goal="running shoes", max_budget=3000.0),
    BuyerPersona(name="Tight budget - bluetooth speaker (will fail, out of stock)", goal="bluetooth speaker", max_budget=4000.0, patience=2),
    BuyerPersona(name="Haggler - hoodie", goal="cotton hoodie", max_budget=1500.0, accepts_first_offer=False),
    BuyerPersona(name="Impossible request - laptop (correctly finds nothing)", goal="laptop", max_budget=50000.0, patience=1),
    BuyerPersona(name="Generous budget - water bottle", goal="smart water bottle", max_budget=5000.0),
]

MAX_TURNS = 8


def banner(text):
    line = "=" * 70
    print(f"\n{line}\n{text}\n{line}\n")


def pace(seconds, fast):
    if not fast:
        time.sleep(seconds)


def choose_persona(args):
    if args.persona is not None:
        idx = args.persona - 1
        if 0 <= idx < len(PERSONAS):
            return PERSONAS[idx]
        print(f"No persona #{args.persona}. Valid range: 1-{len(PERSONAS)}.")
        sys.exit(1)

    print("Choose a buyer persona:\n")
    for i, p in enumerate(PERSONAS, 1):
        print(f"  {i}. {p.name}  (goal: '{p.goal}', budget: Rs.{p.max_budget:.0f})")
    choice = input(f"\nEnter 1-{len(PERSONAS)}: ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(PERSONAS):
            return PERSONAS[idx]
    except ValueError:
        pass
    print("Invalid choice.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Live buyer-agent vs merchant-agent demo")
    parser.add_argument("--persona", type=int, help="Persona number (skip interactive prompt)")
    parser.add_argument("--live", action="store_true", help="Use REAL Razorpay test-mode calls (not dry-run)")
    parser.add_argument("--fast", action="store_true", help="Skip pacing delays")
    args = parser.parse_args()

    persona = choose_persona(args)

    llm_mode = "REAL Groq LLM" if os.environ.get("GROQ_API_KEY") else "mock parser (no GROQ_API_KEY set)"
    payment_mode = "REAL Razorpay test-mode" if args.live else "dry-run (simulated)"

    banner("CHECKOUT MANDATE AGENT — live buyer vs merchant demo")
    print(f"Persona:       {persona.name}")
    print(f"Goal:          {persona.goal}")
    print(f"Budget:        Rs.{persona.max_budget:.0f}")
    print(f"LLM mode:      {llm_mode}")
    print(f"Payment mode:  {payment_mode}")
    pace(2, args.fast)

    razorpay_client = RazorpayClient() if args.live else None
    merchant = CheckoutAgent(razorpay_client=razorpay_client, dry_run=not args.live)
    buyer = BuyerAgent(persona)
    state = SessionState()

    clear_log()

    buyer_msg = buyer.opening_message()
    turns = 0

    banner("CONVERSATION")

    while buyer_msg is not None and turns < MAX_TURNS:
        turns += 1
        print(f"[Buyer Agent]     {buyer_msg}")
        pace(1.2, args.fast)

        merchant_reply, state = merchant.handle_message(buyer_msg, state)
        print(f"[Merchant Agent]  {merchant_reply}")
        pace(1.2, args.fast)
        print()

        buyer_msg = buyer.respond_to(merchant_reply)

    banner("OUTCOME")
    if state.stage == "done":
        print("Purchase completed.")
    elif state.stage == "rejected":
        print("Session hard-stopped after repeated failed attempts (safety limit).")
    else:
        print("Session ended without a purchase (no match, or buyer gave up) — correct behavior, not an error.")

    events = read_log()
    banner(f"AUDIT TRAIL ({len(events)} events logged)")
    for e in events:
        reasoning = f" — {e['reasoning']}" if e.get("reasoning") else ""
        print(f"  [{e['stage']:>9}] {e['event']}{reasoning}")

    print()


if __name__ == "__main__":
    main()