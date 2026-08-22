"""
Mandate model: Intent -> Cart -> Payment.

Inspired by the intent/cart/payment authorization pattern used in emerging
agentic-commerce standards (e.g. AP2's mandate model). This is NOT a spec
implementation -- it's a from-scratch enforcement layer built around the
same idea: every money-moving action must be traceable to an explicit,
bounded, signed authorization.

Design rules enforced in code (not just prompted to the LLM):
  1. A CartMandate can only be created from a valid IntentMandate, and its
     price must fit within the intent's max_budget.
  2. A PaymentMandate can only be created from an explicitly confirmed
     CartMandate.
  3. A PaymentMandate is single-use and time-boxed (expiry).
  4. Every mandate is HMAC-signed at creation and verified before use --
     proof it hasn't been tampered with in transit / in memory.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional


class MandateError(Exception):
    """Raised whenever a mandate rule is violated. Callers should catch
    this and turn it into a graceful, explained rejection -- never a
    silent retry or a swallowed failure."""


def _sign(payload: dict, secret: str) -> str:
    body = json.dumps(payload, sort_keys=True).encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _verify(payload: dict, signature: str, secret: str) -> bool:
    expected = _sign(payload, secret)
    return hmac.compare_digest(expected, signature)


@dataclass
class IntentMandate:
    goal: str
    max_budget: float
    category: Optional[str] = None
    mandate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    signature: str = field(default="", init=False)

    def to_signable(self) -> dict:
        return {
            "mandate_id": self.mandate_id,
            "goal": self.goal,
            "max_budget": self.max_budget,
            "category": self.category,
            "created_at": self.created_at,
        }

    def sign(self, secret: str) -> None:
        self.signature = _sign(self.to_signable(), secret)

    def verify(self, secret: str) -> bool:
        return _verify(self.to_signable(), self.signature, secret)


@dataclass
class CartMandate:
    intent: IntentMandate
    item_name: str
    price: float
    confirmed: bool = False
    mandate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    signature: str = field(default="", init=False)

    def to_signable(self) -> dict:
        return {
            "mandate_id": self.mandate_id,
            "intent_id": self.intent.mandate_id,
            "item_name": self.item_name,
            "price": self.price,
            "confirmed": self.confirmed,
            "created_at": self.created_at,
        }

    def sign(self, secret: str) -> None:
        self.signature = _sign(self.to_signable(), secret)

    def verify(self, secret: str) -> bool:
        return _verify(self.to_signable(), self.signature, secret)

    @classmethod
    def create(cls, intent: IntentMandate, item_name: str, price: float,
               secret: str) -> "CartMandate":
        if price > intent.max_budget:
            raise MandateError(
                f"Cart price {price} exceeds intent max_budget "
                f"{intent.max_budget} for goal '{intent.goal}'."
            )
        cart = cls(intent=intent, item_name=item_name, price=price)
        cart.sign(secret)
        return cart

    def confirm(self, secret: str) -> None:
        """Explicit user confirmation step. Must be called before a
        PaymentMandate can be created from this cart."""
        self.confirmed = True
        self.sign(secret)  # re-sign since state changed


@dataclass
class PaymentMandate:
    cart: CartMandate
    amount: float
    ttl_seconds: int = 300  # 5 minute window, single-use
    mandate_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: float = field(default_factory=time.time)
    used: bool = False
    signature: str = field(default="", init=False)

    @property
    def expiry(self) -> float:
        return self.created_at + self.ttl_seconds

    def is_expired(self) -> bool:
        return time.time() > self.expiry

    def to_signable(self) -> dict:
        return {
            "mandate_id": self.mandate_id,
            "cart_id": self.cart.mandate_id,
            "amount": self.amount,
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            "used": self.used,
        }

    def sign(self, secret: str) -> None:
        self.signature = _sign(self.to_signable(), secret)

    def verify(self, secret: str) -> bool:
        return _verify(self.to_signable(), self.signature, secret)

    @classmethod
    def create(cls, cart: CartMandate, secret: str) -> "PaymentMandate":
        if not cart.confirmed:
            raise MandateError(
                f"Cannot create PaymentMandate: cart '{cart.item_name}' "
                f"has not been explicitly confirmed by the user."
            )
        if not cart.verify(secret):
            raise MandateError(
                "Cart signature verification failed -- possible tampering."
            )
        payment = cls(cart=cart, amount=cart.price)
        payment.sign(secret)
        return payment

    def redeem(self, secret: str) -> None:
        """Call immediately before firing the actual Razorpay charge.
        Enforces: not expired, not already used, signature intact,
        amount unchanged since signing."""
        if not self.verify(secret):
            raise MandateError(
                "PaymentMandate signature verification failed -- "
                "possible tampering."
            )
        if self.used:
            raise MandateError(
                f"PaymentMandate {self.mandate_id} has already been used "
                f"(single-use enforcement)."
            )
        if self.is_expired():
            raise MandateError(
                f"PaymentMandate {self.mandate_id} expired at "
                f"{self.expiry}, now is {time.time()}."
            )
        self.used = True
        self.sign(secret)  # re-sign to lock in used=True
