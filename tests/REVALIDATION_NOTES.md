# Re-validation of 2026-11-24 (evening): failures and fixes

Run: `efficient_corporate_travel_agent/pilot/ladder/runs/revalidation_2026-11-24/`, `blackbaud-flight-policy@v2`, at
2ecadad. 22 scored runs (`tansy-reef` and `willow-fen` got a provider 429 and were not scored): 16/22 valid
(72.7%), easy 4/5, mean field score 0.902, 1/22 over the hosted 65,536 cap (stop before step 5).

## Approver amendment (template SYNC_NOTES 4')

A BOOK that rests on a sign-off already on file now accepts that role and `NONE` (`rules.relied_on`, in
`src/plugin/rules.py` and the byte-identical `verifier/rules.py`; `tests/build_scenarios.py` regenerated the
JSON). Holds still accept only the awaited role (`yew-hollow`: `VICE_PRESIDENT`; `vellum-ash`
unchanged). The unused-sign-off rule 4(b) is unchanged; no Blackbaud case tests an invalid sign-off.

Scenarios whose key changed (approvers only, no world change):

- `ember-quarry`, `fennel-ridge`, `heron-bluff`, `moss-harbor`: `VICE_PRESIDENT` or `NONE`
- `lilac-ferry`: `TRAVEL_DEPARTMENT`, `VICE_PRESIDENT` or `NONE`
- `quill-aspen`: `SENIOR_VICE_PRESIDENT` or `NONE`

`MAX_PASS_ALWAYS_LOWEST` goes from 11 to **12** (measured): `quill-aspen` books the lowest fare with LOWEST_FARE
accepted, so the always-cheapest agent now passes it.

## Every failure, classified

| scenario | category | submitted vs key | class | evidence | fix |
|---|---|---|---|---|---|
| lilac-ferry | multi_rule | approver NONE; key TRAVEL_DEPARTMENT or VICE_PRESIDENT (rest right) | approver rule alone | Both medical approvals are on file; the model booked on them and answered NONE. | 4' (NONE accepted) |
| quill-aspen | hidden_clause | approver NONE; key SENIOR_VICE_PRESIDENT (rest right) | approver rule alone | The SVP's advance authorization of the companion is on file; booked on it, answered NONE. | 4' (NONE accepted) |
| cobalt-sedge | **easy** | BOOK United U7RF-KX5B ($846), LOYALTY_PROGRAM_PREFERENCE; key BA Y53Z-W7C9 ($798) | model slip | It quoted lines 443-444 ("may not influence selection that may result in any incremental cost to the company beyond the 'lowest available airfare'") and booked the $48 dearer United fare anyway because "the premium is small (~6%)". The handbook names no preferred carrier, so line 438 does not help United. | none |
| nectar-pine | multi_rule | BOOK the upgradeable W5LH-CKC8 ($795), TRAVELER_PAYS_UPGRADE, FREQUENT_FLIER; key ULCL-S2DU ($615) | model slip | It found "this flight is 6.75 hours, under 8 hours. So the upgradeable fare isn't permitted by the international long-flight clause" (lines 402-404) and that the fare is $180 above the lowest (412-413), then booked the upgradeable fare because the trip record lists it. Line 433 ("upgradeable fares, are not allowed to be booked") is never weighed. The key is right. | none |
| saffron-knoll | distractor | REFUSE, DRIVING_EXPECTED; key BOOK delta-economy, LOWEST_FARE | model slip | It read lines 383-384 right ("'consideration must be given' - not strictly prohibited") and saw that the traveller had considered driving, then refused "given the available reason codes" and the 490-mile round trip. Lines 664-665 are about car mileage over 500 miles, not a duty to drive. That distractor is what the case tests. | none |
| vellum-ash | flag | BOOK business, INTERNATIONAL_LONG_FLIGHT, NONE; key FLAG / UNCLEAR_POLICY_TEXT | model slip | It set out both readings of "exceeding 8 hours (whether a single segment or multiple segments combined)" (lines 402-403): flying 380 minutes, elapsed 495. Then "Given the combined travel including layover exceeds 8 hours ... I'll consider it qualifies". It took one reading and did not flag. This is the same pattern as Thornton's ember-trellis. | none |

No scenario or grader defect was found. Expected after the fix on the same answers: 18/22 valid.

## Checks

`uv run pytest -q` (214 passed), `uv run ruff check .`, `uv lock --check`, `python3 ../_template/check_shared.py .`
(ok), `tools/stock_verify.py` with the NanoAgent venv (24 scenarios, 0 failures). `world.py` and every scenario
world are unchanged, so `world_diff.py` has nothing to report.
