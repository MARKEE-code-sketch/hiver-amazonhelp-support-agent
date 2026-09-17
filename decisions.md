# Project Decision Log

This file records project decisions as questions and answers. Each answer includes the reason, evidence, trade-off, and conditions that could make us revisit it.

## Decision 001 - How do we measure a brand occurrence?

**Date:** 2026-09-14  
**Status:** Confirmed

### Question

What should count as a brand occurrence in the Customer Support on Twitter dataset?

### Answer

Count every row where `inbound=False`, grouped by `author_id`. On an outbound row, `author_id` is the identifiable support brand that wrote the tweet.

Do not count inbound rows by `author_id`, because inbound authors are customers and are usually represented by anonymized numeric IDs.

### Why?

This is the simplest direct measurement of how active each brand is in the dataset. It can be reproduced without guessing a brand name from the message text.

### Validation

Raw activity alone is not enough. We also verify that an outbound tweet's `in_response_to_tweet_id` points to a real inbound customer tweet. This gives us a more useful measure: verified customer-to-brand reply data.

---

## Decision 002 - Is the largest raw count sufficient by itself?

**Date:** 2026-09-14  
**Status:** Confirmed

### Question

Should we choose a brand only because it has the highest number of outbound tweets?

### Answer

No. The largest count is the primary selection rule requested for this phase, but it must be checked against:

- verified replies to real inbound customer messages;
- number of distinct customer messages receiving replies; and
- sampled customer/reply pairs.

### Why?

A brand could post many announcements, duplicate replies, or unconnected messages. Those rows would increase volume without giving the chatbot useful historical support examples.

### Evidence

The profiler scanned all 2,811,774 rows and used a second pass to verify reply links against the set of real inbound tweet IDs.

---

## Decision 003 - Which brand has the most occurrences?

**Date:** 2026-09-14  
**Status:** Confirmed

### Question

Which brand appears most often as the author of outbound support tweets?

### Answer

`AmazonHelp` ranks first.

```text
AmazonHelp outbound tweets:                 169,840
Verified replies to inbound customer tweets: 168,814
Distinct customer messages replied to:       154,976
Verified reply rate:                           99.40%
```

The runner-up is `AppleSupport` with 106,860 outbound tweets. AmazonHelp has 62,980 more outbound tweets, a 58.94% lead over AppleSupport.

### Evidence

- Reproducible command: `python scripts/profile_brands.py --top-n 20 --sample-size 12 --seed 42`
- Machine-readable result: `artifacts/brand_profile.json`
- Module: `src/support_agent/brand_profiler.py`
- Tests: `tests/test_brand_profiler.py`

---

## Decision 004 - Which brand will the support agent target?

**Date:** 2026-09-14  
**Status:** Confirmed

### Question

Which brand did we choose for the Hiver support agent, and why?

### Answer

We chose **AmazonHelp**.

### Why?

AmazonHelp satisfies the requested largest-occurrence criterion and also has the largest validated pool of customer-support replies. Its 154,976 distinct replied-to customer messages provide ample data for:

- discovering recurring intents;
- creating leakage-safe TRAIN/DEV/TEST splits;
- building a historical retrieval index; and
- sampling a 150-250 example golden evaluation set.

### Alternatives considered

`AppleSupport`, `Uber_Support`, and `SpotifyCares` have narrower product domains and may be easier to model, but all have substantially fewer support examples. Under the selection criterion agreed for this phase, AmazonHelp is the evidence-backed choice.

### Trade-off and re-evaluation trigger

AmazonHelp is broad and multilingual. This can make a small intent taxonomy harder to define and can mix regional support styles or policies.

The next data-quality phase must measure language and issue coverage. We will revisit the brand only if the data cannot support a coherent, explainable scope and roughly 8-12 useful intents. We will not silently change brands.

---

## Decision 005 - How will future decisions be recorded?

**Date:** 2026-09-14  
**Status:** Confirmed

### Question

What format will we use for later project decisions?

### Answer

Append each material decision to this file as a numbered question and answer. Record:

- the date and status;
- the question;
- the chosen answer;
- why it was chosen;
- evidence or measured results;
- alternatives/trade-offs; and
- the condition that would justify revisiting it, when applicable.

Routine coding details do not need separate entries unless they affect scope, evaluation validity, safety, cost, or reproducibility.

---

## Decision 006 - What language scope will the project use?

**Date:** 2026-09-15  
**Status:** Confirmed by user

### Question

Will the AmazonHelp agent support multiple languages?

### Answer

No. The project scope is **English-only**, as confirmed by the user. We will not build the separate language-distribution profiling stage.

### Why?

A single-language scope keeps intent labels, retrieved evidence, generated replies, and human evaluation consistent and explainable within the assignment timeline.

### Important boundary

The raw AmazonHelp data contains some non-English messages. Thread construction remains language-neutral because its job is only to reconstruct the source graph correctly. Before intent discovery, the chosen English-only scope must be enforced without moving a thread between TRAIN, DEV, and TEST. We will not report the raw thread files as already English-filtered.

---

## Decision 007 - How will AmazonHelp conversations be reconstructed?

**Date:** 2026-09-15  
**Status:** Implemented and verified

### Question

Should conversations be built from CSV row order or from Twitter reply links?

### Answer

Build connected conversations from `tweet_id`, `in_response_to_tweet_id`, and `response_tweet_id`. Do not use CSV row order as conversation structure.

### Why?

Rows in the dataset are not guaranteed to form complete conversations in display order. Reply IDs are the explicit source relationships and preserve multi-turn and branched exchanges.

### Inclusion rule

A saved thread must contain at least one inbound customer message and at least one outbound AmazonHelp message. Brand-only announcements and unrelated-brand conversations are not usable support threads.

### Evidence

```text
Source rows scanned:               2,811,774
AmazonHelp seed tweets:              169,840
Graph-closure passes:                      9
Usable threads:                       82,534
Usable messages:                     374,042
Missing referenced tweet IDs:          5,062
Detected cycles:                            0
Duplicate thread IDs:                       0
Duplicate message IDs:                      0
Out-of-order messages:                      0
```

The 5,062 missing referenced IDs represent tweets linked by the source data but absent from the CSV. Available connected messages are preserved, and the missing parent ID can act as a stable thread root.

### Reproducible command

`python scripts/build_threads.py`

---

## Decision 008 - How will the dataset be divided for development and evaluation?

**Date:** 2026-09-15  
**Status:** Implemented and verified

### Question

Should AmazonHelp conversations be split randomly or chronologically?

### Answer

Split complete threads chronologically by their first message:

```text
Oldest 70% -> TRAIN
Next 15%   -> DEV
Newest 15% -> TEST
```

### Why?

Chronological splitting better represents the real task: learn from older support conversations and evaluate on newer ones. Keeping an entire thread in one split prevents the model from seeing part of a TEST conversation in TRAIN.

### Evidence

```text
TRAIN: 57,773 threads / 270,966 messages
DEV:   12,380 threads /  51,810 messages
TEST:  12,381 threads /  51,266 messages
Total: 82,534 threads / 374,042 messages
```

Independent verification found zero duplicate or overlapping thread IDs. TRAIN ends before DEV begins, and DEV ends before TEST begins. Exact file hashes and date ranges are stored in `artifacts/split_manifest.json`.

### Reproducible command

`python scripts/split_threads.py`

---

## Decision 009 - What format will store reconstructed threads and splits?

**Date:** 2026-09-15  
**Status:** Implemented

### Question

Why are reconstructed conversations stored as JSON Lines (`.jsonl`)?

### Answer

Store one complete conversation per line. Each line contains thread metadata and its ordered list of messages.

### Why?

JSONL is simple to inspect, stream, test, and divide without requiring an additional database or dataframe dependency. A single thread is never broken across rows or files.

### Trade-off

JSONL is larger than Parquet. That is acceptable for the current 119 MB processed dataset and keeps these modules dependency-free. We will only introduce Parquet later if measured performance requires it.

### Repository rule

Raw and processed tweet data stay local and are ignored by Git. Small manifests, aggregate statistics, and safe evaluation artifacts may be committed.

---

## Decision 010 - How will a person read one JSONL thread?

**Date:** 2026-09-15  
**Status:** Implemented

### Question

JSONL preserves the data well, but how can a reviewer read one conversation without searching through a large, cluttered file?

### Answer

Keep JSONL as the machine-readable source and provide `scripts/view_thread.py` as a human-readable view. It finds a thread by ID or row number and prints the messages in conversation order. It can also save that view as Markdown.

### Why?

We do not need to duplicate every large split into another format. The small viewer gives a readable representation on demand while the JSONL remains the single processed source.

### Reproducible command

`python scripts/view_thread.py --split test --thread-id 2831688`

---

## Decision 011 - What counts as an intent-review case?

**Date:** 2026-09-15  
**Status:** Implemented

### Question

Which part of a reconstructed thread should become one row for intent review?

### Answer

Use a customer message that received a direct AmazonHelp reply. Preserve up to four earlier messages as context and keep the historical Amazon reply for understanding the old conversation.

### Why?

The customer message is the input whose intent we need to label. Its nearby context makes follow-up messages understandable, while the direct reply confirms that it was a real support interaction.

### Evidence

The case builder found 82,457 TRAIN, 15,326 DEV, and 15,984 TEST English-candidate cases. Its language check is only a conservative sampling guard; it is not treated as a language-classification module, and the reviewer remains the final check for the agreed English scope.

---

## Decision 012 - Will automatic clusters assign the golden intents?

**Date:** 2026-09-15  
**Status:** Rejected for automatic labelling

### Question

Should TF-IDF clustering automatically assign intent names to the 150 examples?

### Answer

No. Use clustering only as discovery evidence and leave every golden intent blank for human review.

### Why?

On a seeded sample of 5,000 TRAIN cases, 20 clusters produced a silhouette score of `-0.044264`. That means the discovered groups overlap and are not reliable enough to act as truth. Automatically copying those labels would bias the evaluation set.

### Evidence

The diagnostic output is stored in `artifacts/intent_discovery/`. It is separated from TEST and was not used to label or select the 150 rows.

---

## Decision 013 - How will the 150 intent-review examples be selected?

**Date:** 2026-09-15  
**Status:** Implemented; awaiting human labels

### Question

How should we prepare 150 examples that are readable, reproducible, and safe for later evaluation?

### Answer

Create `eval/golden_set_review.csv` from the held-out TEST cases using seed `42`. Use at most one case per thread, exclude only context-free acknowledgements such as “done” or “thanks,” and leave all human annotation fields blank.

### Why?

TEST-only sampling keeps evaluation separate from training. One row per thread improves coverage. CSV opens cleanly in Excel, which makes manual review much easier than JSONL.

### Verification

```text
Rows:                 150
Unique thread IDs:    150
All rows in TEST:     yes
Human fields blank:   yes
Deterministic rerun:  yes
SHA-256: 7877B023F08F325767E3D95D084BA4EA74FE65C21137E291AA896E99BC78FEA3
```

The file remains a **golden-set candidate** until the user reviews its intents. After review, labels will be normalized and frozen as `golden_set.csv`.

---

## Decision 014 - Can Banking77 labels be used as AmazonHelp golden labels?

**Date:** 2026-09-15  
**Status:** Rejected due to dataset and assignment mismatch

### Question

Can the intent labels from the supplied secondary dataset be used to label the 150 AmazonHelp examples?

### Answer

No. The supplied snapshot is Banking77 and contains 77 banking-specific intents, not 12 Amazon support intents. Its labels must not be copied onto the AmazonHelp golden set.

### Why?

Banking intents such as `card_swallowed`, `cash_withdrawal_charge`, and `exchange_rate` do not describe Amazon orders, deliveries, returns, products, or Prime membership. Forced mapping would create incorrect ground truth and misleading evaluation scores.

The assignment document also states that:

- the agent must use a small set of intents defined from the selected brand's data;
- Banking77 is an optional secondary dataset for intent work only; and
- the golden evaluation set must contain 150-250 hand-labelled examples built by the candidate.

### Evidence

The local Banking77 `dataset_infos.json` declares 13,083 examples and 77 labels. The assignment wording appears in paragraphs 7, 14, and 18 of `Hiver SDE Intern Assignment.docx`.

### Allowed use

Banking77 may later be used as a separate diagnostic to test whether the intent-classification and metric code works on an already-labelled dataset. Its results must be reported separately from AmazonHelp results.

---

## Decision 015 - Which intent taxonomy will the AmazonHelp agent use?

**Date:** 2026-09-16  
**Status:** Draft; awaiting the 20-example human pilot

### Question

What small, Amazon-specific intent set should be used to label the golden examples?

### Answer

Use these 12 provisional intents:

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

### Why?

These themes recur in AmazonHelp TRAIN conversations and cover the main support lifecycle without creating a large, difficult taxonomy. `other_or_ambiguous` prevents reviewers from forcing unclear cases into a wrong class.

### Evidence

The taxonomy was derived only from TRAIN cases. A full pass over 82,457 TRAIN cases found keyword evidence for every actionable intent. Keywords are used only to measure theme presence; they do not assign labels. Definitions, positive examples, exclusions, and tie-breaking rules are stored in `configs/intents.yaml` and `eval/annotation_guide.md`.

### Human gate

The taxonomy is not final until the user labels examples `GH-001` through `GH-020` and we review where the definitions caused disagreement or uncertainty.

---

## Decision 016 - How will the 150 examples be divided for annotation?

**Date:** 2026-09-16  
**Status:** Approved workflow; annotation not started

### Question

Who will label the 150 golden-set candidates?

### Answer

The user will label the first 20 examples. After the pilot is checked and the taxonomy is frozen, the assistant may propose labels for the remaining 130. The user must review and approve those proposed labels before the set is described as human-validated or frozen as the golden set.

### Why?

The 20-example pilot exposes unclear definitions early. Assistant proposals can reduce repetitive work, but final human validation is necessary because the assignment explicitly asks for a hand-labelled evaluation set and the labels determine every reported metric.

---

## Decision 017 - Should customer appreciation be a separate intent?

**Date:** 2026-09-16  
**Status:** Approved after the human pilot

### Question

Should genuine praise or thanks be separated from `other_or_ambiguous`?

### Answer

Yes. Add `13 = customer_appreciation` without changing the existing numbers 1-12.

### Why?

The user found two clear appreciation conversations in the first 20 examples. These messages need a different agent behavior from an unclear complaint: acknowledge the customer warmly instead of asking diagnostic questions or escalating.

### Boundary

Use appreciation only when no unresolved request remains. Sarcastic thanks such as “thanks for losing my package” must retain the underlying delivery intent.

### Pilot effect

Rows `GH-007` and `GH-014` move from label 12 to label 13. The other user-entered pilot labels remain preserved until the final consistency review.

---

## Decision 018 - How are the remaining 130 examples labelled and reviewed?

**Date:** 2026-09-16  
**Status:** Assistant proposals complete; awaiting user approval

### Question

How should assistant labels be added without overwriting the user's pilot or falsely treating model proposals as final ground truth?

### Answer

Preserve `eval/golden_set_review.csv` as the original user pilot. Write a separate `eval/golden_set_review_assistant_proposals.csv` containing:

- the 20 user pilot labels;
- the two approved appreciation updates from label 12 to label 13;
- 130 assistant-proposed labels;
- readable intent names;
- label-source metadata; and
- assistant review notes for pilot disagreements.

Assistant rows use `review_status = assistant_proposed`. The user changes that status only after accepting or correcting each proposal.

### English-scope correction

Three sampled rows were Spanish despite the lightweight language guard. They were replaced by the first three unused, reviewable English TEST cases in chronological case order:

```text
GH-043 -> case 2831688
GH-052 -> case 2830660
GH-088 -> case 2831668
```

### Verification

```text
Rows:                         150
Unique TEST threads:          150
User pilot rows:               20
Assistant-proposed rows:      130
Ambiguous rows:                18
Appreciation rows:             10
Represented numeric labels:  1-13
SHA-256: D147C63E1CD580F6003965BEEE51E641C63EC0DE38A69897CF16FC2E89399996
```

### Remaining human gate

The file must not be renamed to `golden_set.csv` or used for final reporting until the user reviews the 130 assistant proposals and resolves the pilot disagreements recorded in `assistant_review_note`.

---

## Decision 019 - What does the user's batch approval freeze?

**Date:** 2026-09-16  
**Status:** Implemented

### Question

After the user says “approved,” which labels should become the frozen evaluation snapshot?

### Answer

Freeze the 150 labels **as shown in the assistant-proposal CSV**, without silently changing the user's pilot decisions. Two pilot appreciation cases retain the previously agreed label 13. The other 18 pilot labels remain the user's own choices, including nine for which the assistant noted a possible alternative. The 130 assistant proposals are recorded as approved **in batch**, not individually hand-labelled.

### Why?

Keeping user choices and provenance prevents an unannounced reinterpretation of approval. A frozen copy and hashes prevent later label drift while comparing systems fairly.

### Verification

`scripts/freeze_golden_set.py` checked 150 valid number/name pairs, 150 unique threads, and TEST membership. It matched each row's thread ID, timestamp, and customer text to the original case. It refuses to overwrite an existing snapshot.

```text
Frozen file: eval/golden_set.csv
User pilot: 20
Assistant labels approved in batch: 130
Intent labels: 13
Pilot disagreement notes retained: 9
SHA-256: D0C286DE3DBF7778C4D9819563DE5E2AB036EC65E43A578AC06C5D5F44728980
```

### Limitations

The assignment calls for a hand-labelled evaluation set. Batch approval of 130 assistant labels must not be described as 150 examples individually hand-labelled by the candidate. The sample is delivery-heavy (66/150), while seller/marketplace appears once. The CSV also contains unredacted customer information from historical tweets and remains local-only, excluded from Git.

---

## Decision 020 - What is the simplest honest baseline comparison?

**Date:** 2026-09-16  
**Status:** Implemented

### Question

How can we build two small baselines without pretending TRAIN has verified intent labels or exposing users to unsafe historical replies?

### Answer

Use a fixed-intent baseline that always predicts `delivery_or_courier_issue`, plus a TF-IDF similarity baseline that compares the message against the 13 taxonomy definitions and searches a seeded sample of 5,000 TRAIN cases for one related historical case. Both return a generic safe reply and `ESCALATE`. The historical reply is returned only as reviewer evidence, not as the reply to send.

### Why?

TRAIN cases are not intent-labelled, so we cannot calculate a true majority TRAIN intent. Delivery is used as a transparent fixed guess because it was the strongest theme in the TRAIN keyword audit. TF-IDF gives a simple, reproducible non-LLM comparator. Always escalating avoids claiming a safety threshold was calibrated before DEV labels exist.

### Verification and limitation

`python scripts/run_baselines.py --train-sample 5000 --dev-sample 10` produced predictions on 10 DEV cases without using TEST. It surfaced several weak guesses, including an incorrect appreciation prediction for a complaint. No accuracy, F1, or auto-handle rate is claimed because DEV has no verified intent/escalation labels. Unit tests check determinism, TRAIN-only input, safe escalation, evidence IDs, and zero-similarity fallback. The full suite passed 21 tests.

---

## Decision 021 - How should the small-project retriever be designed?

**Date:** 2026-09-16  
**Status:** Proposed design; not implemented

### Question

How can we find useful historical support cases without adding unnecessary infrastructure?

### Answer

Use the same seeded 5,000 TRAIN cases as the TF-IDF baseline. Encode customer messages with the locally cached sentence-transformer once, then rank them in memory by cosine similarity. Return the top five case IDs, messages, replies, and scores. No vector database, web service, or intent-based filtering is needed at this stage.

### Why?

This is small enough for an in-memory search and gives a clear comparison with the simpler TF-IDF baseline on the same candidate pool. Historical replies are evidence for drafting, not ready-to-send customer answers.

### How will we know it works?

Unit-test ordering, `k=5`, empty queries, deterministic results, and TRAIN-only indexing. On about 25 DEV queries, judge the combined candidates from TF-IDF and embedding retrieval, then report Precision@1, Precision@5, pooled Recall@5, and latency. Keep the embedding retriever only if it materially improves the judged DEV results; leave the frozen TEST set untouched until final comparison.

---

## Decision 022 - Does the implemented embedding retriever earn its added cost?

**Date:** 2026-09-16  
**Status:** Provisional yes; implemented and tested on DEV

### Question

Should the local embedding retriever be kept instead of using only the simpler TF-IDF case search?

### Answer

Keep it provisionally. Both methods searched the same seeded 5,000-case TRAIN pool. In a 15-query DEV relevance pilot, the embedding method returned more cases with the same underlying problem.

### Evidence

```text
Metric                  Embedding     TF-IDF
Precision@1               0.667      0.133
Precision@5               0.587      0.213
Pooled Recall@5           0.860      0.184
Mean search latency      167 ms       5 ms
```

The local embedding build took 377 seconds on this machine; a repeat query using the saved cache took about 20 seconds including model startup. A full-pool query for “package says delivered but I cannot find it” returned five directly related cases, with top similarity 0.7659.

### Limitations

The 25 DEV candidates were deterministically sampled, but 10 were excluded from scoring because the message was Spanish, context-dependent, image-dependent, or lacked a clear issue. The remaining 15 were judged by the assistant using the criterion in `eval/retrieval_pilot_judgments.json`; this is a pilot, not independent human ground truth. One query had no relevant case in the judged pool, so pooled recall uses 14 queries. Similarity values are ranking scores, not calibrated confidence or proof that a reply is safe. The frozen TEST set was not used.

---

## Decision 023 - How should the blueprint show the remaining work?

**Date:** 2026-09-16  
**Status:** Documented

### Question

How can the flowchart stay readable while showing which modules are finished?

### Answer

Show conversation reconstruction, case extraction, masking, and the English-candidate guard as one **Feature engineering** block, with those details below the diagram. Keep thread-level splitting visible because it is the boundary that prevents train/test leakage. Label implemented modules `DONE`, the immediate next module `NEXT`, and unfinished modules `TODO`.

### Why?

The diagram should show the main module connections, not every preprocessing operation. Status labels also prevent an implemented DEV pilot from being mistaken for final evaluation. Module 0 reproducibility and Modules 7-12 remain open; the golden set and retriever have the stated validation caveats.

---

## Decision 024 - How should the flowcharts be displayed?

**Date:** 2026-09-16  
**Status:** Documented

### Question

How can the diagrams remain simple but be easier to read?

### Answer

Use a top-to-bottom layout with larger labels and more space between nodes. Keep the offline stages in one vertical sequence, and show the intent classifier and retriever as the two inputs to reply generation in the online diagram.

### Why?

The previous left-to-right layout spread the stages across the page and made their labels hard to read. The vertical view makes progress and dependencies clearer without adding implementation detail back into the boxes.

---

## Decision 025 - Which LLM should power the first intent-classifier module?

**Date:** 2026-09-16  
**Status:** Implemented; DEV quality gate pending

### Question

How can we classify customer messages into only the 13 approved intents while keeping the module small and testable?

### Answer

Use the already installed Google Gen AI Python SDK with `gemini-3.5-flash-lite`. Give it the approved taxonomy and require structured JSON with an intent from the 13-label enum, a confidence estimate, and a short reason. Validate the result again with Pydantic and an allowed-label check. The Groq key is not used in this module. Do not silently replace malformed or missing model output with a guessed intent.

### Why?

This uses the existing taxonomy directly and avoids a training pipeline for a small assignment. Google rejected the initially selected `gemini-2.5-flash-lite` model for this key with a 404 response and named `gemini-3.5-flash-lite` as its replacement. The model's confidence is not calibrated and cannot by itself authorize auto-handling.

### Verification and limitation

Four isolated classifier tests passed, and the complete project suite passed 29 tests. One live check used a synthetic missing-parcel message and returned `delivered_not_received` with valid JSON. No raw dataset case was sent in that check. This proves API wiring, not intent accuracy; independently verified DEV labels and a baseline comparison are still required before the Module 7 quality gate passes.

---

## Decision 026 - Does the intent classifier look better than the baselines on DEV?

**Date:** 2026-09-16  
**Status:** Provisional yes; human label review required

### Question

On a fixed held-out DEV sample, does the LLM classifier improve on both simple intent baselines?

### Answer

Provisionally yes. A seeded 20-case DEV sample was selected before model calls. One case was excluded because its context contained non-English customer text, leaving 19 assistant-labelled cases. The classifier matched 15/19 provisional labels (78.9% accuracy; macro F1 0.784 over the nine represented intents), compared with TF-IDF at 7/19 (36.8%; macro F1 0.489) and the fixed delivery guess at 6/19 (31.6%; macro F1 0.053). Full predictions are saved in `artifacts/intent_dev_pilot_results.json` and the readable disagreement sheet is `eval/intent_dev_pilot_review.md`.

### Why is this not the final quality claim?

The assistant assigned the DEV labels; a human has not verified them. Four of the 13 taxonomy intents are absent from this small sample. Two disagreements involve debatable taxonomy boundaries (cashback and packaging feedback). The classifier's four errors all carried reported confidence between 0.85 and 0.95, so confidence cannot yet be trusted for escalation. No TEST case or golden-set label was used to choose or score the classifier. The Module 7 quality gate remains open until the DEV labels are reviewed.

---

## Decision 027 - Is the golden intent dataset human-labelled now?

**Date:** 2026-09-16  
**Status:** Confirmed by user

### Question

Can the 150-row TEST intent set be described as human-labelled after the user reviewed the assistant proposals?

### Answer

Yes. The user reviewed all assistant-proposed rows, changed the intent numbers where needed, and verified the set. The current evaluation snapshot is `eval/golden_set_human_labelled.csv`. It contains 150 TEST cases and all 13 taxonomy intents.

### Audit trail

The earlier `eval/golden_set_review_assistant_proposals.csv` and `eval/golden_set.csv` files remain unchanged as historical records. Eight intent values differ between the reviewed proposal copy and the earlier frozen snapshot. The human-reviewed snapshot is the file to use for future intent evaluation.

### Limitation

This review verifies intent labels only. The file still does not contain human labels for escalation action, escalation reason, or expected resolution, so those metrics cannot be claimed yet.

---

## Decision 028 - How should escalation be handled without labelling all 150 cases?

**Date:** 2026-09-16  
**Status:** Implemented; real-data calibration pending

### Question

Do we need human escalation labels for every golden intent example, or can we use explicit safety instructions?

### Answer

Use a deterministic Python policy with explicit instructions also supplied to the future reply generator. Escalate payment, refund, account-security, personal-data, legal/safety, ambiguous, low-confidence, weak/no-evidence, missing-context, and unsupported-reply cases. Auto-handle only a clear low-risk case with strong evidence and a supported reply. Anger alone is not an automatic escalation reason.

### Why?

This keeps the small project understandable and ensures the LLM cannot overrule the human-in-the-loop boundary. The policy is easier to audit than a prompt-only decision. A separate 12-case synthetic safety fixture set now covers the hard rules and threshold boundaries; five policy tests pass. We will not claim escalation accuracy without human-labelled real cases, but we can still verify the rule behavior and report that limitation honestly.

---

## Decision 029 - How should the grounded reply generator handle evidence?

**Date:** 2026-09-16  
**Status:** Implemented; reply-quality gate pending

### Question

How can the LLM draft useful replies without inventing refunds, account actions, or delivery promises?

### Answer

Give Gemini the customer message, predicted intent, and retrieved historical cases. Require structured output containing the reply, support status, cited case IDs, an unsupported-claim flag, and a short support note. If no evidence exists, return a safe human-handoff reply without calling the model. Reject unknown evidence IDs, and locally flag refund/account/timeline commitments so the escalation policy can send them to a human.

### Verification and limitation

Five unit tests and one synthetic live API smoke test passed; the full suite passes 41 tests. The smoke test cited the supplied synthetic case and produced a supported delivery reply. This verifies output structure and safety checks, not final reply quality. DEV judging remains part of Module 11.

---

## Decision 030 - How should the tested modules be connected?

**Date:** 2026-09-16  
**Status:** Implemented; live pipeline gate pending

### Question

How can one request use the classifier, retriever, reply generator, and escalation policy without moving business logic into one large file?

### Answer

Use a thin `SupportAgent` orchestrator. It calls the classifier, searches TRAIN evidence with the retriever, asks the reply generator for a structured draft, and passes the draft plus signals to the deterministic policy. Return one validated `AgentResult` containing the intent, confidence, reply, evidence, decision, and reason. Expose the same flow through a small CLI.

### Verification and limitation

Four mocked end-to-end tests pass, the CLI help command works, and the full suite passes 45 tests. One live synthetic parcel example completed through the CLI: the classifier chose `delivered_not_received`, the retriever returned five TRAIN cases, the generator marked support insufficient, and the policy returned `ESCALATE` with `UNSUPPORTED_REPLY`. The orchestrator does not make independent safety decisions; Module 9 remains authoritative.

---

## Decision 031 - What should Module 11 evaluate and what must it refuse to claim?

**Date:** 2026-09-16  
**Status:** Implemented; final run pending

### Question

How can the evaluation harness produce reproducible evidence without mixing provisional labels, mismatched IDs, or unsupported escalation claims?

### Answer

Use the human-reviewed 150-row TEST intent snapshot as the default gold source. Require prediction IDs to match the gold IDs exactly before calculating accuracy, macro F1, weighted F1, and per-intent metrics. Save structured reply-judge outputs and aggregate relevance, groundedness, helpfulness, tone, safety, pass rate, and critical unsupported-claim rate offline. Compare about 50 blinded human ratings with judge ratings using Spearman correlation, Cohen's kappa, and raw agreement.

### Limitations

The harness does not invent escalation labels or expected resolutions. Until those are collected, it will not report escalation precision/recall or end-to-end success as if they were measured. The implementation is tested on fixtures, but the final 150-case system run and human/judge validation remain future work.

---

## Decision 032 - How should the first Groq evaluation run be scoped?

### Question

Should we run the next evaluation on all 150 examples and use Google, or use a smaller slice with Groq because of provider limits?

### Answer

Run the first 50 rows of the frozen human-reviewed set with Groq `openai/gpt-oss-20b`, checkpointing after every row. Keep the fixed and TF-IDF baselines in the same artifact so the comparison is fair.

### Why?

This gives us a quick, reproducible quality signal without spending the Google quota. The run is explicitly a top-50 slice, not a claim about the full dataset. The main pipeline scored 80% intent accuracy (40/50), versus 30% for the fixed baseline and 36% for TF-IDF. The slice is not balanced: delivery/courier cases make up 15 of 50 examples.

### What did we observe?

The deterministic policy escalated 34 cases and auto-handled 16. These are policy outputs, not measured escalation accuracy, because the golden set has no human escalation/action labels. Reply judging attempted all 50 cases, but Groq rate limits caused 21 judge failures and two malformed judge responses; two reply-generator failures were also safely escalated. Therefore the valid judge subset is only 25 cases and must not be presented as a full-dataset reply-quality score. The detailed evidence is in `artifacts/top50_metrics.json`, `artifacts/top50_reply_metrics.json`, and `reports/top50_evaluation_report.md`.

---

## Decision 033 - How should the available reply-review labels be recorded?

### Question

Should judge-passed replies be accepted as human-passed, and how should the remaining final rows be handled?

### Answer

Mark all 25 rows where the judge passed as human-approved with score 5. Label the final five rows directly: GH-046, GH-047, GH-049, and GH-050 pass with score 4; GH-048 fails with score 2 because its reply includes an unsupported specific email-date claim.

### Verification and limitation

The current `eval/top50_reply_human_review.csv` initially contained no earlier human labels, despite the expectation that most false rows had already been reviewed. The remaining 20 rows were then reviewed using the same standard. The completed sheet now contains 47 human passes and 3 human failures (GH-017, GH-035, and GH-048), with no blanks. The simple judge/human pass agreement is 28/50, but it is confounded by provider-error rows stored as judge failures; it should not be treated as a clean judge-validation result.

---

## Decision 034 - What remains in the final project scope?

### Question

Should we spend more API quota on judge-agreement analysis and a full 150-case run?

### Answer

Skip both. Keep the completed top-50 evaluation as the measured scope and finish failure analysis, offline reproduction, tests, and the final report.

### Why?

The user wants this to remain a small, focused project. The saved artifacts already support the headline top-50 result, while the judge output is provider-limited and the full run would add cost without changing the prototype architecture. The final report states these boundaries explicitly instead of presenting the prototype as fully production-validated.
