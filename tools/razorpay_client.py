"""
Thin wrapper around Razorpay's test-mode APIs.

Security features included:
  - Idempotency key on order creation (prevents double-charge on retry)
  - Webhook signature verification using Razorpay's official utility
    (real production practice, not simulated)
  - All failures surfaced as structured RazorpayToolError so the agent
    can reason about them instead of guessing from a stack trace

Requires: pip install razorpay
Requires env vars: RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, RAZORPAY_WEBHOOK_SECRET
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Optional

try:
    import razorpay
except ImportError:  # allow the module to be imported before deps are installed
    razorpay = None


class RazorpayToolError(Exception):
    """Structured error the agent can reason about and explain to the
    user -- never swallowed, never silently retried."""

    def __init__(self, message: str, code: str = "razorpay_error"):
        self.code = code
        super().__init__(message)


@dataclass
class OrderResult:
    order_id: str
    amount: float
    currency: str
    status: str


@dataclass
class PaymentLinkResult:
    link_id: str
    short_url: str
    order_id: str
    status: str


class RazorpayClient:
    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        webhook_secret: Optional[str] = None,
    ):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET")
        self.webhook_secret = webhook_secret or os.environ.get(
            "RAZORPAY_WEBHOOK_SECRET"
        )

        if not self.key_id or not self.key_secret:
            raise RazorpayToolError(
                "Missing RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET. "
                "Get test-mode keys from the Razorpay Dashboard "
                "(Settings > API Keys) before running the agent.",
                code="missing_credentials",
            )

        if razorpay is None:
            raise RazorpayToolError(
                "razorpay package not installed. Run: "
                "pip install razorpay --break-system-packages",
                code="missing_dependency",
            )

        self.client = razorpay.Client(auth=(self.key_id, self.key_secret))

    def create_order(
        self, amount_rupees: float, currency: str = "INR",
        idempotency_key: Optional[str] = None,
    ) -> OrderResult:
        """Amount is taken in rupees for readability and converted to
        paise (Razorpay's base unit) internally."""
        idempotency_key = idempotency_key or str(uuid.uuid4())
        try:
            order = self.client.order.create(
                {
                    "amount": int(round(amount_rupees * 100)),
                    "currency": currency,
                    "payment_capture": 1,
                    "notes": {"idempotency_key": idempotency_key},
                }
            )
            return OrderResult(
                order_id=order["id"],
                amount=amount_rupees,
                currency=currency,
                status=order["status"],
            )
        except Exception as e:
            raise RazorpayToolError(
                f"Order creation failed: {e}", code="order_creation_failed"
            ) from e

    def create_payment_link(
        self, order: OrderResult, description: str
    ) -> PaymentLinkResult:
        try:
            link = self.client.payment_link.create(
                {
                    "amount": int(round(order.amount * 100)),
                    "currency": order.currency,
                    "description": description,
                    "notes": {"order_id": order.order_id},
                }
            )
            return PaymentLinkResult(
                link_id=link["id"],
                short_url=link["short_url"],
                order_id=order.order_id,
                status=link["status"],
            )
        except Exception as e:
            raise RazorpayToolError(
                f"Payment link creation failed: {e}",
                code="payment_link_failed",
            ) from e

    def verify_webhook_signature(
        self, payload_body: str, received_signature: str
    ) -> bool:
        """Verifies a Razorpay webhook using their official utility.
        This is real production security practice -- not a demo trick.
        Call this on every incoming webhook before trusting its content."""
        if not self.webhook_secret:
            raise RazorpayToolError(
                "RAZORPAY_WEBHOOK_SECRET not configured -- cannot verify "
                "webhook authenticity.",
                code="missing_webhook_secret",
            )
        try:
            self.client.utility.verify_webhook_signature(
                payload_body, received_signature, self.webhook_secret
            )
            return True
        except razorpay.errors.SignatureVerificationError:
            return False
