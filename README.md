# Checkout Mandate Agent

A conversational checkout agent that completes purchases via Razorpay's
test-mode APIs, gated by a three-stage authorization chain: **Intent →
Cart → Payment mandate**. Every mandate is signed, bounded, single-use,
and logged — so every money-moving action is explainable, gated, and
auditable, not just "an LLM decided to."

Built as an honest exploration of a real, current problem: **as AI agents
start transacting on users' behalf, how does a merchant know an agent
had permission to spend — and how much, on what, until when?**

Verified end-to-end with a real LLM (Groq) and a real Razorpay test-mode
transaction — not just claimed. See [Live verification](#live-verification)
below.

## Why this exists (and what it isn't)

Agent-to-agent commerce is moving fast right now — ChatGPT's Instant
Checkout runs on Stripe/OpenAI's ACP, Google's AP2 has 60+ partners
building around cryptographically signed "mandates," and Coinbase's x402
has processed over 100M agent transactions. Card networks are in
production on this too: Mastercard Agent Pay and Visa's Trusted Agent
Protocol now provide agent-authorization rails with configurable spend
caps, merchant restrictions, and expiration windows, and in March 2026
Banco Santander and Mastercard completed what they describe as Europe's
first live end-to-end payment executed by an AI agent on production
infrastructure. Razorpay's own Buildathon brief calls this "the open
problem of the year" — and the regulatory side agrees it's unresolved: a
2026 legal analysis notes it remains an open question whether AI agent
authorization even satisfies existing Regulation E requirements, which
were written assuming a human is the one clicking "buy."

The specific failure mode this project targets has a name: **authority
decay** (also classified by OWASP as "Excessive Agency"). A user
authorizes Agent A with a defined budget and scope; Agent A delegates to
Agent B; Agent B has no direct relationship with the original user — it
only knows what Agent A told it. Without explicit scope enforcement at
each handoff, agents can end up operating beyond what was actually
authorized. That's exactly what this project's mandate chain, and the
buyer agent's own independently-enforced budget cap, are built to
prevent: authorization that survives a handoff between two
independently-reasoning agents, not just a single agent's word for it.

**This project does not implement AP2, ACP, Agent Pay, or any other
spec.** No solo two-week build should claim protocol compliance —
that's a fast way to lose credibility with anyone who actually knows the
space. What it does implement, from scratch, is the *underlying
pattern* those protocols and card-network frameworks are converging on:
an explicit, signed, bounded authorization chain between "what the user
wants" and "money actually moving." That pattern is the transferable
idea, and it's fully working here against Razorpay's real test-mode
Orders and Payment Links APIs.

## Architecture

```
User message
    │
    ▼
IntentMandate  (goal + hard budget cap, signed)
    │
    ▼
CartMandate    (exact item + price, must fit intent's budget,
    │           requires explicit user confirmation before advancing)
    ▼
PaymentMandate (scoped: amount + 5-min expiry + single-use,
    │           re-verified immediately before the Razorpay call)
    ▼
Razorpay test-mode Order + Payment Link
    │
    ▼
Audit log (every transition, every rejection, timestamped)
```

**Design decision worth calling out explicitly:** the LLM (Groq /
`openai/gpt-oss-120b`) is used only for natural-language understanding
and response generation. All mandate validation and money-gating logic
is deterministic Python, not LLM judgment. An LLM should decide *what
the user is asking for*; it should never be the thing standing between a
user and an irreversible payment. That's the actual meaning of "bounded
and gated," not just a phrase for the pitch.

## Security features

- **HMAC-SHA256 signing** on every mandate — tampering between creation
  and use is detected and rejected, not silently trusted.
- **Budget enforcement in code** — a `CartMandate` cannot be created if
  its price exceeds the `IntentMandate`'s max budget. Not a prompt
  instruction; a hard `if` statement.
- **Explicit confirmation gate** — a `PaymentMandate` cannot exist unless
  the cart was explicitly confirmed by the user (yes/no, not inferred).
- **Single-use + time-boxed payment mandates** — a 5-minute expiry window
  and a `used` flag prevent replay/double-spend on the same mandate.
- **Razorpay webhook signature verification** — using Razorpay's own
  `utility.verify_webhook_signature()`, real production practice, not
  simulated.
- **Idempotency keys** on order creation to prevent duplicate charges on
  retry.
- **Hard stop after repeated failures** — the agent refuses to keep
  retrying indefinitely; it stops and asks the user to restart after 3
  failed attempts, rather than looping.

## Repo structure

```
checkout-mandate-agent/
  agent/
    mandates.py    # Intent/Cart/Payment mandate classes, signing, validation
    core.py        # conversation loop, LLM intent parsing, mandate orchestration
    buyer_agent.py # autonomous buyer agent (two-agent extension)
    audit.py       # structured JSONL audit logger
  tools/
    razorpay_client.py  # Orders + Payment Links + webhook verification
    catalog.py           # mock merchant catalog with keyword synonyms
  eval/
    scenarios.json         # 10 scripted buyer scenarios (single-agent)
    run_eval.py             # runs single-agent scenarios, writes RESULTS.md
    run_multi_agent.py       # runs autonomous buyer vs merchant, writes MULTI_AGENT_RESULTS.md
    test_mandates.py         # unit-level proof of every security rule
  logs/
    audit_trail.jsonl         # generated on run — the audit trail itself
  RESULTS.md                   # single-agent eval pass rate + transcripts
  MULTI_AGENT_RESULTS.md         # two-agent eval outcomes + transcripts
  .env.example
  requirements.txt
```

## Running it

```bash
pip install -r requirements.txt --break-system-packages

# Proves the mandate/security rules work — no API keys needed:
python eval/test_mandates.py

# Runs all 10 conversational scenarios end-to-end — no API keys needed
# (falls back to a rule-based intent parser when GROQ_API_KEY is unset):
python eval/run_eval.py

# Runs the two-agent extension (autonomous buyer vs merchant):
python eval/run_multi_agent.py
```

For a live demo with real LLM understanding and real (test-mode)
Razorpay payment links: copy `.env.example` to `.env`, fill in
`GROQ_API_KEY` (console.groq.com) and `RAZORPAY_KEY_ID` /
`RAZORPAY_KEY_SECRET` (Razorpay Dashboard → Settings → API Keys, test
mode), then instantiate:

```python
CheckoutAgent(razorpay_client=RazorpayClient(), dry_run=False)
```

## Eval results

10/10 scripted single-agent scenarios pass — happy path, over-budget
rejection, out-of-stock handling, user cancellation, ambiguous
confirmation, mid-session recovery after cancel. Verified twice: once
with the deterministic rule-based fallback parser, and again against the
real Groq LLM. Full transcripts and audit-event counts in
[`RESULTS.md`](./RESULTS.md).

## Two-agent extension: autonomous buyer vs merchant

Built on top of the (already fully working, standalone) single-agent
core above. `agent/buyer_agent.py` is an independent agent with its own
goal, budget, and negotiation behavior — it decides every message
itself, with no scripted human turns and no human in the loop for the
transaction. `eval/run_multi_agent.py` runs it against the same
CheckoutAgent merchant side across 8 personas (tight budgets, hagglers,
impatient buyers, out-of-stock requests).

**Result: 5/8 sessions completed a purchase.** The other 3 correctly did
*not* complete — two personas wanted an item that's out of stock in the
catalog regardless of budget, one wanted an item that doesn't exist at
all. That's not a bug to chase to 8/8; it's the merchant agent's mandate
gate holding up against an autonomous counterpart that adjusts its own
budget mid-conversation, same as it holds against a scripted human.

Like the checkout agent's own money-gating, the buyer agent's spend cap
is enforced in code, not left to LLM judgment — an autonomous buyer
agent shouldn't be able to reason its way past its own stated budget any
more than the merchant agent lets a user talk it into skipping a
mandate. Full transcripts in
[`MULTI_AGENT_RESULTS.md`](./MULTI_AGENT_RESULTS.md).

## Live verification

Beyond the scripted eval suites, the full stack was run live, once each,
against real external services:

- **Real Groq LLM** (`openai/gpt-oss-120b`) correctly parsed natural,
  unscripted phrasing (e.g. "need something comfy for jogging, can't
  spend more than three thousand rupees" → `{goal: "comfortable jogging
  shoes", max_budget: 3000, category: "footwear"}`).
- **Real Razorpay test-mode Order + Payment Link** created end-to-end
  through the full conversational agent (not just the isolated API
  client) — a genuine `rzp.io` link rendering a live Razorpay checkout
  page for ₹2,499, "Running Shoes - Blue, Size 9," correctly flagged as
  test mode.

This confirms the architecture works as a live system, not only against
scripted/mocked inputs.

## What broke, and how it got fixed

**Bug 1 — catalog search failed silently, scored 5/10 instead of 10/10.**
The first eval run scored 5/10, not 10/10. The bug: the mock intent
parser passed the entire raw user message ("I want running shoes under
3000") as the search query, and the catalog search required that whole
string to appear as a substring inside a product name — which of course
it never did. Every scenario that depended on a cart actually being
proposed failed silently into a generic "couldn't find anything" reply,
which *looked* plausible enough that it was tempting to assume the
scenarios themselves were just badly designed. Re-reading the transcripts
line by line (not just the pass/fail table) showed the real cause. Fixed
by cleaning filler/budget phrasing out of the extracted goal and
switching catalog search to keyword-overlap matching instead of full
substring containment.

**Bug 2 — LLM understood the request correctly, catalog still couldn't
find it.** After wiring in a real Groq LLM (`openai/gpt-oss-120b` —
`llama-3.3-70b-versatile`, used originally, has since been deprecated by
Groq), a message like "need something comfy for jogging, can't spend
more than three thousand rupees" was correctly parsed into a ₹3000
budget — but still returned "couldn't find anything." The LLM had
paraphrased the goal into words ("jogging gear") that never literally
appear in any catalog product name, so the keyword-overlap search from
Bug 1's fix still missed it. Diagnosed by adding a debug print of the raw
LLM extraction, which showed the model was *also* inventing category
labels outside the ones the catalog actually uses (returning
`'sportswear'` instead of `'footwear'`). First attempted fix: few-shot
examples in the prompt plus code-level validation of the category, with
catalog search falling back to matching *any* item in that broad
category when no keyword matched.

**Bug 3 — the Bug 2 fix introduced a worse bug: false-positive matches.**
The category-fallback fix for Bug 2 solved "jogging gear" correctly
finding Running Shoes — but it was too permissive. Eval scenario S9 asks
for "laptop" (nothing resembling a laptop exists in the catalog); the
LLM correctly tagged it `category: 'electronics'`, and the fallback then
matched it to **Wireless Earbuds** — wrong, but silently "successful"
from the code's point of view, since it returned *something*. The same
failure hit the out-of-stock-speaker scenario, incorrectly resolving to
earbuds instead of correctly reporting no match. The lesson: a broad,
LLM-guessed category is too loose a signal to match on — right category,
wrong (or nonexistent) item. Fixed by replacing category-based fallback
entirely with **explicit per-item keyword synonyms** (e.g. Running Shoes
lists `jogging`, `sport`, `athletic` as synonyms). This is deterministic
and precise: "jogging" still correctly finds Running Shoes, but "laptop"
correctly finds nothing, because no catalog item claims that synonym —
no category-level guessing involved. Re-verified at 10/10 (single-agent)
and 5/8 (two-agent) against the real Groq LLM, confirming the fix holds
under actual non-deterministic LLM output, not just scripted input.