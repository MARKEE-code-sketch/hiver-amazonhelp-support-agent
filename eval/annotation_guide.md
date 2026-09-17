# AmazonHelp intent annotation guide

## Goal

Choose exactly one intent for the customer's current support problem. Use the
customer message and prior context. Do not copy the subject of Amazon's old
reply when it does not match the customer's request.

## Allowed intents

1. `order_management`
2. `delivery_or_courier_issue`
3. `delivered_not_received`
4. `return_refund_or_replacement`
5. `damaged_wrong_or_missing_item`
6. `payment_charge_or_gift_card`
7. `account_access_or_security`
8. `prime_membership`
9. `digital_content_device_or_app`
10. `seller_or_marketplace`
11. `pricing_promotion_or_availability`
12. `other_or_ambiguous`
13. `customer_appreciation`

Full definitions and examples are in `configs/intents.yaml`.

## Labelling steps

1. Read `customer_message`.
2. Read `prior_context` when the current message is a follow-up.
3. Identify the underlying problem, not the customer's emotion.
4. Apply the tie-breaking rules below.
5. Enter one exact intent name in `gold_intent`.
6. Set `ambiguous` to `yes` or `no`.
7. Add a short note only when the choice was difficult.
8. Set `review_status` to `reviewed`.

## Tie-breaking rules

- Damaged, wrong, defective, or incomplete item wins over the requested refund
  or replacement.
- Marked delivered but missing wins over a general delivery problem.
- A late Prime shipment is a delivery issue, not a Prime-membership issue.
- Prime Video, Kindle, Alexa, Echo, Fire TV, and Amazon app problems are digital
  product issues, not general Prime or account issues.
- A seller label is used when seller conduct, fraud, communication, or listing
  quality is the central problem.
- Price shown before purchase is pricing; an incorrect charge after payment is
  payment.
- Use `other_or_ambiguous` only after checking the current message and context.
- Use `customer_appreciation` only for genuine praise with no unresolved request.
  Sarcastic thanks must use the underlying complaint intent.

## Pilot procedure

The user completed rows `GH-001` through `GH-020` using numeric labels. The
pilot exposed genuine appreciation messages, so label `13` was added without
renumbering labels `1` through `12`. Assistant labels for rows `GH-021` through
`GH-150` are proposals until the user reviews them.
