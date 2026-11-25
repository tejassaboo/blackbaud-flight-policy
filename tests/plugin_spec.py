"""The handbook-specific settings the template's acceptance tests read. Every other file in tests/ is the
template's and stays identical across plugins (see TEMPLATE_GUIDE.md)."""

from pathlib import Path

import contract

ROOT = Path(__file__).resolve().parents[1]

# Ids that are published or taken: a new plugin never reuses one (MASTER_PLAN section 4, "id check").
PUBLISHED_IDS = {
    "aiib-delegation-entitlement", "ec-mission-cabin-allowance", "ftr-city-pair-fare-selection",
    "gates-vendor-flight-ranking", "njc-cabin-meal-allowance", "sfc-travel-preapproval", "uc-g28-expense-audit",
    "un-staff-air-travel-audit", "vt-airfare-policy-booking", "wa-saam-travel-versioned-audit",
    "energy-corporate-flight-booking", "pharma-distributor-flight-booking", "shipping-company-flight-booking",
    "telecommunications-flight-booking", "preference-aware-flight-booking", "llm-context-compress",
    "weather-alert", "word-check", "arxiv-source",
}

# The frozen original's SHA256SUMS, when this checkout sits beside pilot_work/ (skipped elsewhere).
FROZEN_SHA256SUMS = ROOT.parents[1] / "pilot_work" / "originals" / "blackbaud" / "frozen" / "SHA256SUMS"

# Scenario mix by primary category (EDGE_CASES.md section 5.2; the 24-scenario row).
MIX = {"easy": 5, "boundary_twin": 6, "multi_rule": 4, "hidden_clause": 2, "distractor": 2, "refusal": 2, "flag": 3}

# Overlay minimums (EDGE_CASES.md section 5.3) for the rules this handbook has. The handbook has no
# overnight-stop rule, so no overnight scenario is required.
OVERLAY_MINIMUMS = {
    "multi_leg": 3, "date_arithmetic": 2, "month_end": 1, "personal_travel": 1, "multi_traveller": 1,
    "dearer_option": 2, "upgrade_not_taken": 2, "outside_air_section": 2,
}

# Words a scenario id may not contain beyond the template's universal list: this handbook's rule and role
# terms.
ID_FORBIDDEN_TERMS = {
    "spouse", "companion", "vacation", "personal", "family", "holiday", "medical", "surgery", "leadership", "executive",
    "team", "loyalty", "miles", "status", "refundable", "nonrefundable", "upgradeable", "domestic", "international",
    "lounge", "drive", "driving", "car", "double", "backup", "hawaii", "layover", "connection", "segment", "segments",
    "combined", "vice", "president", "senior", "director", "advance", "notice", "frequent", "flier", "coach",
    "nonstop", "desk", "ceo", "cfo", "approval", "signoff",
}

# The handbook-specific enums whose member words a scenario id may not contain either.
ID_CATEGORY_ENUMS = [contract.Passenger, contract.Purpose, contract.SignOffSubject]

# How many scenarios a degenerate agent may pass: one that always holds the right offer for approval, and
# one that always books the cheapest seat (with the right section).
MAX_PASS_ALWAYS_FLAG = 2
MAX_PASS_ALWAYS_LOWEST = 12  # 11, plus quill-aspen once NONE is accepted beside the companion sign-off on file (SYNC_NOTES 4')

# Hand-built duration cases beyond the automatic both-sides tests: (rule, outbound scheduled minutes per
# flight, layovers, expected True / False / None for unclear).
DURATION_CASES = [
    ("international-long", [481], [], True),
    ("international-long", [480], [], False),
    ("international-long", [215, 285], [70], True),  # flights combined exceed the limit: over on every reading
    ("international-long", [241, 240], [200], True),
    ("international-long", [175, 205], [100], False),  # whole journey, ground time included, within: not over
    ("international-long", [175, 205], [101], None),  # flights within, journey over: does ground time count?
    ("international-long", [240, 240], [55], None),  # flights total exactly 480, journey 535
    ("international-long", [100, 150, 200], [60, 60], None),
    ("international-long", [100, 150, 231], [60, 60], True),
    ("arrival-lounge", [480], [], True),  # inclusive: "eight hours or greater"
    ("arrival-lounge", [479], [], False),
    ("arrival-lounge", [480, 60], [55], True),  # one flight at the limit
    ("arrival-lounge", [300, 120], [55], False),  # journey 475, under the limit
    ("arrival-lounge", [300, 179], [60], None),  # no flight at the limit, journey 539
]
