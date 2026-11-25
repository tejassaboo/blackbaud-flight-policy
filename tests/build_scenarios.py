"""Writes the Blackbaud scenario JSON files (an authoring aid, not a test; the JSON files are the truth).

    uv run python tests/build_scenarios.py

Flight numbers that a trip record refers to (colleagues' flights, a ticket already held, an upgradeable fare)
are read from the shared world, so they match what search_flights lists. Expected answers are hand-written
here; tests/test_scenarios.py checks them against rules.solve.
"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from plugin.world import pinned_offers

POLICY = (ROOT / "src/plugin/data/policy.txt").read_text(encoding="utf-8").split("\n")
OUT = ROOT / "src/plugin/data/scenarios"


def norm(text):
    return " ".join(text.split())


def keep(a, b, quote, why):
    text = norm(" ".join(POLICY[a - 1:b]))
    quote = text if quote is None else quote
    assert norm(quote) in text, (a, b, quote, text)
    return {"lines": [a, b], "sha256": hashlib.sha256(text.encode()).hexdigest(), "quote": quote, "why": why}


def aside(a, b, quote, why):
    text = norm(" ".join(POLICY[a - 1:b]))
    assert norm(quote) in text, (a, b, quote, text)
    return {"lines": [a, b], "quote": quote, "why": why}


# ----- clauses -----
LOWEST = keep(412, 413, "All airline tickets must be booked at the lowest available airfare as determined by Concur or "
              "the Travel Desk (subject to the parameters defined in this section).", "the default: the lowest available airfare")
CRITERIA = keep(426, 429, None, "a connection counts when it has at most one plane change of at most two hours")
NONREF = keep(432, 432, "Nonrefundable tickets must always be booked.", "a refundable fare is never booked")
NO_UPGRADEABLE = keep(433, 433, "Full Y fares, or upgradeable fares, are not allowed to be booked.",
                      "upgradeable fares are not allowed")
DOMESTIC = keep(397, 398, "Our policy is that domestic air purchases are coach class, regardless of flight time, and "
                "booked via nonrefundable tickets.", "domestic trips are coach, whatever the flight time")
MEDICAL = keep(398, 399, "Exception requests for medical reasons may be submitted and approved by both the travel "
               "department and the appropriate Vice President.", "a medical exception needs both approvals")
INTERNATIONAL = keep(402, 404, "International travel is to be by lowest possible airfare available. Any international "
                     "travel exceeding 8 hours (whether a single segment or multiple segments combined) can be booked in "
                     "an upgradeable fare or, with the prior approval of the traveler's Vice-President, in business class.",
                     "the international rule: lowest fare; business over 8 hours with the Vice-President's prior approval")
LEADERS = keep(286, 288, None, "at most three Executive Leadership Team members on one flight; only the CEO excepts")
PERSONAL = keep(296, 298, None, "personal air travel is not booked through the company")
SCOPE_BUSINESS = keep(128, 129, None, "the company reimburses travel connected with company business")
COMPANION = keep(267, 271, None, "a companion's travel, authorized in advance by a Senior Vice President or higher")
DOUBLE = keep(455, 455, "Double-bookings and back-to-back flights are prohibited.", "no second ticket for the same trip")
LOYALTY = keep(442, 444, None, "loyalty programmes may not add cost beyond the lowest available airfare")
ADVANCE = keep(408, 409, None, "the advance-planning rule is 'whenever possible', not a ban")
DRIVING = keep(382, 384, None, "driving under four hours must be considered, not chosen")
QUESTIONS = keep(139, 141, "Any questions, concerns or feedback regarding this travel polic y or the company's travel "
                 "management program should be addressed to the Travel Desk at travel@blackbaud.com.",
                 "policy questions go to the Travel Desk")

LOUNGE = aside(544, 547, "For travelers on international flights of eight hours or greater where a business meeting occurs "
               "on the day of arrival, it is permitted to use and expense airport arrival lounges.",
               "an inclusive 8-hour rule for arrival lounges, under Lodging: it does not decide the cabin")
WIFI = aside(472, 473, "Wi-Fi in flight (GOGO)-is reimbursable ONLY for flights over 1.5 hours.",
             "a flight-length rule for Wi-Fi fees, not for the cabin")
CAR = aside(664, 665, "For travel where the round trip travel distance exceeds 500 miles (800 km), personal car mileage "
            "may not be reimbursed", "a distance rule for personal-car mileage, not for flying")
SUMMARY_ADVANCE = aside(166, 167, "Air travel should be booked 14 days in advance whenever possible; at a minimum 7",
                        "the summary's softer restatement of the advance-planning rule")
REPORTS = aside(749, 749, "Expense reports should be submitted by the traveler within 14 calendar days of completion of a "
                "trip.", "a day count for expense reports, not for booking")
CHANGES = aside(447, 449, "standby fees or fees resulting from changing return flights en-route on the same day may be "
                "reimbursed", "the allowed way to move to a later flight: standby, not a second ticket")
MILES = aside(404, 405, "Employees may utilize their own frequent flier miles to upgrade fares, where applicable.",
              "the traveller may use miles on the ticket bought; it does not choose the fare")
OWN_UPGRADE = aside(398, 398, "Individuals may upgrade with frequent flyer miles or at their own expense.",
                    "a traveller's own upgrade does not change what the company buys")

# ----- builders -----


def trip(**fields):
    base = {
        "traveller_name": "", "traveller_title": "", "passenger": "EMPLOYEE", "accompanies": "", "home_country": "US",
        "on_leadership_team": False, "origin": "", "destination": "", "travel_date": "", "return_date": "",
        "booking_date": "", "purpose": "", "purpose_kind": "CUSTOMER_VISIT", "requested_cabin": "ECONOMY",
        "wants_upgradeable_fare": False, "loyalty_airline": "", "medical_need_on_file": False, "sign_offs": [],
        "colleagues_on_flights": [], "tickets_held": [], "upgradeable_fares": [], "driving_minutes": 0,
    }
    unknown = set(fields) - set(base)
    assert not unknown, unknown
    base.update(fields)
    return base


def sign(role, name, subject):
    return {"role": role, "name": name, "subject": subject}


def offer(slot, flight, cabin, cents, seats=True, refundable=False):
    data = {"slot": slot, "flight": flight, "cabin": cabin, "fare_cents": cents}
    if not seats:
        data["seats"] = False
    if refundable:
        data["refundable"] = True
    return data


def expected(decision, slots, cabins, reasons, approvers, clauses, phrase=""):
    return {"decision": decision, "offer_slots": slots, "cabins": cabins, "reason_codes": reasons,
            "approvers": approvers, "clauses": clauses, "unclear_phrase": phrase}


def search(origin, destination, date, flights, offers, return_date="", background=None):
    data = {"name": "main", "origin": origin, "destination": destination, "date": date, "return_date": return_date,
            "flights": flights, "offers": offers}
    # Background offers only on the scenario's own search (handbook.json background_offers is 0, so a search the
    # scenario does not pin lists nothing): 3 unless the scenario sets its own number.
    data["background"] = 3 if background is None else background
    return data


def first_flight(scenario_id, search_spec, slot):
    """The first flight number of a pinned offer, as search_flights lists it."""
    for name, made in pinned_offers(scenario_id, search_spec):
        if name == slot:
            return made.segments[0].flight_number
    raise KeyError(slot)


S = []


def scenario(id, category, overlays, request, trip_, search_spec, exp, must_keep, notes, twin_of="", twin_fact="",
             flag_twins=(), ambiguity="none", distractors=()):
    S.append({
        "id": id, "category": category, "overlays": list(overlays), "twin_of": twin_of, "twin_fact": twin_fact,
        "flag_twins": list(flag_twins), "ambiguity_note": ambiguity, "request": request, "trip": trip_,
        "world": {"searches": [search_spec]}, "expected": exp, "must_keep": list(must_keep),
        "distractors": list(distractors), "design_notes": notes,
    })


DOM_LOW = ["CLASS_OF_SERVICE", "DOMESTIC_CLASS", "LOWEST_AIRFARE"]
INT_LOW = ["CLASS_OF_SERVICE", "INTERNATIONAL_CLASS", "LOWEST_AIRFARE"]
INT_CLASS = ["CLASS_OF_SERVICE", "INTERNATIONAL_CLASS"]
# A booking that declines the business cabin asked for gives the reason the request is declined (task
# instructions): the 8-hour condition or the domestic coach rule, not LOWEST_FARE (template APPROVER_REVIEW,
# declined requests). nectar-pine's upgradeable fare is declined by line 433 of the Lowest Airfare Selection
# section, so it keeps LOWEST_FARE.
NOT_LONG = ["LONG_FLIGHT_CONDITION_NOT_MET", "UPGRADE_NOT_ELIGIBLE"]
LONG_OK = ["INTERNATIONAL_LONG_FLIGHT", "LONG_FLIGHT_APPROVED"]
UNCLEAR_ROLES = ["NOT_NAMED", "TRAVEL_DEPARTMENT"]
# A Vice-President's business sign-off on file, used by the decision or not: NONE or that role (template
# SYNC_NOTES 4(b) and 4').
NONE_OR_VP = ["NONE", "VICE_PRESIDENT"]

# ===== easy (5) =====

scenario(
    "amber-wren", "easy", [],
    "I'm heading from Austin up to Denver on the 15th for the analytics training. Just economy, whatever's cheapest.",
    trip(traveller_name="Maya Torres", traveller_title="Implementation Consultant", origin="AUS", destination="DEN",
         travel_date="2026-12-15", booking_date="2026-12-01", purpose="Analytics product training in Denver",
         purpose_kind="TRAINING"),
    search("AUS", "DEN", "2026-12-15", {
        "early": {"carrier": "WN", "depart": "07:05"},
        "mid": {"carrier": "UA", "depart": "09:40"},
        "noon": {"carrier": "WN", "depart": "13:15"},
        "late": {"carrier": "UA", "depart": "17:30"},
    }, [
        offer("early-economy", "early", "ECONOMY", 21400, seats=False),
        offer("mid-economy", "mid", "ECONOMY", 23800),
        offer("noon-economy", "noon", "ECONOMY", 24900),
        offer("late-economy", "late", "ECONOMY", 31500, refundable=True),
    ]),
    expected("BOOK", ["mid-economy"], ["ECONOMY"], ["LOWEST_FARE"], ["NONE"], DOM_LOW),
    [LOWEST, DOMESTIC],
    "Domestic economy: the lowest available airfare (lines 412-413). The cheaper 07:05 fare is sold out; the "
    "refundable fare is dearer anyway.")

scenario(
    "basil-cove", "easy", ["multi_leg"],
    "Can you book me Boston to Phoenix on January 12th for the customer kickoff? I don't mind a connection if it saves "
    "money.",
    trip(traveller_name="Owen Pruitt", traveller_title="Account Executive", origin="BOS", destination="PHX",
         travel_date="2027-01-12", booking_date="2026-12-14", purpose="Customer kickoff meeting in Phoenix"),
    search("BOS", "PHX", "2027-01-12", {
        "nonstop": {"carrier": "AA", "depart": "08:00"},
        "denver": {"carrier": "UA", "via": ["DEN"], "depart": "06:30", "layovers": [70]},
        "atlanta": {"carrier": "DL", "via": ["ATL"], "depart": "09:15", "layovers": [85]},
    }, [
        offer("nonstop-economy", "nonstop", "ECONOMY", 36800),
        offer("denver-economy", "denver", "ECONOMY", 29900),
        offer("atlanta-economy", "atlanta", "ECONOMY", 31200),
    ]),
    expected("BOOK", ["denver-economy"], ["ECONOMY"], ["LOWEST_FARE"], ["NONE"], DOM_LOW),
    [LOWEST, CRITERIA, DOMESTIC],
    "The cheapest fare is a one-stop connection with a 70-minute plane change, inside the criteria of lines 426-429, "
    "so it is the lowest available airfare.")

scenario(
    "cobalt-sedge", "easy", ["upgrade_not_taken", "outside_air_section"],
    "I fly Houston to London on the 20th of January. My VP already okayed business class, but honestly economy is "
    "fine for me this time. Please put me on United though, I'm a few flights short of keeping my status.",
    trip(traveller_name="Daniel Okafor", traveller_title="Director, EMEA Partnerships", origin="IAH", destination="LHR",
         travel_date="2027-01-20", booking_date="2026-12-16", purpose="Partner summit in London",
         purpose_kind="CONFERENCE", loyalty_airline="United Airlines",
         sign_offs=[sign("VICE_PRESIDENT", "Renee Castillo", "BUSINESS_CLASS")]),
    search("IAH", "LHR", "2027-01-20", {
        "united": {"carrier": "UA", "depart": "17:10"},
        "british": {"carrier": "BA", "depart": "19:45"},
    }, [
        offer("united-economy", "united", "ECONOMY", 84600),
        offer("united-business", "united", "BUSINESS", 512000),
        offer("british-economy", "british", "ECONOMY", 79800),
        offer("british-business", "british", "BUSINESS", 498000),
    ]),
    expected("BOOK", ["british-economy"], ["ECONOMY"], ["LOWEST_FARE", "LOYALTY_PROGRAM_PREFERENCE"], NONE_OR_VP,
             INT_LOW + ["FREQUENT_FLIER"]),
    [LOWEST, INTERNATIONAL, LOYALTY],
    "The traveller asks for economy, so the approved business seat is not taken. A loyalty programme may not add "
    "cost beyond the lowest available airfare (lines 442-444): the cheaper British Airways fare, not United.",
    distractors=[MILES])

scenario(
    "dune-larkspur", "easy", ["upgrade_not_taken"],
    "Seattle to Tokyo Haneda on February 3rd for the partner workshop. My VP signed off on business if I need it, but "
    "let's keep costs down: economy, cheapest you can find.",
    trip(traveller_name="Hannah Lindqvist", traveller_title="Solutions Architect", origin="SEA", destination="HND",
         travel_date="2027-02-03", booking_date="2027-01-05", purpose="Partner workshop in Tokyo",
         purpose_kind="TRAINING", sign_offs=[sign("VICE_PRESIDENT", "Gregory Hale", "BUSINESS_CLASS")]),
    search("SEA", "HND", "2027-02-03", {
        "delta": {"carrier": "DL", "depart": "11:20"},
        "japan": {"carrier": "JL", "depart": "13:05"},
        "ana": {"carrier": "NH", "depart": "16:40"},
    }, [
        offer("delta-economy", "delta", "ECONOMY", 91200),
        offer("delta-business", "delta", "BUSINESS", 586000),
        offer("japan-economy", "japan", "ECONOMY", 93400),
        offer("ana-economy", "ana", "ECONOMY", 88700),
        offer("ana-business", "ana", "BUSINESS", 601000),
    ]),
    expected("BOOK", ["ana-economy"], ["ECONOMY"], ["LOWEST_FARE"], NONE_OR_VP, INT_LOW),
    [LOWEST, INTERNATIONAL],
    "Over 8 hours with the Vice-President's approval, business is permitted (lines 402-404), not required: the "
    "traveller asks for the cheapest economy fare, so the lowest possible airfare.")

scenario(
    "ember-quarry", "easy", ["dearer_option"],
    "Booking New York JFK to Tokyo Narita on January 27th for the APAC customer summit. It's over thirteen hours in the air "
    "and my VP pre-approved business class, so please book business.",
    trip(traveller_name="Priya Natarajan", traveller_title="Senior Manager, Customer Success", origin="JFK",
         destination="NRT", travel_date="2027-01-27", booking_date="2026-12-22", purpose="APAC customer summit",
         purpose_kind="CONFERENCE", requested_cabin="BUSINESS",
         sign_offs=[sign("VICE_PRESIDENT", "Laura Whitman", "BUSINESS_CLASS")]),
    search("JFK", "NRT", "2027-01-27", {
        "japan": {"carrier": "JL", "depart": "11:00"},
        "ana": {"carrier": "NH", "depart": "13:30"},
        "american": {"carrier": "AA", "depart": "16:15"},
    }, [
        offer("japan-economy", "japan", "ECONOMY", 118000),
        offer("japan-business", "japan", "BUSINESS", 482000),
        offer("ana-economy", "ana", "ECONOMY", 112500),
        offer("ana-business", "ana", "BUSINESS", 455000),
        offer("american-economy", "american", "ECONOMY", 121000),
        offer("american-business", "american", "BUSINESS", 497000),
    ]),
    expected("BOOK", ["ana-business"], ["BUSINESS"], LONG_OK, NONE_OR_VP, INT_CLASS),
    [INTERNATIONAL],
    "Every itinerary is far over 480 minutes and the traveller's Vice-President approved business in advance "
    "(lines 402-404): the cheapest business fare. Background connections are longer still, so they agree.")

# ===== boundary twins (6) =====

def ams_flights(minutes):
    return {
        "delta": {"carrier": "DL", "depart": "17:50", "minutes": [minutes]},
        "klm": {"carrier": "KL", "depart": "19:25", "minutes": [minutes]},
    }
AMS_OFFERS = [
    offer("delta-economy", "delta", "ECONOMY", 78400),
    offer("delta-business", "delta", "BUSINESS", 389000),
    offer("klm-economy", "klm", "ECONOMY", 81200),
    offer("klm-business", "klm", "BUSINESS", 402000),
]
AMS_TRIP = {"origin": "DTW", "destination": "AMS", "travel_date": "2027-02-09", "booking_date": "2027-01-11",
            "purpose": "Quarterly review with the Amsterdam office", "purpose_kind": "INTERNAL_MEETING",
            "requested_cabin": "BUSINESS", "sign_offs": [sign("VICE_PRESIDENT", "Martin Ruiz", "BUSINESS_CLASS")]}

scenario(
    "fennel-ridge", "boundary_twin", ["dearer_option"],
    "Detroit to Amsterdam overnight on February 9th for the quarterly review. Martin, my VP, approved business class "
    "for this one, so business please.",
    trip(traveller_name="Claire Benoit", traveller_title="Director, Product Management", **AMS_TRIP),
    search("DTW", "AMS", "2027-02-09", ams_flights(481), AMS_OFFERS, background=0),
    expected("BOOK", ["delta-business"], ["BUSINESS"], LONG_OK, NONE_OR_VP, INT_CLASS),
    [INTERNATIONAL],
    "Both nonstops are scheduled at 481 minutes: international travel exceeding 8 hours, with the Vice-President's "
    "prior approval (lines 402-404). Background is off: a filler connection could fall on the other side.",
    twin_of="garnet-moor", twin_fact="both nonstops scheduled at 481 minutes or 480 minutes")

scenario(
    "garnet-moor", "boundary_twin", ["upgrade_not_taken"],
    "Detroit to Amsterdam overnight on February 9th for the quarterly review. Martin, my VP, approved business class. "
    "It's an eight-hour flight and I go straight from the airport into a meeting, so I'll use the arrival lounge too. "
    "Business please.",
    trip(traveller_name="Claire Benoit", traveller_title="Director, Product Management", **AMS_TRIP),
    search("DTW", "AMS", "2027-02-09", ams_flights(480), AMS_OFFERS, background=0),
    expected("BOOK", ["delta-economy"], ["ECONOMY"], NOT_LONG, NONE_OR_VP, INT_LOW),
    [INTERNATIONAL, LOWEST],
    "Both nonstops are scheduled at exactly 480 minutes: not 'exceeding 8 hours' (lines 402-404), so business is "
    "not available whoever approved it; the lowest possible airfare. The arrival-lounge rule (lines 544-547) is "
    "'eight hours or greater' and does allow the lounge, but it is a lodging rule and does not change the cabin.",
    twin_of="fennel-ridge", twin_fact="both nonstops scheduled at 480 minutes or 481 minutes", distractors=[LOUNGE])

BOG_TRIP = {"origin": "BOS", "destination": "BOG", "travel_date": "2027-03-02", "booking_date": "2027-02-01",
            "purpose": "Customer implementation workshop in Bogota", "purpose_kind": "CUSTOMER_VISIT",
            "requested_cabin": "BUSINESS", "sign_offs": [sign("VICE_PRESIDENT", "Alan Prescott", "BUSINESS_CLASS")]}
BOG_REQUEST = ("I need to get from Boston to Bogota on March 2nd for the implementation workshop. Alan, my VP, signed "
               "off on business class in advance. Please book business.")

scenario(
    "heron-bluff", "boundary_twin", ["multi_leg", "dearer_option"],
    BOG_REQUEST,
    trip(traveller_name="Lucia Ferrante", traveller_title="Principal Consultant", **BOG_TRIP),
    search("BOS", "BOG", "2027-03-02", {
        "morning": {"carrier": "UA", "via": ["IAH"], "depart": "06:00", "minutes": [215, 285], "layovers": [70]},
        "midday": {"carrier": "UA", "via": ["IAH"], "depart": "11:30", "minutes": [215, 285], "layovers": [70]},
    }, [
        offer("morning-economy", "morning", "ECONOMY", 61800),
        offer("morning-business", "morning", "BUSINESS", 214000),
        offer("midday-economy", "midday", "ECONOMY", 64300),
        offer("midday-business", "midday", "BUSINESS", 228000),
    ], background=0),
    expected("BOOK", ["morning-business"], ["BUSINESS"], LONG_OK, NONE_OR_VP, INT_CLASS),
    [INTERNATIONAL],
    "Only connections through Houston: 215 + 285 = 500 flying minutes. 'Multiple segments combined' (lines 402-404) "
    "exceed 480 even without the 70-minute connection, so every reading agrees: business with the Vice-President's "
    "prior approval.",
    twin_of="iris-tundra", twin_fact="connections through Houston (500 flying minutes) or Miami (380 flying, 480 "
    "elapsed)")

scenario(
    "iris-tundra", "boundary_twin", ["multi_leg"],
    BOG_REQUEST,
    trip(traveller_name="Lucia Ferrante", traveller_title="Principal Consultant", **BOG_TRIP),
    search("BOS", "BOG", "2027-03-02", {
        "morning": {"carrier": "AA", "via": ["MIA"], "depart": "06:15", "minutes": [175, 205], "layovers": [100]},
        "midday": {"carrier": "AA", "via": ["MIA"], "depart": "12:05", "minutes": [175, 205], "layovers": [100]},
    }, [
        offer("morning-economy", "morning", "ECONOMY", 58900),
        offer("morning-business", "morning", "BUSINESS", 205000),
        offer("midday-economy", "midday", "ECONOMY", 60400),
        offer("midday-business", "midday", "BUSINESS", 219000),
    ], background=0),
    expected("BOOK", ["morning-economy"], ["ECONOMY"], NOT_LONG, NONE_OR_VP, INT_LOW),
    [INTERNATIONAL, LOWEST],
    "Only connections through Miami: 175 + 205 = 380 flying minutes and 480 minutes from first departure to last "
    "arrival with the 100-minute connection. Even counting the ground time the travel does not exceed 480, so "
    "business is not available; the lowest possible airfare.",
    twin_of="heron-bluff", twin_fact="connections through Miami (380 flying, 480 elapsed) or Houston (500 flying "
    "minutes)")

AUS_BOS = {
    "jetblue": {"carrier": "B6", "depart": "07:00"},
    "delta": {"carrier": "DL", "depart": "09:15"},
    "southwest": {"carrier": "WN", "depart": "11:40"},
}
AUS_BOS_OFFERS = [
    offer("jetblue-economy", "jetblue", "ECONOMY", 28900),
    offer("delta-economy", "delta", "ECONOMY", 31200),
    offer("southwest-economy", "southwest", "ECONOMY", 33500),
]
OFFSITE = {"origin": "AUS", "destination": "BOS", "travel_date": "2027-01-19", "booking_date": "2026-12-15",
           "purpose": "Leadership offsite at the Cambridge office", "purpose_kind": "INTERNAL_MEETING",
           "on_leadership_team": True}
OFFSITE_REQUEST = ("I'm going Austin to Boston on January 19th for the leadership offsite in Cambridge. Book me the "
                   "cheapest economy flight. Most of the team is already ticketed on the early JetBlue.")


def offsite_colleagues(scenario_id, third_on_team):
    spec = search("AUS", "BOS", "2027-01-19", AUS_BOS, AUS_BOS_OFFERS)
    number = first_flight(scenario_id, spec, "jetblue-economy")
    return [
        {"name": "Sandra Kim", "title": "Chief Financial Officer", "on_leadership_team": True, "flight_number": number,
         "date": "2027-01-19"},
        {"name": "Victor Hale", "title": "Chief Technology Officer", "on_leadership_team": True,
         "flight_number": number, "date": "2027-01-19"},
        {"name": "Nora Patel", "title": "Chief People Officer" if third_on_team else "Director, Executive Programs",
         "on_leadership_team": third_on_team, "flight_number": number, "date": "2027-01-19"},
    ]


scenario(
    "jasper-glen", "boundary_twin", ["multi_traveller", "outside_air_section"],
    OFFSITE_REQUEST,
    trip(traveller_name="Thomas Reyes", traveller_title="Chief Revenue Officer",
         colleagues_on_flights=offsite_colleagues("jasper-glen", False), **OFFSITE),
    search("AUS", "BOS", "2027-01-19", AUS_BOS, AUS_BOS_OFFERS),
    expected("BOOK", ["jetblue-economy"], ["ECONOMY"], ["LOWEST_FARE"], ["NONE"], DOM_LOW + ["TRAVELING_TOGETHER"]),
    [LEADERS, LOWEST, DOMESTIC],
    "Two leadership-team members and a director are on the 07:00 JetBlue; with the traveller that is three members "
    "of the Executive Leadership Team, which does not exceed three (lines 286-288): the cheapest fare.",
    twin_of="kelp-meadow", twin_fact="the third colleague on the 07:00 flight is a director, or a leadership-team member")

scenario(
    "kelp-meadow", "boundary_twin", ["multi_traveller", "outside_air_section", "dearer_option"],
    OFFSITE_REQUEST,
    trip(traveller_name="Thomas Reyes", traveller_title="Chief Revenue Officer",
         colleagues_on_flights=offsite_colleagues("kelp-meadow", True), **OFFSITE),
    search("AUS", "BOS", "2027-01-19", AUS_BOS, AUS_BOS_OFFERS),
    expected("BOOK", ["delta-economy"], ["ECONOMY"], ["LOWEST_FARE", "TRAVELLER_LIMIT_PER_FLIGHT"], ["NONE"],
             DOM_LOW + ["TRAVELING_TOGETHER"]),
    [LEADERS, LOWEST, DOMESTIC],
    "Three leadership-team members are already on the 07:00 JetBlue; the traveller would be a fourth, which exceeds "
    "three (lines 286-288), and only the CEO may except it. The cheapest fare on another flight: Delta at 09:15.",
    twin_of="jasper-glen", twin_fact="the third colleague on the 07:00 flight is a leadership-team member, or a director")

# ===== multi-rule (4) =====

scenario(
    "lilac-ferry", "multi_rule", ["dearer_option"],
    "Boston to Seattle on February 16th for the customer go-live. Because of my back surgery I've got a medical "
    "exception for business class; both the travel desk and my VP approved it. Please book business.",
    trip(traveller_name="Robert Asante", traveller_title="Senior Project Manager", origin="BOS", destination="SEA",
         travel_date="2027-02-16", booking_date="2027-01-20", purpose="Customer go-live support in Seattle",
         requested_cabin="BUSINESS", medical_need_on_file=True,
         sign_offs=[sign("TRAVEL_DEPARTMENT", "Blackbaud Travel Desk", "MEDICAL_EXCEPTION"),
                    sign("VICE_PRESIDENT", "Janet Morrow", "MEDICAL_EXCEPTION")]),
    search("BOS", "SEA", "2027-02-16", {
        "morning": {"carrier": "DL", "depart": "08:30"},
        "alaska": {"carrier": "AS", "depart": "10:10"},
        "afternoon": {"carrier": "DL", "depart": "15:45"},
    }, [
        offer("morning-economy", "morning", "ECONOMY", 34100),
        offer("morning-business", "morning", "BUSINESS", 118000),
        offer("alaska-economy", "alaska", "ECONOMY", 32800),
        offer("afternoon-economy", "afternoon", "ECONOMY", 35900),
        offer("afternoon-business", "afternoon", "BUSINESS", 112500),
    ]),
    expected("BOOK", ["afternoon-business"], ["BUSINESS"], ["MEDICAL_NEED"], ["NONE", "TRAVEL_DEPARTMENT", "VICE_PRESIDENT"],
             ["CLASS_OF_SERVICE", "DOMESTIC_CLASS"]),
    [DOMESTIC, MEDICAL],
    "Domestic air is coach regardless of flight time (line 397), but a medical exception approved by both the travel "
    "department and the appropriate Vice President (lines 398-399) is on file: the cheapest nonrefundable business "
    "fare.")

scenario(
    "moss-harbor", "multi_rule", ["date_arithmetic", "dearer_option"],
    "Atlanta to Paris for the EMEA leadership week: out Monday March 8th, back the following Monday. My VP approved "
    "business class in advance. Please book a business round trip.",
    trip(traveller_name="Gabriel Moreau", traveller_title="Director, International Sales", origin="ATL",
         destination="CDG", travel_date="2027-03-08", return_date="2027-03-15", booking_date="2027-02-08",
         purpose="EMEA leadership week in Paris", purpose_kind="INTERNAL_MEETING", requested_cabin="BUSINESS",
         sign_offs=[sign("VICE_PRESIDENT", "Helen Carver", "BUSINESS_CLASS")]),
    search("ATL", "CDG", "2027-03-08", {
        "delta": {"carrier": "DL", "depart": "17:30", "minutes": [535],
                  "return": {"depart": "10:15", "minutes": [600]}},
        "airfrance": {"carrier": "AF", "depart": "21:40", "minutes": [530],
                      "return": {"depart": "13:20", "minutes": [610]}},
    }, [
        offer("delta-economy", "delta", "ECONOMY", 138000),
        offer("delta-business", "delta", "BUSINESS", 612000),
        offer("airfrance-economy", "airfrance", "ECONOMY", 132500),
        offer("airfrance-business", "airfrance", "BUSINESS", 589000, refundable=True),
    ], return_date="2027-03-15", background=0),
    expected("BOOK", ["delta-business"], ["BUSINESS"], LONG_OK + ["REFUNDABLE_FARE_NOT_ALLOWED"], NONE_OR_VP,
             INT_CLASS + ["LOWEST_AIRFARE"]),
    [INTERNATIONAL, NONREF],
    "Both directions exceed 480 minutes and the Vice-President approved business in advance (lines 402-404). The "
    "cheaper Air France business fare is refundable, and nonrefundable tickets must always be booked (line 432): the "
    "Delta business round trip. The return is the following Monday, March 15.")

nectar_spec = search("BOS", "LHR", "2027-02-22", {
    "british": {"carrier": "BA", "depart": "18:30"},
    "delta": {"carrier": "DL", "depart": "21:10"},
}, [
    offer("british-economy", "british", "ECONOMY", 61500),
    offer("british-flex", "british", "ECONOMY", 79500),
    offer("delta-economy", "delta", "ECONOMY", 64000),
], background=0)
scenario(
    "nectar-pine", "multi_rule", ["synonym"],
    "Boston to London Heathrow on February 22nd. Economy is fine, but please get me the British Airways economy fare "
    "that I can upgrade later with my miles.",
    trip(traveller_name="Fiona Gallagher", traveller_title="Senior Consultant", origin="BOS", destination="LHR",
         travel_date="2027-02-22", booking_date="2027-01-25", purpose="Customer data migration workshop in London",
         wants_upgradeable_fare=True,
         upgradeable_fares=[{"flight_number": first_flight("nectar-pine", nectar_spec, "british-flex"),
                             "fare_cents": 79500}]),
    nectar_spec,
    # Validation w1v3: the fare is wanted for a miles upgrade, so the frequent flier rule (lines 442-444) is also
    # a ground for declining it.
    expected("BOOK", ["british-economy"], ["ECONOMY"], [*NOT_LONG, "LOWEST_FARE", "LOYALTY_PROGRAM_PREFERENCE"],
             ["NONE"], INT_LOW + ["FREQUENT_FLIER"]),
    [NO_UPGRADEABLE, INTERNATIONAL, LOWEST],
    "Upgradeable fares are not allowed to be booked (line 433). The only exception, international travel exceeding "
    "8 hours (lines 402-404), does not reach a 405-minute nonstop. The lowest fare; the traveller may still use miles "
    "on it where the airline allows (lines 404-405).",
    distractors=[MILES])

scenario(
    "onyx-brook", "multi_rule", ["dearer_option"],
    "Chicago O'Hare to Los Angeles on January 14th for the nonprofit customer conference. Just grab the cheapest seat "
    "you can.",
    trip(traveller_name="Kevin Duarte", traveller_title="Customer Marketing Manager", origin="ORD", destination="LAX",
         travel_date="2027-01-14", booking_date="2026-12-17", purpose="Nonprofit customer conference in Los Angeles",
         purpose_kind="CONFERENCE"),
    search("ORD", "LAX", "2027-01-14", {
        "early": {"carrier": "UA", "depart": "07:15"},
        "american": {"carrier": "AA", "depart": "09:50"},
        "midday": {"carrier": "UA", "depart": "13:30"},
    }, [
        offer("early-economy", "early", "ECONOMY", 25900, refundable=True),
        offer("american-economy", "american", "ECONOMY", 28400),
        offer("midday-economy", "midday", "ECONOMY", 30100),
    ]),
    expected("BOOK", ["american-economy"], ["ECONOMY"], ["LOWEST_FARE", "REFUNDABLE_FARE_NOT_ALLOWED"], ["NONE"],
             DOM_LOW),
    [NONREF, DOMESTIC, LOWEST],
    "The cheapest seat is a refundable fare, but domestic trips are booked via nonrefundable tickets (line 397) and "
    "nonrefundable tickets must always be booked (line 432): the cheapest nonrefundable fare.")

# ===== hidden clause (2) =====

scenario(
    "pearl-thistle", "hidden_clause", ["multi_leg"],
    "Boston to Honolulu on February 10th for the customer conference. It's well over eleven hours, and my VP approved "
    "business class, so please book business.",
    trip(traveller_name="Simone Achebe", traveller_title="Director, Customer Advocacy", origin="BOS", destination="HNL",
         travel_date="2027-02-10", booking_date="2027-01-12", purpose="Customer conference in Honolulu",
         purpose_kind="CONFERENCE", requested_cabin="BUSINESS",
         sign_offs=[sign("VICE_PRESIDENT", "Paul Brennan", "BUSINESS_CLASS")]),
    search("BOS", "HNL", "2027-02-10", {
        "nonstop": {"carrier": "DL", "depart": "08:45", "minutes": [690]},
        "sanfrancisco": {"carrier": "UA", "via": ["SFO"], "depart": "07:00", "minutes": [395, 330], "layovers": [80]},
    }, [
        offer("nonstop-economy", "nonstop", "ECONOMY", 62800),
        offer("nonstop-business", "nonstop", "BUSINESS", 248000),
        offer("sanfrancisco-economy", "sanfrancisco", "ECONOMY", 59900),
        offer("sanfrancisco-business", "sanfrancisco", "BUSINESS", 231000),
    ]),
    expected("BOOK", ["sanfrancisco-economy"], ["ECONOMY"], NOT_LONG, NONE_OR_VP, DOM_LOW),
    [DOMESTIC, LOWEST, CRITERIA],
    "Honolulu is in the United States, so this is domestic: coach class, regardless of flight time (line 397). The "
    "Vice-President's approval belongs to the international rule (lines 402-404), which does not apply. The cheapest "
    "fare is a connection with an 80-minute plane change, inside lines 426-429.")

scenario(
    "quill-aspen", "hidden_clause", ["outside_air_section", "companion"],
    "Hi, I'm Elena Bell. I'm joining my husband Marcus at the customer conference in Orlando on March 3rd to help host "
    "the customers' spouses program. Our SVP approved my travel ahead of time. Economy is fine, cheapest flight from "
    "Boston please.",
    trip(traveller_name="Elena Bell", traveller_title="Spouse of Marcus Bell, Vice President of Sales",
         passenger="SPOUSE_OR_COMPANION", accompanies="Marcus Bell", origin="BOS", destination="MCO",
         travel_date="2027-03-03", booking_date="2027-02-03",
         purpose="Co-hosting the customers' spouses program at the customer conference",
         purpose_kind="CLIENT_ENTERTAINING",
         sign_offs=[sign("SENIOR_VICE_PRESIDENT", "Diane Foster", "COMPANION_TRAVEL")]),
    search("BOS", "MCO", "2027-03-03", {
        "morning": {"carrier": "B6", "depart": "08:10"},
        "delta": {"carrier": "DL", "depart": "11:25"},
        "evening": {"carrier": "B6", "depart": "16:50"},
    }, [
        offer("morning-economy", "morning", "ECONOMY", 21900),
        offer("delta-economy", "delta", "ECONOMY", 23400),
        offer("evening-economy", "evening", "ECONOMY", 24600),
    ]),
    expected("BOOK", ["morning-economy"], ["ECONOMY"], ["COMPANION_TRAVEL_AUTHORIZED", "LOWEST_FARE"],
             ["NONE", "SENIOR_VICE_PRESIDENT"], ["LOWEST_AIRFARE", "SPOUSE_COMPANION"]),
    [COMPANION, LOWEST],
    "A companion's travel is reimbursed when authorized in advance by a Senior Vice President or higher, to help "
    "entertain clients' spouses (lines 267-271, in General Travel Guidelines, not Air Travel): book her at the lowest "
    "fare. The approval relied on is the Senior Vice President's.")

# ===== distractor (2) =====

scenario(
    "raven-dell", "distractor", ["date_arithmetic", "month_end"],
    "Sorry for the short notice, I know it's less than a week out: I need Boston to Atlanta on January 2nd for the "
    "customer's year-start planning session. Economy, cheapest available.",
    trip(traveller_name="Jordan Whitaker", traveller_title="Customer Success Manager", origin="BOS", destination="ATL",
         travel_date="2027-01-02", booking_date="2026-12-28", purpose="Customer year-start planning session"),
    search("BOS", "ATL", "2027-01-02", {
        "morning": {"carrier": "DL", "depart": "07:40"},
        "jetblue": {"carrier": "B6", "depart": "10:30"},
        "afternoon": {"carrier": "DL", "depart": "12:15"},
    }, [
        offer("morning-economy", "morning", "ECONOMY", 32400),
        offer("jetblue-economy", "jetblue", "ECONOMY", 29800),
        offer("afternoon-economy", "afternoon", "ECONOMY", 35100),
    ]),
    expected("BOOK", ["jetblue-economy"], ["ECONOMY"], ["LOWEST_FARE"], ["NONE"], DOM_LOW + ["ADVANCE_PURCHASE"]),
    [ADVANCE, LOWEST, DOMESTIC],
    "Booked on December 28 for January 2: 5 days ahead, across a month and year end. The 7-day minimum applies "
    "'whenever possible' (lines 408-409) and is no ban, so the trip is booked at the lowest available airfare.",
    distractors=[SUMMARY_ADVANCE, REPORTS])

scenario(
    "saffron-knoll", "distractor", [],
    "Charlotte to Atlanta on February 4th for the customer workshop. I did think about driving, it's about three "
    "hours forty-five each way and roughly 490 miles there and back, but I'd lose most of the day, so I'd rather fly. "
    "Cheapest economy please.",
    trip(traveller_name="Marcus Lee", traveller_title="Implementation Consultant", origin="CLT", destination="ATL",
         travel_date="2027-02-04", booking_date="2027-01-14", purpose="Customer workshop in Atlanta",
         driving_minutes=225),
    search("CLT", "ATL", "2027-02-04", {
        "early": {"carrier": "AA", "depart": "07:20"},
        "delta": {"carrier": "DL", "depart": "08:05"},
        "evening": {"carrier": "AA", "depart": "17:45"},
    }, [
        offer("early-economy", "early", "ECONOMY", 18900),
        offer("delta-economy", "delta", "ECONOMY", 17600),
        offer("evening-economy", "evening", "ECONOMY", 21300),
    ]),
    expected("BOOK", ["delta-economy"], ["ECONOMY"], ["LOWEST_FARE"], ["NONE"], DOM_LOW + ["AIR_TRAVEL_GENERAL"]),
    [DRIVING, LOWEST, DOMESTIC],
    "The drive is under four hours, so driving 'must be considered' (lines 383-384); the traveller has considered it "
    "and flies, which the clause allows. The 500-mile personal-car rule (lines 664-665) is about mileage, not flying. "
    "The lowest available airfare.",
    distractors=[CAR, WIFI])

# ===== refusal (2) =====

scenario(
    "tansy-reef", "refusal", ["personal_travel", "outside_air_section"],
    "Can you book me Boston to Orlando on December 23rd? It's our family holiday trip to the parks. Just put it on the "
    "corporate card and I'll sort it out with expenses later.",
    trip(traveller_name="Allison Grant", traveller_title="Senior Software Engineer", origin="BOS", destination="MCO",
         travel_date="2026-12-23", booking_date="2026-12-02", purpose="Family holiday", purpose_kind="PERSONAL"),
    search("BOS", "MCO", "2026-12-23", {
        "jetblue": {"carrier": "B6", "depart": "09:05"},
        "delta": {"carrier": "DL", "depart": "13:40"},
    }, [
        offer("jetblue-economy", "jetblue", "ECONOMY", 27400),
        offer("delta-economy", "delta", "ECONOMY", 29900),
    ]),
    expected("REFUSE", [], ["NONE"], ["OUTSIDE_POLICY_SCOPE", "PERSONAL_TRAVEL_NOT_COVERED"], ["NONE"],
             ["PERSONAL_VACATION", "RESPONSIBILITY"]),
    [PERSONAL, SCOPE_BUSINESS],
    "Employees are not permitted to book personal air travel using Concur and must use their own payment methods, not "
    "the corporate card (lines 296-298); the company pays only for travel connected with company business (lines "
    "128-129). No ticket is bought.")

umber_spec = search("AUS", "ORD", "2027-01-21", {
    "morning": {"carrier": "UA", "depart": "10:15"},
    "evening": {"carrier": "AA", "depart": "18:40"},
}, [
    offer("morning-economy", "morning", "ECONOMY", 26400),
    offer("evening-economy", "evening", "ECONOMY", 27900),
])
scenario(
    "umber-crest", "refusal", [],
    "I'm already ticketed on the 10:15 United from Austin to Chicago on January 21st, but my morning meeting here might "
    "run over. Please also book me on the 6:40pm American as a backup; I'll just skip whichever one I don't make.",
    trip(traveller_name="Brian Castellano", traveller_title="Regional Sales Manager", origin="AUS", destination="ORD",
         travel_date="2027-01-21", booking_date="2026-12-29", purpose="Customer visit in Chicago",
         tickets_held=[{"flight_number": first_flight("umber-crest", umber_spec, "morning-economy"),
                        "date": "2027-01-21", "origin": "AUS", "destination": "ORD"}]),
    umber_spec,
    expected("REFUSE", [], ["NONE"], ["DOUBLE_BOOKING_PROHIBITED", "NO_COMPLIANT_OFFER"], ["NONE"], ["DOUBLE_BOOKINGS"]),
    [DOUBLE],
    "The traveller already holds a ticket for this trip; a second, back-up ticket is a double-booking, and "
    "double-bookings and back-to-back flights are prohibited (line 455), with no exception. Same-day changes and "
    "standby (lines 447-449) are the way to move later. No ticket is bought.",
    distractors=[CHANGES])

# ===== flag (3) =====

scenario(
    "vellum-ash", "flag", ["multi_leg", "unclear_phrase"],
    BOG_REQUEST,
    trip(traveller_name="Lucia Ferrante", traveller_title="Principal Consultant", **BOG_TRIP),
    search("BOS", "BOG", "2027-03-02", {
        "morning": {"carrier": "AA", "via": ["MIA"], "depart": "06:15", "minutes": [175, 205], "layovers": [115]},
        "midday": {"carrier": "AA", "via": ["MIA"], "depart": "12:05", "minutes": [175, 205], "layovers": [115]},
    }, [
        offer("morning-economy", "morning", "ECONOMY", 58900),
        offer("morning-business", "morning", "BUSINESS", 205000),
        offer("midday-economy", "midday", "ECONOMY", 60400),
        offer("midday-business", "midday", "BUSINESS", 219000),
    ], background=0),
    expected("FLAG_FOR_APPROVAL", ["morning-business"], ["BUSINESS"], ["UNCLEAR_POLICY_TEXT"], UNCLEAR_ROLES + ["VICE_PRESIDENT"],
             INT_CLASS, phrase="exceeding 8 hours (whether a single segment or multiple segments combined)"),
    [INTERNATIONAL, QUESTIONS],
    "Connections through Miami: 175 + 205 = 380 flying minutes, 495 minutes from first departure to last arrival "
    "with the 115-minute connection. 'Multiple segments combined' (lines 402-404) does not say whether the ground "
    "time between them counts: without it the travel is within 480 (economy), with it over (business, which the "
    "Vice-President approved). Hold the business fare; nobody is named to settle the words, and policy questions go "
    "to the Travel Desk (lines 139-141).",
    flag_twins=["heron-bluff", "iris-tundra"],
    ambiguity={"phrase": "exceeding 8 hours (whether a single segment or multiple segments combined)",
               "readings": [("the segments' flying minutes are added and ground time between them is left out: 380, "
                             "within the limit, so economy"),
                            ("the combined travel runs from the first departure to the last arrival, ground time "
                             "included: 495, over the limit, so business with the Vice-President's approval")]})

willow_spec = search("ORD", "HND", "2027-03-10", {
    "ana": {"carrier": "NH", "depart": "11:45"},
    "united": {"carrier": "UA", "depart": "12:30"},
}, [
    offer("ana-economy", "ana", "ECONOMY", 104000),
    offer("ana-flex", "ana", "ECONOMY", 139500),
    offer("ana-business", "ana", "BUSINESS", 562000),
    offer("united-economy", "united", "ECONOMY", 99800),
    offer("united-business", "united", "BUSINESS", 548000),
], background=0)
scenario(
    "willow-fen", "flag", ["unclear_phrase"],
    "Chicago to Tokyo Haneda on March 10th for the APAC partner meetings. I'm not asking for business. Just book the "
    "ANA economy fare that can be upgraded, so I can move up with my own miles.",
    trip(traveller_name="Ethan Mercer", traveller_title="Partner Alliances Manager", origin="ORD", destination="HND",
         travel_date="2027-03-10", booking_date="2027-02-08", purpose="APAC partner meetings in Tokyo",
         purpose_kind="CUSTOMER_VISIT", wants_upgradeable_fare=True,
         upgradeable_fares=[{"flight_number": first_flight("willow-fen", willow_spec, "ana-flex"),
                             "fare_cents": 139500}]),
    willow_spec,
    expected("FLAG_FOR_APPROVAL", ["ana-flex"], ["ECONOMY"], ["UNCLEAR_POLICY_TEXT"], UNCLEAR_ROLES,
             INT_LOW, phrase="can be booked in an upgradeable fare"),
    [INTERNATIONAL, NO_UPGRADEABLE, QUESTIONS],
    "A 755-minute nonstop: international travel exceeding 8 hours 'can be booked in an upgradeable fare' (lines "
    "402-404), but 'Full Y fares, or upgradeable fares, are not allowed to be booked' (line 433), and the handbook "
    "states no order between the two. The contradiction is genuine: hold the upgradeable fare; nobody is named to "
    "settle it, and policy questions go to the Travel Desk (lines 139-141).",
    flag_twins=["nectar-pine", "ember-quarry"],
    ambiguity={"phrase": "can be booked in an upgradeable fare",
               "readings": [("the international sentence is a specific permission for travel over 8 hours that "
                             "overrides the general ban: book the upgradeable fare"),
                            ("line 433 bans upgradeable fares in every case, so only business with the "
                             "Vice-President's approval or the lowest fare remains: book the lowest fare")]})

scenario(
    "yew-hollow", "flag", ["approval_required", "dearer_option"],
    "San Francisco to Seoul on February 17th for the customer data summit. My director, Wes, approved business class "
    "for the long flight. Please book business.",
    trip(traveller_name="Grace Holloway", traveller_title="Senior Data Scientist", origin="SFO", destination="ICN",
         travel_date="2027-02-17", booking_date="2027-01-18", purpose="Customer data summit in Seoul",
         purpose_kind="CONFERENCE", requested_cabin="BUSINESS",
         sign_offs=[sign("DIRECTOR", "Wes Albright", "BUSINESS_CLASS")]),
    search("SFO", "ICN", "2027-02-17", {
        "united": {"carrier": "UA", "depart": "11:10"},
        "korean": {"carrier": "KE", "depart": "13:40"},
    }, [
        offer("united-economy", "united", "ECONOMY", 96500),
        offer("united-business", "united", "BUSINESS", 498000),
        offer("korean-economy", "korean", "ECONOMY", 92300),
        offer("korean-business", "korean", "BUSINESS", 471000),
    ], background=0),
    # Validation w1v3: LONG_FLIGHT_CONDITION_NOT_MET names the same missing prior approval (lines 402-404).
    expected("FLAG_FOR_APPROVAL", ["korean-business"], ["BUSINESS"], ["APPROVAL_REQUIRED", "LONG_FLIGHT_CONDITION_NOT_MET"],
             ["VICE_PRESIDENT"], INT_CLASS),
    [INTERNATIONAL],
    "The nonstops are about 680 minutes, international travel exceeding 8 hours, so business is possible with the "
    "prior approval of the traveller's Vice-President (lines 402-404). Only a director signed: hold the cheapest "
    "business fare for the Vice-President. Approval required, not 'no compliant offer'.",
    flag_twins=["ember-quarry", "garnet-moor"],
    ambiguity="none: an approval is required and missing; the text is clear")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.json"):
        old.unlink()
    for data in S:
        (OUT / f"{data['id']}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {len(S)} scenarios to {OUT}")


if __name__ == "__main__":
    main()
