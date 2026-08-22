"""
Buyer agent: an independent agent with its own goal and budget that
negotiates a purchase with CheckoutAgent (the merchant-side agent) with
no human in the loop for the transaction itself.

This is the "agent-to-agent" half of the story: two separately-reasoning
agents transacting, with the merchant side enforcing the mandate chain
regardless of what the buyer agent asks for or how it phrases things.

Hybrid design, matching CheckoutAgent's own philosophy: the LLM is used
to PHRASE certain messages (opening line, negotiation pushback) so this
is genuinely an AI agent generating language, not a script. But the
actual DECISION -- accept, reject, walk away, how much to spend -- is
always deterministic Python (respond_to()'s branching logic), never left
to the LLM. Confirmation words ("yes"/"no") and budget-retry messages
are also kept as fixed, reliably-parseable strings rather than
LLM-phrased, because the merchant agent parses them with exact keyword
matching / regex -- letting the LLM freely rephrase those would risk
breaking that parsing, the same class of bug already found and fixed on
the merchant side (see README, "what broke, and how it got fixed").
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

try:
    from groq import Groq
except ImportError:
    Groq = None


@dataclass
class BuyerPersona:
    name: str
    goal: str            # e.g. "buy running shoes"
    max_budget: float
    patience: int = 3     # max negotiation turns before giving up
    accepts_first_offer: bool = True  # False = tries to push back once


class BuyerAgent:
    def __init__(self, persona: BuyerPersona):
        self.persona = persona
        self.turns_taken = 0
        self.groq_client = None
        if os.environ.get("GROQ_API_KEY") and Groq is not None:
            self.groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def opening_message(self) -> str:
        base = f"I want {self.persona.goal} under {int(self.persona.max_budget)}"
        return self._phrase("open_conversation", base, extra=f"Goal: {self.persona.goal}, budget: {int(self.persona.max_budget)}")

    def _phrase(self, intent: str, fallback: str, extra: str = "") -> str:
        """Uses the LLM to phrase what the buyer agent says, while the
        underlying DECISION (what intent/action this is) was already made
        by deterministic code in respond_to(). The LLM only controls
        wording -- never whether to accept, reject, or walk away from a
        transaction. Falls back to the fixed-template message if no LLM
        key is set or the call fails, so the agent always still works."""
        if not self.groq_client:
            return fallback
        try:
            prompt = (
                f"You are a shopper AI agent talking to a merchant checkout "
                f"agent. Write ONE short, natural sentence (under 20 words) "
                f"for this situation: {intent}. {extra} "
                f"Do not add quotes or explanation, just the sentence."
            )
            resp = self.groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )
            text = resp.choices[0].message.content.strip().strip('"')
            return text if text else fallback
        except Exception:
            return fallback

    def respond_to(self, merchant_reply: str) -> Optional[str]:
        """Decides the buyer agent's next message given the merchant
        agent's last reply. Returns None when the buyer agent decides to
        end the session (accepted, gave up, or hit patience limit).

        Decision logic is rule-based and deterministic -- NOT delegated
        to the LLM -- because this is the buyer agent's own spend-control
        boundary. Swapping in an LLM here would be reasonable for tone/
        phrasing, but the accept/reject/walk-away decision stays coded.
        """
        self.turns_taken += 1
        reply_lower = merchant_reply.lower()

        # Merchant found a matching item within budget -> proposing a cart
        if "confirm purchase" in reply_lower:
            price_match = re.search(r"₹(\d+)", merchant_reply)
            price = float(price_match.group(1)) if price_match else None

            if price is not None and price > self.persona.max_budget:
                # Should not happen if CheckoutAgent enforced budget correctly --
                # if it does, the buyer agent correctly refuses to overspend.
                return "no"

            if not self.persona.accepts_first_offer and self.turns_taken <= 1:
                # simulate a buyer that pushes back once before accepting --
                # CheckoutAgent has no negotiation logic, so this will just
                # re-prompt for confirmation, testing that path. Phrasing is
                # LLM-generated (cosmetic only); the underlying decision to
                # push back once, not accept immediately, is already fixed
                # by the persona's accepts_first_offer flag above.
                return self._phrase(
                    "politely ask the merchant for a better price before agreeing",
                    "can you do better on price?",
                )

            return "yes"

        # Merchant couldn't find anything in budget
        if "couldn't find anything" in reply_lower:
            if self.turns_taken >= self.persona.patience:
                return None  # give up
            # try a slightly relaxed ask (simulate realistic buyer behavior)
            bumped_budget = self.persona.max_budget * 1.2
            self.persona.max_budget = bumped_budget
            return f"okay, {self.persona.goal} under {int(bumped_budget)}"

        # Ambiguous / needs explicit confirmation
        if "explicit yes or no" in reply_lower:
            return "yes"

        # Payment succeeded or session done
        if "authorized" in reply_lower or "payment link created" in reply_lower:
            return None

        # Too many failed attempts, hard stop from merchant side
        if "too many failed attempts" in reply_lower:
            return None

        if self.turns_taken >= self.persona.patience:
            return None

        return "yes"  # default fallback