# Blackbaud Travel Policy Flight Booking

**No affiliation with Blackbaud, Inc.** The handbook is the company's *Travel Policy* (February 2014), a PDF a
travel agency hosted publicly, bundled verbatim for research. Do not publish this plugin before the course staff
confirm that a verbatim corporate handbook may be redistributed (MASTER_PLAN section 4: corporate plugins wait for
the instructor's answer).

A `nanoagent.plugin/v0001` plugin. An agent handles one traveller's flight request under the company's real travel
policy: it reads the trip record, searches a simulated flight world and submits **BOOK**, **REFUSE** or
**FLAG_FOR_APPROVAL** with the offer, cabin, reason, approver and policy section. A deterministic Python verifier,
with no LLM, rebuilds the offers and the policy's answer itself and checks every field. Built from the
original-handbook template (`handbook_plugins/_template`); `tests/build_scenarios.py` writes the scenario files.

## The handbook and the harness flag

The frozen text (`src/plugin/data/policy.txt`, 9,397 words, 1,095 lines, sha256 `9425eef7...df1b87c`, equal to
`pilot_work/originals/blackbaud/frozen/SHA256SUMS`) is never paraphrased, and the task text restates no rule. Under
stock NanoAgent the agent does not see it: the plugin then runs as the `off` baseline. The `harness.policy` switch
of the NanoAgent fork (github.com/tejassaboo/nanoagent, branch `policy-switch`) adds it to the system prompt:
`harness.policy: full` adds all of it, and the selection methods add parts of it. These plugins are meant to run
with `query: instructions+input`, so a selector sees the traveller's request.

**Size.** At 1.33 tokens a word the policy alone is about 12,500 tokens. Under `full` the first call carries about
14,000 input tokens (policy; task instructions, tool input schemas and the submit schema about 1,450 at 4
characters a token; the request), the second about 14,300 (plus the trip record) and the third 14,900 to 16,700
(plus the search results, 3 to 12 offers). A run makes 3 calls (`get_trip`, `search_flights`, `submit`): 43,200 to
45,000 input tokens per run, output tokens not counted. If the harness also shows the tools' output schemas, add
about 3,000 a call (52,000 to 54,000 a run). Either way a 3-call run stays under the hosted cap of 65,536 total
tokens, with about 11,000 to 22,000 to spare. Calibrated on the paid Thornton and NJC validation runs (DeepSeek
tokens, about 0.2 a character of handbook plus 1,800), the first call is about 14,500. NanoAgent checks the cap
before each step, and after `submit` it makes one more call for the final message, which starts at about 48,000
to 50,000 and so still runs. A repeated search is different: it pushes the total before `submit` to about 67,000,
over the cap, so a hosted run with one extra tool call stops before it submits.

## Task

- **Input:** `TaskInput`: `scenario` (one of 24 case ids) and `request`, the traveller's own words.
- **Steps:** `get_trip`, then `search_flights` on the trip's route and date (with the return date for the one
  round trip), then `submit`.
- **Output:** `BookingOutput`: `decision`, `offer_id` (empty when refusing), `cabin` (`NONE` when refusing),
  `reason_code`, `approver` and `clause`, each from a closed list. The reason list is the template's shared list
  (codes for rules this policy lacks) plus `DOUBLE_BOOKING_PROHIBITED` and `COMPANION_TRAVEL_AUTHORIZED`, and decoy codes from other handbooks' rules. Fares
  are in cents of US dollars (`currency: USD`).
- **Success:** every field is one the answer key accepts; the cabin is graded as the chosen offer's own. Score =
  fields right / 6.
- **No hidden facts:** no scenario has `answer_key_inputs`. Facts the policy needs that a booking tool would not
  show by itself are in the trip record: colleagues already ticketed on a flight (and whether they sit on the
  Executive Leadership Team), a ticket already held, and which listed economy fares the airline's fare rules mark
  upgradeable (the world's offers carry no fare-brand field).

| Scenario | Category | Expected decision (offer, cabin) | Reason | Approver | Clause (frozen lines) |
|---|---|---|---|---|---|
| `amber-wren` | easy | BOOK (mid-economy; ECONOMY) | LOWEST_FARE | NONE | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE (397-398, 412-413) |
| `basil-cove` | easy | BOOK (denver-economy; ECONOMY) | LOWEST_FARE | NONE | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE (397-398, 412-413, 426-429) |
| `cobalt-sedge` | easy | BOOK (british-economy; ECONOMY) | LOWEST_FARE or LOYALTY_PROGRAM_PREFERENCE | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS or LOWEST_AIRFARE or FREQUENT_FLIER (402-404, 412-413, 442-444) |
| `dune-larkspur` | easy | BOOK (ana-economy; ECONOMY) | LOWEST_FARE | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS or LOWEST_AIRFARE (402-404, 412-413) |
| `ember-quarry` | easy | BOOK (ana-business; BUSINESS) | INTERNATIONAL_LONG_FLIGHT or LONG_FLIGHT_APPROVED | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS (402-404) |
| `fennel-ridge` | boundary_twin | BOOK (delta-business; BUSINESS) | INTERNATIONAL_LONG_FLIGHT or LONG_FLIGHT_APPROVED | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS (402-404) |
| `garnet-moor` | boundary_twin | BOOK (delta-economy; ECONOMY) | LONG_FLIGHT_CONDITION_NOT_MET or UPGRADE_NOT_ELIGIBLE | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS or LOWEST_AIRFARE (402-404, 412-413) |
| `heron-bluff` | boundary_twin | BOOK (morning-business; BUSINESS) | INTERNATIONAL_LONG_FLIGHT or LONG_FLIGHT_APPROVED | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS (402-404) |
| `iris-tundra` | boundary_twin | BOOK (morning-economy; ECONOMY) | LONG_FLIGHT_CONDITION_NOT_MET or UPGRADE_NOT_ELIGIBLE | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS or LOWEST_AIRFARE (402-404, 412-413) |
| `jasper-glen` | boundary_twin | BOOK (jetblue-economy; ECONOMY) | LOWEST_FARE | NONE | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE or TRAVELING_TOGETHER (286-288, 397-398, 412-413) |
| `kelp-meadow` | boundary_twin | BOOK (delta-economy; ECONOMY) | LOWEST_FARE or TRAVELLER_LIMIT_PER_FLIGHT | NONE | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE or TRAVELING_TOGETHER (286-288, 397-398, 412-413) |
| `lilac-ferry` | multi_rule | BOOK (afternoon-business; BUSINESS) | MEDICAL_NEED | NONE or TRAVEL_DEPARTMENT or VICE_PRESIDENT | CLASS_OF_SERVICE or DOMESTIC_CLASS (397-398, 398-399) |
| `moss-harbor` | multi_rule | BOOK (delta-business; BUSINESS) | INTERNATIONAL_LONG_FLIGHT or LONG_FLIGHT_APPROVED or REFUNDABLE_FARE_NOT_ALLOWED | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS or LOWEST_AIRFARE (402-404, 432) |
| `nectar-pine` | multi_rule | BOOK (british-economy; ECONOMY) | LONG_FLIGHT_CONDITION_NOT_MET or LOWEST_FARE or UPGRADE_NOT_ELIGIBLE | NONE | CLASS_OF_SERVICE or INTERNATIONAL_CLASS or LOWEST_AIRFARE (402-404, 412-413, 433) |
| `onyx-brook` | multi_rule | BOOK (american-economy; ECONOMY) | LOWEST_FARE or REFUNDABLE_FARE_NOT_ALLOWED | NONE | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE (397-398, 412-413, 432) |
| `pearl-thistle` | hidden_clause | BOOK (sanfrancisco-economy; ECONOMY) | LONG_FLIGHT_CONDITION_NOT_MET or UPGRADE_NOT_ELIGIBLE | NONE or VICE_PRESIDENT | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE (397-398, 412-413, 426-429) |
| `quill-aspen` | hidden_clause | BOOK (morning-economy; ECONOMY) | COMPANION_TRAVEL_AUTHORIZED or LOWEST_FARE | NONE or SENIOR_VICE_PRESIDENT | LOWEST_AIRFARE or SPOUSE_COMPANION (267-271, 412-413) |
| `raven-dell` | distractor | BOOK (jetblue-economy; ECONOMY) | LOWEST_FARE | NONE | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE or ADVANCE_PURCHASE (397-398, 408-409, 412-413) |
| `saffron-knoll` | distractor | BOOK (delta-economy; ECONOMY) | LOWEST_FARE | NONE | CLASS_OF_SERVICE or DOMESTIC_CLASS or LOWEST_AIRFARE or AIR_TRAVEL_GENERAL (382-384, 397-398, 412-413) |
| `tansy-reef` | refusal | REFUSE (none; NONE) | OUTSIDE_POLICY_SCOPE or PERSONAL_TRAVEL_NOT_COVERED | NONE | PERSONAL_VACATION or RESPONSIBILITY (128-129, 296-298) |
| `umber-crest` | refusal | REFUSE (none; NONE) | DOUBLE_BOOKING_PROHIBITED or NO_COMPLIANT_OFFER | NONE | DOUBLE_BOOKINGS (455) |
| `vellum-ash` | flag | FLAG_FOR_APPROVAL (morning-business; BUSINESS) | UNCLEAR_POLICY_TEXT | NOT_NAMED or TRAVEL_DEPARTMENT or VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS (139-141, 402-404) |
| `willow-fen` | flag | FLAG_FOR_APPROVAL (ana-flex; ECONOMY) | UNCLEAR_POLICY_TEXT | NOT_NAMED or TRAVEL_DEPARTMENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS or LOWEST_AIRFARE (139-141, 402-404, 433) |
| `yew-hollow` | flag | FLAG_FOR_APPROVAL (korean-business; BUSINESS) | APPROVAL_REQUIRED | VICE_PRESIDENT | CLASS_OF_SERVICE or INTERNATIONAL_CLASS (402-404) |

Mix (EDGE_CASES.md 5.2, 24 row): 5 easy, 6 boundary twins, 4 multi-rule, 2 hidden clause, 2 distractor, 2
refusal, 3 flags (12.5%; the 15% cap is 3). Decisions: 19 BOOK (6 business, 13 economy), 2 REFUSE, 3
FLAG_FOR_APPROVAL. Twin pairs: 481 against 480 minutes on nonstops (`fennel-ridge`, `garnet-moor`); segments
combined, Houston at 500 flying minutes against Miami at 380 flying and 480 elapsed (`heron-bluff`,
`iris-tundra`); three against four leadership-team members on one flight (`jasper-glen`, `kelp-meadow`).

Each unclear point of the text is one flag with clear twins on both sides:

- **A gap.** "exceeding 8 hours (whether a single segment or multiple segments combined)" does not say whether the
  ground time between segments counts. `vellum-ash` (380 flying minutes, 495 elapsed) is the only scenario where
  the two readings differ; twins `heron-bluff` (over on both readings) and `iris-tundra` (within on both).
- **A contradiction.** Lines 402-404 say international travel over 8 hours "can be booked in an upgradeable
  fare"; line 433 says "Full Y fares, or upgradeable fares, are not allowed to be booked", with no stated order.
  `willow-fen` (755 minutes, upgradeable fare asked for) holds it; twins `nectar-pine` (405 minutes: line 433
  alone applies, the lowest fare) and `ember-quarry` (over 8 hours with the Vice-President's approval, asking for
  business, which no line forbids).
- **Approval required.** `yew-hollow`: a director, not the traveller's Vice-President, approved business on a
  680-minute flight; hold the business fare for the Vice-President (never "no compliant offer"). Twins
  `ember-quarry` (approved: book business) and `garnet-moor` (480 minutes: economy whoever approved).

Accept sets: on BOOK and REFUSE every defensible code is accepted beside the specific one (`LOWEST_FARE` beside
`TRAVELLER_LIMIT_PER_FLIGHT`, `REFUNDABLE_FARE_NOT_ALLOWED` or `LOYALTY_PROGRAM_PREFERENCE`; `UPGRADE_NOT_ELIGIBLE`,
`LONG_FLIGHT_CONDITION_NOT_MET` and `LOWEST_FARE` for a business request that fails; `OUTSIDE_POLICY_SCOPE` beside
`PERSONAL_TRAVEL_NOT_COVERED`; `NO_COMPLIANT_OFFER` beside `DOUBLE_BOOKING_PROHIBITED`), and the sections are the
class-of-service heading, its domestic or international subheading and the lowest-airfare section, plus the
section of any rule the trip touches. The approver is `NONE` unless a sign-off is relied on or awaited; where a sign-off is on file
but the decision does not use it (a business sign-off on an economy booking: `cobalt-sedge`, `dune-larkspur`,
`garnet-moor`, `iris-tundra`, `pearl-thistle`), that role is accepted beside `NONE`. A BOOK that rests on a sign-off
already on file accepts its role and `NONE` too (`ember-quarry`, `fennel-ridge`, `heron-bluff`, `moss-harbor`,
`lilac-ferry`, `quill-aspen`); a hold for a sign-off not yet given (`yew-hollow`) accepts only the awaited role. A hold over unclear words
accepts `NOT_NAMED` or `TRAVEL_DEPARTMENT` (lines 139-141 send policy questions to the Travel Desk), and
`vellum-ash` also `VICE_PRESIDENT`, whose sign-off on file the held business fare relies on. REFUSE means the company buys no ticket at all for the request.

**Duration (`rules.over`).** "international-long": the outbound (and, for a round trip, the return) direction's
segment minutes added together, strictly over 480 ("exceeding 8 hours (whether a single segment or multiple
segments combined)", lines 402-404); over on every reading when the flying minutes exceed 480, within on every
reading when the elapsed journey with its ground time is 480 or less, otherwise unclear (`None`). It applies to
international trips only: line 397 makes domestic air coach "regardless of flight time" (`pearl-thistle`, Boston
to Honolulu, 690 minutes). "arrival-lounge" (lines 544-547, "eight hours or greater", inclusive, per flight) is
coded and tested but decides no answer field; `garnet-moor` shows it does not change the cabin. Background offers
are on (3 per search, and only on a scenario's own search: `handbook.json` `background_offers` is 0, so a search
the case does not pin lists nothing and says so) except where an itinerary could fall on the other side of 480 minutes: every international
scenario whose answer depends on the limit sets `background: 0`, and `rules.solve` raises if offers on one search
disagree on the limit.

Degenerate agents (`tests/test_verifier.py`): one that always holds the right offer as unclear passes 2 cases
(`vellum-ash`, `willow-fen`); one that always books the cheapest seat with `LOWEST_FARE`, `NONE` and the right
section passes 9 (the cheapest-economy cases where nothing asked for is declined on another ground; it fails every
business, refusal, hold, refundable and leadership-team case). A booking that declines what the traveller asked
for gives the reason the request is declined (the task says so), and accepts `LOWEST_FARE` only where the
lowest-fare rule is that reason.

## Tools

| Tool | Does | Code |
|---|---|---|
| `booking_requirements` | The trip record's fields, the world's conventions (local times, dates, fares, sold-out seats) and its airports | `src/plugin/guide.py` |
| `get_trip` | A case's request and trip record: traveller, route, dates, purpose, requested cabin and fare, sign-offs, colleagues' flights, tickets held, fare rules, driving time | `src/plugin/tools.py` |
| `search_flights` | Every offer on a route and local date (one way, or round trip with `return_date`): the pinned scenario offers plus seeded background offers on those searches only; a search the case does not pin lists nothing and says so | `src/plugin/world.py` |
| `solve_booking` | The answer key (`rules.solve`), the agent task's `reference`, never shown to the agent | `src/plugin/rules.py` |

| Task | Does | Runner |
|---|---|---|
| `book-blackbaud-flight` | Handles one booking request | `agent`, with `get_trip` and `search_flights`; reference `solve_booking` |
| `booking-requirements` | Shows `booking_requirements` | `tool` |
| `search-flights` | Shows `search_flights` | `tool` |

## Layout

- `contract.py`: the template's shared contract plus this policy's scenario ids, approvers, sections, two reason
  codes and trip record.
- `src/plugin/`: `world.py`, `scenarios.py`, `guide.py`, `answer.py`, `tools.py` (shared), `rules.py` (this
  policy's rules, citing frozen lines), `__main__.py`.
- `src/plugin/data/`: `policy.txt` (frozen), `handbook.json`, `scenarios/*.json`.
- `verifier/`: byte-identical copies of the shared modules and `rules.py`, plus `booking.py` and `tools.py`.
- `tests/`: the template's acceptance suite; `tests/plugin_spec.py` holds this policy's settings.
- `tests/build_scenarios.py`: writes the scenario files (an authoring aid, not a test).

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
uv lock --check
python3 ../_template/check_shared.py .
# from a NanoAgent checkout (read-only use):
nanoagent plugin inspect <this folder>
nanoagent plugin pack <this folder> /tmp/blackbaud-flight-policy.tar.gz
# from this folder, with that checkout's Python:
/path/to/nanoagent/nanoagent/.venv/bin/python ../_template/tools/stock_verify.py
```

Offline: `hosts: []`, an empty `.env`, `write: []`, no clock (each case fixes its `booking_date`).
