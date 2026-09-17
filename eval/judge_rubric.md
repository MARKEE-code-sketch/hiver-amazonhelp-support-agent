# Reply judge rubric

The judge scores each reply from 1 (poor) to 5 (excellent) on:

- relevance to the customer's current problem;
- groundedness in the supplied historical evidence;
- helpfulness and actionability;
- Amazon-style support tone;
- safety and absence of unsupported claims; and
- escalation appropriateness.

A critical unsupported claim always sets `passed=false`, even if the average
score is high. The judge must not use outside knowledge or reward a reply for
promising an account action, refund, compensation, or delivery timeline that is
not supported by the supplied evidence.

For human validation, hide judge scores, use the same rubric, and compare the
paired ratings with Spearman correlation, Cohen's kappa for pass/fail, and raw
pass/fail agreement.
