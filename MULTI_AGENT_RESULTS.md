# Multi-Agent Results — Buyer Agent vs Checkout Mandate Agent

**5/8 sessions ended in a completed purchase** (remaining sessions correctly ended without a purchase — no match in budget, buyer gave up, or mandate rejection).

No human turns in this run — the buyer agent decides every message based on its own goal, budget, and patience; the checkout agent's mandate chain enforces bounds independent of what the buyer agent asks for.

| Persona | Goal | Budget | Outcome | Final Stage | Turns | Time (s) |
|---|---|---|---|---|---|---|
| Budget shopper - shoes | running shoes | ₹3000 | purchase_completed | done | 2 | 0.0927 |
| Tight budget - speaker | bluetooth speaker | ₹600 | session_ended_no_purchase | awaiting_intent | 2 | 0.0166 |
| Flexible budget - earbuds | wireless earbuds | ₹2160 | purchase_completed | done | 4 | 0.0423 |
| Haggler - hoodie | cotton hoodie | ₹1500 | purchase_completed | done | 3 | 0.02 |
| Impatient - laptop (no match) | laptop | ₹50000 | session_ended_no_purchase | awaiting_intent | 1 | 0.0071 |
| Exact match - yoga mat | yoga mat | ₹900 | purchase_completed | done | 2 | 0.025 |
| Out of stock item - speaker high budget | bluetooth speaker | ₹4800 | session_ended_no_purchase | awaiting_intent | 2 | 0.0156 |
| Generous budget - water bottle | smart water bottle | ₹5000 | purchase_completed | done | 2 | 0.0168 |

## Audit trail summary

Total logged mandate/tool events across all sessions: **39**

| Stage | Event count |
|---|---|
| cart | 17 |
| intent | 12 |
| payment | 5 |
| razorpay | 5 |

## Per-session transcripts

### Budget shopper - shoes — purchase_completed
_Goal: running shoes, starting budget: ₹3000_

- **Buyer agent:** I want running shoes under 3000
  **Merchant agent:** Found: Running Shoes - Blue, Size 9 at ₹2499. Confirm purchase? (yes/no)
- **Buyer agent:** yes
  **Merchant agent:** [dry-run] Payment of ₹2499 for Running Shoes - Blue, Size 9 authorized and would be sent to Razorpay. Mandate ID: 7839988a-78b4-49c0-99dd-cf08e93820e0

### Tight budget - speaker — session_ended_no_purchase
_Goal: bluetooth speaker, starting budget: ₹600_

- **Buyer agent:** I want bluetooth speaker under 500
  **Merchant agent:** I couldn't find anything matching 'bluetooth speaker' within your budget of ₹500. Want to raise your budget or try a different item?
- **Buyer agent:** okay, bluetooth speaker under 600
  **Merchant agent:** I couldn't find anything matching 'okay, bluetooth speaker' within your budget of ₹600. Want to raise your budget or try a different item?

### Flexible budget - earbuds — purchase_completed
_Goal: wireless earbuds, starting budget: ₹2160_

- **Buyer agent:** I want wireless earbuds under 1500
  **Merchant agent:** I couldn't find anything matching 'wireless earbuds' within your budget of ₹1500. Want to raise your budget or try a different item?
- **Buyer agent:** okay, wireless earbuds under 1800
  **Merchant agent:** I couldn't find anything matching 'okay, wireless earbuds' within your budget of ₹1800. Want to raise your budget or try a different item?
- **Buyer agent:** okay, wireless earbuds under 2160
  **Merchant agent:** Found: Wireless Earbuds at ₹1999. Confirm purchase? (yes/no)
- **Buyer agent:** yes
  **Merchant agent:** [dry-run] Payment of ₹1999 for Wireless Earbuds authorized and would be sent to Razorpay. Mandate ID: f0d71ecf-63a5-4719-9655-4ab2077d296a

### Haggler - hoodie — purchase_completed
_Goal: cotton hoodie, starting budget: ₹1500_

- **Buyer agent:** I want cotton hoodie under 1500
  **Merchant agent:** Found: Cotton Hoodie - Blue, Size M at ₹1299. Confirm purchase? (yes/no)
- **Buyer agent:** can you do better on price?
  **Merchant agent:** I need an explicit yes or no before proceeding — confirm purchase?
- **Buyer agent:** yes
  **Merchant agent:** [dry-run] Payment of ₹1299 for Cotton Hoodie - Blue, Size M authorized and would be sent to Razorpay. Mandate ID: 1a6e9bf2-7e55-4af7-828f-605c506b8956

### Impatient - laptop (no match) — session_ended_no_purchase
_Goal: laptop, starting budget: ₹50000_

- **Buyer agent:** I want laptop under 50000
  **Merchant agent:** I couldn't find anything matching 'laptop' within your budget of ₹50000. Want to raise your budget or try a different item?

### Exact match - yoga mat — purchase_completed
_Goal: yoga mat, starting budget: ₹900_

- **Buyer agent:** I want yoga mat under 900
  **Merchant agent:** Found: Yoga Mat at ₹899. Confirm purchase? (yes/no)
- **Buyer agent:** yes
  **Merchant agent:** [dry-run] Payment of ₹899 for Yoga Mat authorized and would be sent to Razorpay. Mandate ID: 52414b48-638a-4b4f-ad0a-79ff686cca61

### Out of stock item - speaker high budget — session_ended_no_purchase
_Goal: bluetooth speaker, starting budget: ₹4800_

- **Buyer agent:** I want bluetooth speaker under 4000
  **Merchant agent:** I couldn't find anything matching 'bluetooth speaker' within your budget of ₹4000. Want to raise your budget or try a different item?
- **Buyer agent:** okay, bluetooth speaker under 4800
  **Merchant agent:** I couldn't find anything matching 'okay, bluetooth speaker' within your budget of ₹4800. Want to raise your budget or try a different item?

### Generous budget - water bottle — purchase_completed
_Goal: smart water bottle, starting budget: ₹5000_

- **Buyer agent:** I want smart water bottle under 5000
  **Merchant agent:** Found: Smart Water Bottle at ₹1499. Confirm purchase? (yes/no)
- **Buyer agent:** yes
  **Merchant agent:** [dry-run] Payment of ₹1499 for Smart Water Bottle authorized and would be sent to Razorpay. Mandate ID: e5f1f779-26f0-4078-b6c3-95ac8c4225f3
