# Sample dispute evidence package

```
DISPUTE EVIDENCE PACKAGE
Session ID: 3722eb4b-4edf-4007-a44c-c4ded602d8eb
Generated: 2026-08-23T07:21:37.646473+00:00

SCOPE AND CONSENT CHECK
  Intent explicitly captured:        YES
    Stated goal: running shoes
    Budget cap authorized: Rs.3000
  Cart explicitly confirmed by user:  YES
  Payment mandate authorized:         YES
    Authorized amount: Rs.2499.0
    Authorization expiry: 2026-08-23 07:26:37 UTC
  Outcome: completed

FULL TIMELINE
  [2026-08-23 07:21:37 UTC] intent.intent_created
  [2026-08-23 07:21:37 UTC] cart.cart_proposed
  [2026-08-23 07:21:37 UTC] cart.cart_confirmed
  [2026-08-23 07:21:37 UTC] payment.payment_mandate_created
  [2026-08-23 07:21:37 UTC] razorpay.dry_run_success

Note: this package documents that authorization was scoped (explicit
budget cap, explicit cart confirmation) and time-bounded (payment
mandate expiry, single-use enforcement) at every step -- the standard
the CFPB's Jan 2026 Reg Z advisory sets for narrowing a consumer's
dispute rights on an agent-delegated purchase.
```
