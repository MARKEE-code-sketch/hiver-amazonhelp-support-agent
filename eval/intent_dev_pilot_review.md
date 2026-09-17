# Intent classifier DEV pilot: review sheet

This is a 20-case seeded sample from the DEV split (`seed=2026`). One case was excluded because its conversation context contained non-English customer text. The remaining 19 labels were assigned by the assistant before running the classifier; they are **not human-verified ground truth**. Inputs sent to Google had numbers and email-like text redacted, and only earlier customer messages were used as context. No TEST case was used.

| System | Correct / 19 | Accuracy | Macro F1 over the 9 intents present |
|---|---:|---:|---:|
| Fixed delivery guess | 6 | 0.316 | 0.053 |
| TF-IDF baseline | 7 | 0.368 | 0.489 |
| LLM classifier | 15 | 0.789 | 0.784 |

The complete, case-level inputs and predictions are in `artifacts/intent_dev_pilot_results.json`. Four classifier predictions disagreed with the provisional labels:

| Case ID | Provisional label | Classifier label | What needs review |
|---|---|---|---|
| 2507105 | `delivery_or_courier_issue` | `delivered_not_received` | The parcel was later found beside a bin, not handed to the resident. Is this poor delivery handling or non-receipt? |
| 1912140 | `pricing_promotion_or_availability` | `payment_charge_or_gift_card` | Promised cashback did not appear after purchase. The taxonomy boundary between a promotion and a payment credit needs a ruling. |
| 2728874 | `delivery_or_courier_issue` | `other_or_ambiguous` | The customer criticizes packaging without saying the item was damaged. Is this a courier/packaging problem or only feedback? |
| 676880 | `order_management` | `delivery_or_courier_issue` | The order will not ship until the expected arrival day. Does the pre-dispatch rule outweigh the customer's delivery-time concern? |

The classifier gave these four disagreements confidence values from **0.85 to 0.95**. That is a warning: its confidence is not calibrated and must not be used alone to auto-handle a case.

Before calling this module's quality gate complete, a human should verify the pilot labels, especially the four cases above. The sample is too small and uneven for a final accuracy claim; four of the 13 intents do not appear at all.
