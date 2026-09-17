# Evaluation Package

This directory contains the human-labelled evaluation data, review history, reply-review sheet, and the reply-judge rubric for the AmazonHelp support agent.

The evaluation contract is intentionally strict:

- intent labels are human-reviewed;
- prediction IDs must match the golden IDs exactly;
- TRAIN data may be used for retrieval, but TEST labels must not be used to tune the agent;
- every metric must identify its data slice;
- provider failures must be recorded, not silently converted into successful predictions; and
- reply quality and provider failures are reported separately from intent accuracy.

## Directory map

| File | Purpose | Use for final results? |
|---|---|---|
| `golden_set_human_labelled.csv` | Current 150-row human-reviewed intent snapshot | Yes |
| `golden_set.csv` | Earlier frozen review snapshot | Audit history only |
| `golden_set_review.csv` | First manual review workspace | Audit history only |
| `golden_set_review_assistant_proposals.csv` | Assistant label proposals that the user corrected | Audit history only |
| `top50_reply_human_review.csv` | Human pass/fail and 1 to 5 review of generated replies | Yes for top-50 reply review |
| `judge_rubric.md` | Structured reply-judge criteria | Yes |

CSV files may contain historical customer text and personal details. Keep them local and do not publish them without redaction.

## 1. Golden intent set

### Source

The final intent snapshot is `golden_set_human_labelled.csv`. It contains 150 TEST examples selected from the AmazonHelp case data. The rows were reviewed by the user after an initial 20-example pilot and assistant proposals.

The approved taxonomy contains 13 intents:

1. `order_management`
2. `delivery_or_courier_issue`
3. `delivered_not_received`
4. `return_refund_or_replacement`
5. `damaged_wrong_or_missing_item`
6. `payment_charge_or_gift_card`
7. `account_access_or_security`
8. `prime_membership`
9. `pricing_promotion_or_availability`
10. `digital_content_device_or_app`
11. `seller_or_marketplace`
12. `other_or_ambiguous`
13. `customer_appreciation`

The definitions, inclusion rules, exclusion rules, and examples are in `../configs/intents.yaml`.

### Golden CSV fields

Important columns include:

| Field | Meaning |
|---|---|
| `example_id` | Stable ID such as `GH-001` |
| `split` | Dataset split, normally `test` for the golden set |
| `thread_id` | Source conversation identifier |
| `customer_message` | Message presented to the agent |
| `prior_context` | Earlier context, if needed to understand the message |
| `historical_amazon_reply` | Original historical reply, retained as context only |
| `intent` | Human-reviewed numeric label |
| `intent_name` | Human-reviewed taxonomy name |
| `review_status` | Review provenance, such as `human_reviewed` |

### Labelling rule

Label the customer's current support problem. Do not label the emotion alone, and do not copy the intent implied by the historical reply.

Use `other_or_ambiguous` only when the current problem cannot be determined from the message and its prior context.

Examples:

- A late parcel is `delivery_or_courier_issue`.
- A parcel marked delivered but missing is `delivered_not_received`.
- A received product that is broken or incomplete is `damaged_wrong_or_missing_item`.
- A duplicate or unexplained charge is `payment_charge_or_gift_card`.
- A request to cancel an order before normal delivery is `order_management`.

### Inspecting a source thread

If a row is difficult, use its `thread_id` to inspect the full chronological conversation:

```powershell
python scripts\view_thread.py --split test --thread-id THREAD_ID
```

Do not reorder rows, rename ID columns, or edit the frozen human-reviewed snapshot during evaluation.

## 2. Reply review sheet

`top50_reply_human_review.csv` contains the 50 generated replies from the top-50 run.

### Columns

| Field | Meaning |
|---|---|
| `example_id` | Matches the prediction and golden-set ID |
| `customer_message` | Input shown to the agent |
| `reply` | Generated support response |
| `judge_pass` | Saved LLM-judge result, including provider-failure rows stored as failed |
| `human_score_1_to_5` | Human quality score |
| `human_pass` | Human pass/fail decision |
| `human_notes` | Short reason for the decision |

### Human review standard

Pass a reply when it is relevant, grounded in the available evidence, useful, respectful, and safe. Fail it when it invents an action or fact, gives a misleading promise, is too vague to help, or ignores an important risk.

Safe human handoffs are acceptable when the request is ambiguous, sensitive, or unsupported. They should not claim that a case was already forwarded unless the system has evidence of that action.

The current completed sheet contains 47 human passes and 3 failures:

- GH-017: claims the issue was already forwarded to billing.
- GH-035: provides no concrete next step for a missing parcel.
- GH-048: invents a specific email date and claims a request was forwarded.

## 3. Reply-judge rubric

The rubric is in `judge_rubric.md`. It scores six dimensions from 1 to 5:

1. relevance;
2. groundedness;
3. helpfulness;
4. tone;
5. safety; and
6. escalation appropriateness.

A critical unsupported claim forces `passed=false`.

The top-50 Groq judge run produced 25 provider-valid rows. It also recorded 21 rate-limit failures and 2 malformed structured responses. The two reply-generator failures were safely escalated and excluded from the valid judge subset. These details are in `../artifacts/top50_reply_metrics.json`.

## 4. Evaluation commands

### Validate the taxonomy

```powershell
python scripts\validate_taxonomy.py
```

### Run the simple baselines

```powershell
python scripts\run_baselines.py
```

### Run the top-50 agent evaluation

The runner uses the first 50 rows of `golden_set_human_labelled.csv`, uses Groq, and checkpoints after every row:

```powershell
python scripts\run_top50_evaluation.py
```

Output: `../artifacts/top50_predictions.json`.

### Score intent predictions offline

```powershell
python scripts\score_top50_results.py
```

Output: `../artifacts/top50_metrics.json`.

### Judge replies

```powershell
python scripts\judge_top50_replies.py
```

Output files:

- `../artifacts/top50_reply_judgments.json`
- `../artifacts/top50_reply_metrics.json`
- `top50_reply_human_review.csv`

### Reproduce published metrics without an API

```powershell
python scripts\reproduce_results.py
```

This reads saved artifacts only and verifies that all 50 human review rows are complete.

## 5. Evaluation outputs

The published top-50 intent result is:

| System | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| Fixed delivery baseline | 30% | 0.0355 | 0.1385 |
| TF-IDF baseline | 36% | 0.4316 | 0.2844 |
| Main pipeline | 80% (40/50) | 0.8252 | 0.8043 |

This is a top-50 hand-labelled evaluation, not a full 150-row result. The sample is not balanced, with 15 delivery or courier examples.

## 6. Reproducibility rules

- Keep `.env` outside version control.
- Do not alter `golden_set_human_labelled.csv` after the evaluation is frozen.
- Do not use TEST labels to tune prompts, thresholds, retrieval, or taxonomy after scoring.
- Preserve raw prediction and judge artifacts.
- Report the exact slice, provider, model, and provider failures.
- Keep human review separate from assistant proposal history.
- Treat historical replies as evidence, not guaranteed answers.

## 7. Related project files

- Project overview: `../README.md`
- Final report: `../reports/final_report.md`
- Decision log: `../decisions.md`
- Taxonomy: `../configs/intents.yaml`
- Evaluation code: `../src/support_agent/evaluator.py`
