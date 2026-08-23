"""
Core agent loop.

Design decision (worth stating explicitly in the pitch): the LLM is used
for natural-language understanding and response generation, but the
mandate state machine and all money-gating decisions are DETERMINISTIC
code, not LLM judgment calls. This is deliberate -- an LLM should decide
what the user wants; it should never be the thing standing between a
user and an irreversible payment. That's what "bounded and gated" means
in practice, not just in the pitch deck.

If GROQ_API_KEY is not set, falls back to a simple rule-based parser so
the eval harness and demo can run without any API key -- clearly logged
as mock mode so this is never misrepresented as live LLM behavior.
"""

from __future__ import annotations

import os
import re
import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

from agent.mandates import IntentMandate, CartMandate, PaymentMandate, MandateError
from agent.audit import log_event
from tools.catalog import search_catalog, get_item
from tools.razorpay_client import RazorpayToolError

try:
    from groq import Groq
except ImportError:
    Groq = None

MANDATE_SECRET = os.environ.get("MANDATE_SIGNING_SECRET", "dev-secret-change-me")

CONFIRM_WORDS = {"yes", "confirm", "go ahead", "sure", "ok", "okay", "proceed", "do it"}
CANCEL_WORDS = {"no", "cancel", "stop", "nevermind", "never mind"}


@dataclass
class SessionState:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    intent: Optional[IntentMandate] = None
    cart: Optional[CartMandate] = None
    payment: Optional[PaymentMandate] = None
    stage: str = "awaiting_intent"  # awaiting_intent | awaiting_confirmation | done | rejected
    failed_attempts: int = 0
    max_failed_attempts: int = 3


def _mock_extract_intent(message: str) -> dict:
    """Rule-based fallback extractor -- used only when no Groq key is set.
    Strips budget phrasing and filler words, leaving keyword terms for
    catalog search. Looks for a rupee budget ('under 2000', 'budget 1500')."""
    budget_match = re.search(r"(?:under|budget|below|max)\s*(?:rs\.?|₹)?\s*(\d+)", message.lower())
    budget = float(budget_match.group(1)) if budget_match else 5000.0

    goal = message.lower()
    goal = re.sub(r"(?:under|budget|below|max)\s*(?:rs\.?|₹)?\s*\d+", "", goal)
    filler = r"\b(i want|i'd like|looking for|please|a|an|the|for|to buy|buy)\b"
    goal = re.sub(filler, "", goal)
    goal = re.sub(r"\s+", " ", goal).strip()

    return {"goal": goal or message, "max_budget": budget, "category": None}


def _llm_extract_intent(message: str, client) -> dict:
    valid_categories = {"footwear", "electronics", "fitness", "apparel"}
    prompt = (
        "Extract a shopping intent from this user message as JSON with keys "
        "goal (string, a short product search phrase using everyday product "
        "words, not vague paraphrases), max_budget (number, in INR, default "
        "5000 if not mentioned), category (must be exactly one of: "
        "'footwear', 'electronics', 'fitness', 'apparel', or null if none "
        "clearly fits).\n\n"
        "Examples:\n"
        "'need something comfy for jogging' -> category: 'footwear'\n"
        "'want a gadget for music' -> category: 'electronics'\n"
        "'something for my home workouts' -> category: 'fitness'\n"
        "'need a warm top for winter' -> category: 'apparel'\n\n"
        "Respond with ONLY the JSON object, no other text.\n\n"
        f"Message: {message}"
    )
    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    text = resp.choices[0].message.content.strip()
    text = re.sub(r"^```json|```$", "", text, flags=re.MULTILINE).strip()
    result = json.loads(text)

    # defensive: the model doesn't always follow the closed category list
    # (e.g. returns 'sportswear' instead of 'fitness'/'footwear') --
    # rather than trust the prompt alone, validate here and fall back to
    # null so search_catalog's category fallback is only ever trusted
    # with a category that actually exists in the catalog.
    if result.get("category") not in valid_categories:
        result["category"] = None

    return result


class CheckoutAgent:
    def __init__(self, razorpay_client=None, dry_run: bool = True):
        """dry_run=True skips real Razorpay API calls and simulates a
        successful (or scenario-forced) response instead -- lets the eval
        harness run without live test-mode keys. Set dry_run=False and
        pass a real RazorpayClient for the actual demo/pitch video."""
        self.razorpay_client = razorpay_client
        self.dry_run = dry_run
        self.groq_client = None
        if os.environ.get("GROQ_API_KEY") and Groq is not None:
            self.groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def _extract_intent(self, message: str) -> dict:
        if self.groq_client:
            try:
                result = _llm_extract_intent(message, self.groq_client)
                print(f"[DEBUG] LLM extracted: {result}")
                return result
            except Exception as e:
                import traceback
                print(f"[DEBUG] Groq LLM extraction failed, falling back to mock: {e}")
                traceback.print_exc()
        return _mock_extract_intent(message)

    def handle_message(self, message: str, state: SessionState) -> tuple[str, SessionState]:
        msg_lower = message.strip().lower()

        # ---- Stage: awaiting_intent -> propose a cart ----
        if state.stage == "awaiting_intent":
            extracted = self._extract_intent(message)
            try:
                state.intent = IntentMandate(
                    goal=extracted["goal"],
                    max_budget=float(extracted["max_budget"]),
                    category=extracted.get("category"),
                )
                state.intent.sign(MANDATE_SECRET)
                log_event("intent", "intent_created", extracted, session_id=state.session_id)
            except Exception as e:
                log_event("intent", "intent_parse_failed", {"raw": message}, str(e), session_id=state.session_id)
                return ("Sorry, I couldn't understand your budget or request. "
                        "Could you rephrase, e.g. 'running shoes under 3000'?"), state

            results = search_catalog(extracted["goal"], extracted.get("category"))
            affordable = [r for r in results if r["price"] <= state.intent.max_budget and r["stock"] > 0]

            if not affordable:
                log_event("cart", "no_match_or_over_budget", {"query": extracted["goal"], "budget": state.intent.max_budget}, session_id=state.session_id)
                return (f"I couldn't find anything matching '{extracted['goal']}' "
                        f"within your budget of ₹{state.intent.max_budget:.0f}. "
                        "Want to raise your budget or try a different item?"), state

            item = affordable[0]
            try:
                state.cart = CartMandate.create(state.intent, item["name"], item["price"], MANDATE_SECRET)
            except MandateError as e:
                log_event("cart", "cart_creation_rejected", {"item": item}, str(e), session_id=state.session_id)
                return f"Couldn't add that to cart: {e}", state

            log_event("cart", "cart_proposed", {"item": item["name"], "price": item["price"]}, session_id=state.session_id)
            state.stage = "awaiting_confirmation"
            return (f"Found: {item['name']} at ₹{item['price']:.0f}. "
                    f"Confirm purchase? (yes/no)"), state

        # ---- Stage: awaiting_confirmation -> confirm cart, create+redeem payment mandate ----
        if state.stage == "awaiting_confirmation":
            if any(w in msg_lower for w in CANCEL_WORDS):
                log_event("cart", "cart_cancelled_by_user", {"item": state.cart.item_name}, session_id=state.session_id)
                state.stage = "awaiting_intent"
                state.cart = None
                return "No problem, cancelled. What would you like instead?", state

            if not any(w in msg_lower for w in CONFIRM_WORDS):
                return "I need an explicit yes or no before proceeding — confirm purchase?", state

            try:
                state.cart.confirm(MANDATE_SECRET)
                log_event("cart", "cart_confirmed", {"item": state.cart.item_name}, session_id=state.session_id)
                state.payment = PaymentMandate.create(state.cart, MANDATE_SECRET)
                log_event("payment", "payment_mandate_created", {"amount": state.payment.amount, "expiry": state.payment.expiry}, session_id=state.session_id)
            except MandateError as e:
                log_event("payment", "payment_mandate_rejected", {}, str(e), session_id=state.session_id)
                state.failed_attempts += 1
                return self._maybe_hard_stop(state, f"Couldn't proceed: {e}")

            return self._execute_payment(state)

        return "Session already complete. Start a new request to buy something else.", state

    def _execute_payment(self, state: SessionState) -> tuple[str, SessionState]:
        try:
            state.payment.redeem(MANDATE_SECRET)
        except MandateError as e:
            log_event("payment", "redeem_rejected", {}, str(e), session_id=state.session_id)
            state.failed_attempts += 1
            return self._maybe_hard_stop(state, f"Payment could not proceed: {e}")

        if self.dry_run or self.razorpay_client is None:
            log_event("razorpay", "dry_run_success", {"amount": state.payment.amount, "item": state.cart.item_name}, session_id=state.session_id)
            state.stage = "done"
            return (f"[dry-run] Payment of ₹{state.payment.amount:.0f} for "
                    f"{state.cart.item_name} authorized and would be sent to "
                    f"Razorpay. Mandate ID: {state.payment.mandate_id}"), state

        try:
            order = self.razorpay_client.create_order(state.payment.amount)
            link = self.razorpay_client.create_payment_link(
                order, description=state.cart.item_name
            )
            log_event("razorpay", "payment_link_created", {"order_id": order.order_id, "link": link.short_url}, session_id=state.session_id)
            state.stage = "done"
            return (f"Payment link created: {link.short_url} "
                    f"(₹{state.payment.amount:.0f} for {state.cart.item_name})"), state
        except RazorpayToolError as e:
            log_event("razorpay", "razorpay_call_failed", {"code": e.code}, str(e), session_id=state.session_id)
            state.failed_attempts += 1
            return self._maybe_hard_stop(
                state, f"Payment provider error ({e.code}): {e}. "
                       "You can try again or choose a different item."
            )

    def _maybe_hard_stop(self, state: SessionState, message: str) -> tuple[str, SessionState]:
        if state.failed_attempts >= state.max_failed_attempts:
            log_event("rejection", "hard_stop", {"attempts": state.failed_attempts}, session_id=state.session_id)
            state.stage = "rejected"
            return (message + " Too many failed attempts — stopping here to "
                    "avoid a retry loop. Please start a new request."), state
        state.stage = "awaiting_intent"
        state.cart = None
        state.payment = None
        return message, state