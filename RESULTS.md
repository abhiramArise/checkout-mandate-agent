# Eval Results — Checkout Mandate Agent

**Pass rate: 10/10**

Run mode: dry-run (no live Razorpay/Groq calls — LLM extraction falls back to rule-based parsing when GROQ_API_KEY is unset).

| Scenario | Description | Expected | Actual | Result | Turns | Time (s) |
|---|---|---|---|---|---|---|
| S1_happy_path | Standard in-budget purchase, clean confirmation | done | done | PASS | 2 | 1.5582 |
| S2_over_budget | Requested item category exists but nothing fits budget | awaiting_intent | awaiting_intent | PASS | 1 | 0.711 |
| S3_user_cancels | User cancels after cart is proposed | awaiting_intent | awaiting_intent | PASS | 2 | 0.5889 |
| S4_no_confirmation_given | User says something ambiguous instead of yes/no | awaiting_confirmation | awaiting_confirmation | PASS | 2 | 0.6461 |
| S5_out_of_stock | Item matches budget but is out of stock (bluetooth speaker) | awaiting_intent | awaiting_intent | PASS | 1 | 1.8002 |
| S6_confirm_then_success | Hoodie purchase, explicit ok instead of yes | done | done | PASS | 2 | 0.571 |
| S7_low_budget_no_match | Budget far too low for anything in catalog | awaiting_intent | awaiting_intent | PASS | 1 | 0.6407 |
| S8_water_bottle_confirm | Simple item, 'sure' as confirmation word | done | done | PASS | 2 | 0.6731 |
| S9_speaker_confirm | Search term matches nothing in catalog at all | awaiting_intent | awaiting_intent | PASS | 1 | 1.486 |
| S10_cancel_then_retry | User cancels, then makes a fresh valid request in same session | done | done | PASS | 4 | 2.414 |

## Audit trail summary

Total logged events across all scenarios: **36**

| Stage | Event count |
|---|---|
| cart | 17 |
| intent | 11 |
| payment | 4 |
| razorpay | 4 |

## Per-scenario transcripts

### S1_happy_path — PASS
_Standard in-budget purchase, clean confirmation_

- **User:** I want running shoes under 3000
  **Agent:** Found: Running Shoes - Blue, Size 9 at ₹2499. Confirm purchase? (yes/no)
- **User:** yes
  **Agent:** [dry-run] Payment of ₹2499 for Running Shoes - Blue, Size 9 authorized and would be sent to Razorpay. Mandate ID: 97894ea9-a3c4-4f58-8d67-9fbaa4660047

### S2_over_budget — PASS
_Requested item category exists but nothing fits budget_

- **User:** I want a bluetooth speaker under 500
  **Agent:** I couldn't find anything matching 'bluetooth speaker' within your budget of ₹500. Want to raise your budget or try a different item?

### S3_user_cancels — PASS
_User cancels after cart is proposed_

- **User:** I want a yoga mat under 1000
  **Agent:** Found: Yoga Mat at ₹899. Confirm purchase? (yes/no)
- **User:** no
  **Agent:** No problem, cancelled. What would you like instead?

### S4_no_confirmation_given — PASS
_User says something ambiguous instead of yes/no_

- **User:** I want wireless earbuds under 2500
  **Agent:** Found: Wireless Earbuds at ₹1999. Confirm purchase? (yes/no)
- **User:** maybe later
  **Agent:** I need an explicit yes or no before proceeding — confirm purchase?

### S5_out_of_stock — PASS
_Item matches budget but is out of stock (bluetooth speaker)_

- **User:** I want a bluetooth speaker under 4000
  **Agent:** I couldn't find anything matching 'bluetooth speaker' within your budget of ₹4000. Want to raise your budget or try a different item?

### S6_confirm_then_success — PASS
_Hoodie purchase, explicit ok instead of yes_

- **User:** I want a cotton hoodie under 1500
  **Agent:** Found: Cotton Hoodie - Blue, Size M at ₹1299. Confirm purchase? (yes/no)
- **User:** ok
  **Agent:** [dry-run] Payment of ₹1299 for Cotton Hoodie - Blue, Size M authorized and would be sent to Razorpay. Mandate ID: 501be36c-b378-4ffc-8da8-b018c5b4ce85

### S7_low_budget_no_match — PASS
_Budget far too low for anything in catalog_

- **User:** I want running shoes under 100
  **Agent:** I couldn't find anything matching 'running shoes' within your budget of ₹100. Want to raise your budget or try a different item?

### S8_water_bottle_confirm — PASS
_Simple item, 'sure' as confirmation word_

- **User:** smart water bottle under 2000
  **Agent:** Found: Smart Water Bottle at ₹1499. Confirm purchase? (yes/no)
- **User:** sure
  **Agent:** [dry-run] Payment of ₹1499 for Smart Water Bottle authorized and would be sent to Razorpay. Mandate ID: e860aea7-6850-4975-8fae-fd950fe362c1

### S9_speaker_confirm — PASS
_Search term matches nothing in catalog at all_

- **User:** I want a laptop under 50000
  **Agent:** I couldn't find anything matching 'laptop' within your budget of ₹50000. Want to raise your budget or try a different item?

### S10_cancel_then_retry — PASS
_User cancels, then makes a fresh valid request in same session_

- **User:** earbuds under 2500
  **Agent:** Found: Wireless Earbuds at ₹1999. Confirm purchase? (yes/no)
- **User:** no
  **Agent:** No problem, cancelled. What would you like instead?
- **User:** yoga mat under 1000
  **Agent:** Found: Yoga Mat at ₹899. Confirm purchase? (yes/no)
- **User:** yes
  **Agent:** [dry-run] Payment of ₹899 for Yoga Mat authorized and would be sent to Razorpay. Mandate ID: 47d85912-207e-4c65-a197-e1f104fc461c
