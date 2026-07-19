You are running the quarterly CPI calibration review.

$pcm_block

## Decisions this quarter
$decisions_block

## Human score adjustments (draft vs final deltas)
$adjustments_block

## Spot-check reversals (signals wrongly discarded by triage)
$reversals_block

## Missed developments reported by the team, with the stage that failed
$missed_block

## Source scorecard (triage outcomes per configured source)
$scorecard_block

Produce a markdown report with these sections:
1. **Systematic scoring biases** — factors where drafts consistently diverge from human finals, with the direction and size of the bias.
2. **Proposed weight adjustments** — current weights are $weights_json; propose changes only where the evidence supports them, with one-line reasoning each. Weights must still sum to 1.0.
3. **Triage prompt corrections** — patterns in the reversals worth encoding as few-shot examples.
4. **PCM updates to consider** — watch themes to add (from funded probes and misses) or non-goals to add (from kills).
5. **Source changes to consider** — from the scorecard: sources that only produce discards (candidates to drop or re-query) and source classes that are under-represented among advanced signals.
6. **Process health** — disagreement rate between drafts and finals (near-zero is a red flag: it means review is rubber-stamping).
