"""
Quick smoke test for the mandate enforcement logic -- no LLM, no Razorpay
API calls needed. Run this first to prove the core security/authorization
rules actually hold before wiring up the agent loop.

Run: python eval/test_mandates.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent.mandates import IntentMandate, CartMandate, PaymentMandate, MandateError

SECRET = "test-secret-do-not-use-in-prod"


def check(label, condition):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    return condition


def test_happy_path():
    print("\n-- Scenario: happy path --")
    intent = IntentMandate(goal="buy running shoes", max_budget=3000.0)
    intent.sign(SECRET)
    check("intent signed", intent.verify(SECRET))

    cart = CartMandate.create(intent, "Running Shoes - Blue, Size 9", 2499.0, SECRET)
    check("cart created within budget", cart.verify(SECRET))

    cart.confirm(SECRET)
    check("cart confirmed", cart.confirmed)

    payment = PaymentMandate.create(cart, SECRET)
    check("payment mandate created", payment.verify(SECRET))

    payment.redeem(SECRET)
    check("payment redeemed, marked used", payment.used)


def test_over_budget_rejected():
    print("\n-- Scenario: over-budget cart is rejected --")
    intent = IntentMandate(goal="buy earbuds", max_budget=1000.0)
    intent.sign(SECRET)
    try:
        CartMandate.create(intent, "Wireless Earbuds", 1999.0, SECRET)
        check("over-budget cart correctly rejected", False)
    except MandateError as e:
        check(f"over-budget cart correctly rejected ({e})", True)


def test_unconfirmed_cart_blocks_payment():
    print("\n-- Scenario: unconfirmed cart cannot produce a payment mandate --")
    intent = IntentMandate(goal="buy a yoga mat", max_budget=1000.0)
    intent.sign(SECRET)
    cart = CartMandate.create(intent, "Yoga Mat", 899.0, SECRET)
    # NOTE: cart.confirm() never called
    try:
        PaymentMandate.create(cart, SECRET)
        check("unconfirmed cart correctly blocked payment", False)
    except MandateError as e:
        check(f"unconfirmed cart correctly blocked payment ({e})", True)


def test_single_use_enforced():
    print("\n-- Scenario: payment mandate cannot be reused --")
    intent = IntentMandate(goal="buy a water bottle", max_budget=2000.0)
    intent.sign(SECRET)
    cart = CartMandate.create(intent, "Smart Water Bottle", 1499.0, SECRET)
    cart.confirm(SECRET)
    payment = PaymentMandate.create(cart, SECRET)
    payment.redeem(SECRET)
    try:
        payment.redeem(SECRET)  # second attempt
        check("double-spend correctly blocked", False)
    except MandateError as e:
        check(f"double-spend correctly blocked ({e})", True)


def test_expired_mandate_rejected():
    print("\n-- Scenario: expired payment mandate is rejected --")
    intent = IntentMandate(goal="buy a hoodie", max_budget=1500.0)
    intent.sign(SECRET)
    cart = CartMandate.create(intent, "Cotton Hoodie - Blue, Size M", 1299.0, SECRET)
    cart.confirm(SECRET)
    payment = PaymentMandate.create(cart, SECRET)
    payment.ttl_seconds = 0  # force immediate expiry for the test
    payment.sign(SECRET)     # re-sign so this isolates expiry, not tampering
    time.sleep(0.01)
    try:
        payment.redeem(SECRET)
        check("expired mandate correctly rejected", False)
    except MandateError as e:
        check(f"expired mandate correctly rejected ({e})", True)


def test_tampering_detected():
    print("\n-- Scenario: tampered mandate fails signature verification --")
    intent = IntentMandate(goal="buy earbuds", max_budget=2500.0)
    intent.sign(SECRET)
    cart = CartMandate.create(intent, "Wireless Earbuds", 1999.0, SECRET)
    cart.confirm(SECRET)
    payment = PaymentMandate.create(cart, SECRET)

    # simulate tampering: attacker changes amount after signing, without re-signing
    payment.amount = 1.0
    try:
        payment.redeem(SECRET)
        check("tampered mandate correctly rejected", False)
    except MandateError as e:
        check(f"tampered mandate correctly rejected ({e})", True)


if __name__ == "__main__":
    test_happy_path()
    test_over_budget_rejected()
    test_unconfirmed_cart_blocks_payment()
    test_single_use_enforced()
    test_expired_mandate_rejected()
    test_tampering_detected()
    print("\nAll scenarios executed. Review PASS/FAIL above.")
