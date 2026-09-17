# Top-50 Evaluation Report

Date: 2026-09-17  
Scope: first 50 rows of `eval/golden_set_human_labelled.csv`  
Provider: Groq, model `openai/gpt-oss-20b`

## What this run answers

This run checks whether the complete support-agent pipeline predicts the approved intent better than simple baselines. It also attempts a structured review of generated replies. It is a quick top-50 checkpoint, not a final claim about all 150 examples.

## Intent results

| System | Accuracy | Macro F1 | Weighted F1 |
|---|---:|---:|---:|
| Fixed delivery baseline | 30% | 0.0355 | 0.1385 |
| TF-IDF baseline | 36% | 0.4316 | 0.2844 |
| Main classifier + retrieval + policy | **80% (40/50)** | **0.8252** | **0.8043** |

The slice contains all 13 approved intents, but it is not balanced: `delivery_or_courier_issue` appears 15 times. Rare-intent scores should therefore be treated as directional.

## Reply-judge results

The judge was called for 50 cases. Groq limits and output-format failures reduced the usable judge sample:

- 21 `RateLimitError` rows
- 2 `ValidationError` rows
- 2 reply-generator failures, which were safely converted to human handoffs and excluded from the valid judge subset
- 25 provider-valid judged replies

The valid subset passed 25/25, with average relevance 4.6/5, groundedness 4.4/5, helpfulness 3.56/5, and tone 4.44/5. This is not an independent human quality score; the safety and escalation dimensions defaulted to 3 in the provider-normalized judge output. Human review now covers all 50 rows: 47 passes and 3 failures (GH-017, GH-035, and GH-048). The simple exact pass/fail agreement between the judge field and human field is 28/50 (56%); this is affected by the 23 provider-error rows stored as judge failures, so it is not a clean judge-agreement estimate. The all-50 aggregate is retained for audit but must not be used as the headline quality result because provider failures were scored as failed rows.

## Policy observations

The deterministic policy returned `ESCALATE` for 34 cases and `AUTO_HANDLE` for 16. This is expected conservative behavior, but it is not escalation accuracy: the golden set contains no human escalation/action labels.

## Observed intent mismatches

These examples show where taxonomy boundaries still need attention:

- GH-001: defective DVD labelled `other_or_ambiguous`, predicted `damaged_wrong_or_missing_item`.
- GH-012 and GH-031: Prime delivery-guarantee complaints predicted as `prime_membership` instead of delivery.
- GH-024: an item delivered open predicted as a general delivery issue instead of damaged/wrong/missing item.
- GH-028: a No Cost EMI complaint predicted as pricing instead of payment.
- GH-041: an Amazon Pay cashback complaint predicted as pricing instead of payment.
- GH-048: a repeated app-support complaint predicted as ambiguous instead of digital/app support.

## What we must not claim

This result does not prove production readiness or full-dataset accuracy. It is a non-balanced 50-row slice, uses a provider with observed rate limits, has no human escalation labels, has no independent human reply ratings, and uses uncalibrated LLM confidence. Retrieved historical replies are evidence, not ground truth.

## Next five actions

1. Review and fill `eval/top50_reply_human_review.csv` for the 50 generated replies.
2. Re-run judge agreement metrics after human ratings exist (Spearman, Cohen's kappa, and raw agreement).
3. Investigate the intent-boundary mismatches above and freeze any taxonomy/prompt changes before another scored run.
4. Run the same frozen pipeline on all 150 rows only when the Groq quota/window supports it, preserving checkpoints.
5. Complete the reproducibility checklist and final report before calling the project submission-ready.

Artifacts: `artifacts/top50_predictions.json`, `artifacts/top50_metrics.json`, `artifacts/top50_reply_judgments.json`, and `artifacts/top50_reply_metrics.json`.
