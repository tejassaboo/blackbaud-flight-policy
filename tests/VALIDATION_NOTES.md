# Validation notes: blackbaud-flight-policy (paid wave 1 validation v3, 2026-11-25)

Run: `efficient_corporate_travel_agent/pilot/ladder/runs/validation_w1v3_2026-11-25/blackbaud-flight-policy@w1v3/`,
arm `full`, DeepSeek V4 Flash (Nebius fp8 pinned), temperature 0, max_steps 6, max_tokens 8192, one run per
scenario, at plugin head 540c0b8 (after the approver rule 4' and the declined-request reason rule). Line numbers are
lines of `src/plugin/data/policy.txt`.

## Results

17/24 valid (70.8%), **easy 3/5** (cobalt-sedge and dune-larkspur fail). By category: boundary 6/6, distractor
1/2, easy 3/5, flag 0/3, hidden 2/2, multi 3/4, refusal 2/2. Re-scoring the stored submissions under the fixed keys
(this commit's verifier, no paid call) gives **19/24 (79.2%), easy 3/5**: the two easy failures are slips and stay
wrong.

## Every failure, classified

| scenario | category | submitted vs key | class | evidence |
|---|---|---|---|---|
| cobalt-sedge | **easy** | United economy U7RF-KX5B ($846), LOWEST_FARE; key British Airways economy ($798) | model slip | The search showed BA 1956 economy at 79800 cents. The model wrote "The lowest fare available: United economy UA 620 at $846 ... That's the lowest fare overall too", so it misread the fare list and never reached lines 442-444. The 2026-11-24 run failed the same case another way (it quoted lines 443-444 and booked United anyway). The key is right: the traveller asks for economy, and a loyalty programme may not add cost beyond the lowest available airfare (lines 442-444). |
| dune-larkspur | **easy** | Delta economy EY2M-EQNJ ($912), LOWEST_FARE; key ANA economy KHAV-9XH3 ($887) | model slip | "The cheapest economy offer is Delta EY2M-EQNJ at $912.00 (nonstop). That's the lowest fare." ANA NH 874 at 88700 cents was in the same search result, seated and nonstop. The model scanned the list wrongly. The request ("economy, cheapest you can find") and the key agree. |
| nectar-pine | multi_rule | right offer (BA economy $615), clause LOWEST_AIRFARE; reason LOYALTY_PROGRAM_PREFERENCE; key LONG_FLIGHT_CONDITION_NOT_MET, UPGRADE_NOT_ELIGIBLE or LOWEST_FARE | **grader defect (narrow)** | It found line 433 ("upgradeable fares, are not allowed to be booked") and declined the $795 upgradeable fare, "citing the loyalty-program preference as the reason the requested fare was not selected". The traveller wants the dearer fare "that I can upgrade later with my miles", and lines 442-444 say frequent flier participation "may not influence selection that may result in any incremental cost to the company beyond the 'lowest available airfare'". That ground fits the request, and cobalt-sedge keys the same code on the same lines. |
| saffron-knoll | distractor | REFUSE, DRIVING_EXPECTED; key BOOK Delta $176 | model slip | It read "consideration must be given to driving instead of flying" (lines 383-384) as "driving is expected ... so we refuse". The traveller says he considered driving and would rather fly, so the condition is met. This is the same slip as the 2026-11-24 run. |
| vellum-ash | flag | BOOK economy, LONG_FLIGHT_CONDITION_NOT_MET; key FLAG business | model slip | "The flying minutes are 380 minutes = 6.33 hours ... less than 8 hours". It quoted "(whether a single segment or multiple segments combined)" (lines 402-404) but never asked whether the 115-minute connection counts (495 minutes with it). It took one reading as settled. Twins heron-bluff and iris-tundra passed. |
| willow-fen | flag | BOOK the upgradeable ANA fare, INTERNATIONAL_LONG_FLIGHT; key FLAG it | model slip | It quoted both line 433 ("upgradeable fares, are not allowed to be booked") and lines 402-404 ("can be booked in an upgradeable fare"), then settled on the second, "So the upgradeable fare is allowed", without weighing which line governs. The handbook states no order between them. Twins nectar-pine and ember-quarry passed. |
| yew-hollow | flag | right hold, offer, cabin, approver (VICE_PRESIDENT), clause; reason LONG_FLIGHT_CONDITION_NOT_MET; key APPROVAL_REQUIRED only | **grader defect (narrow)** | "business class requires prior approval of the traveler's Vice-President ... The condition (VP approval) is not met. So LONG_FLIGHT_CONDITION_NOT_MET fits. Alternatively, APPROVAL_REQUIRED. But LONG_FLIGHT_CONDITION_NOT_MET is more specific." Lines 402-404 make the VP's prior approval part of the long-flight condition for business, so the code names the missing piece. Anixter heron-scree accepts the code of the unmet authorization on its hold for the same reason (APPROVER_REVIEW section 3). The hold, the offer and the awaited role still carry the handbook content. |

## Fixes (this commit)

`src/plugin/rules.py` and the byte-identical `verifier/rules.py`, `tests/build_scenarios.py`, README rows,
regenerated scenario JSON. No id, world, request, decision or category changed.

1. **Declined upgradeable fare within the limit (nectar-pine, the only case of the branch):** `LOYALTY_PROGRAM_PREFERENCE`
   and the `FREQUENT_FLIER` section are accepted beside the existing codes and sections.
2. **Business hold for a missing VP approval (yew-hollow, the only case of the branch):** `LONG_FLIGHT_CONDITION_NOT_MET`
   is accepted beside `APPROVAL_REQUIRED`.

Not loosened: cobalt-sedge, dune-larkspur, saffron-knoll, vellum-ash, willow-fen.

Cross-plugin items: long-flight business already accepts both `LONG_FLIGHT_APPROVED` and `INTERNATIONAL_LONG_FLIGHT`.
No key books a connection that declines a requested nonstop. basil-cove's connection declines nothing, so the route
codes do not apply.

## Q2

The always-cheapest agent books the cheapest seat with `LOWEST_FARE`, and nectar-pine already accepted that answer.
Its count is unchanged: **9/24 (38%)** (amber-wren, basil-cove, cobalt-sedge, dune-larkspur, jasper-glen,
nectar-pine, quill-aspen, raven-dell, saffron-knoll; `MAX_PASS_ALWAYS_LOWEST = 9`). Both easy failures are cases
this agent passes: the model missed the cheapest fare in the list. The always-flag agent is unaffected
(`UNCLEAR_POLICY_TEXT` is still not accepted on yew-hollow).

## Re-run

No record or request changed, so no run is strictly required, and both fixes re-score valid. The easy bar is still
unmet on this run's evidence (3/5), so the two easy cases should be re-run:

- **cobalt-sedge and dune-larkspur** (easy; both are slips, and the bar needs them valid). cobalt-sedge has now failed
  in two paid runs in a row, in two different ways, both drawn by the United request. If it fails again, the lead
  should consider whether it is a distractor case rather than an easy one. That would be a category change, not a
  key change.
- Optional: nectar-pine and yew-hollow (confirm the fixes), saffron-knoll (the same slip twice).

## Checks

`uv run pytest -q` (214 passed), `uv run ruff check .`, `uv lock --check`, `check_shared.py`,
`tools/stock_verify.py` (24 scenarios, 0 failures), stock `nanoagent plugin inspect .` (exit 0).
