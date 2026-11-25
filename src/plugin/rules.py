"""The answer key's rules for the Blackbaud, Inc. Travel Policy (February 2014), as exact integer code.
Byte-identical in src/plugin/rules.py and verifier/rules.py; it imports only modules a verifier may use.

Every rule cites the frozen handbook text (src/plugin/data/policy.txt) by line. Where the text leaves an
answer open, the rule returns FLAG_FOR_APPROVAL with the unclear words, and a scenario may depend on each
unclear phrase at most once (tests/test_scenarios.py). Combinations no scenario needs raise ValueError, so a
new scenario cannot fall silently into untested logic.

The duration hook. Lines 402-404: "Any international travel exceeding 8 hours (whether a single segment or
multiple segments combined) can be booked in an upgradeable fare or, with the prior approval of the
traveler's Vice-President, in business class." The handbook measures the travel of one direction, adding the
segments' scheduled minutes together, and is strictly over the limit above 480 minutes ("exceeding"). It does
not say whether the ground time between segments counts: when the flying minutes alone exceed 480 every
reading agrees (over); when the whole elapsed journey, ground time included, is within 480 every reading
agrees (not over); otherwise the reading is unclear (None). A nonstop's flying and elapsed minutes are equal,
so a nonstop is never unclear.

The handbook's second duration threshold, the arrival-lounge rule of lines 544-547 ("international flights
of eight hours or greater", inclusive), is a lodging rule: no answer field depends on it, and it is coded only
so a scenario can show that it does not change the cabin. It is measured per flight; for a connection whose
every flight is under 480 minutes but whose journey is not, the reading is unclear (None).
"""

from contract import Approver, Cabin, Clause, Decision, Passenger, Purpose, ReasonCode, SignOffSubject

from .world import days_between

HANDBOOK = "Blackbaud, Inc. Travel Policy, February 2014"

# Each closed-list section and the heading it names in the frozen text (tests check every heading is there).
CLAUSE_HEADINGS = {
    Clause.SCOPE: "SCOPE",
    Clause.RESPONSIBILITY: "RESPONSIBILITY AND ENFORCEMENT",
    Clause.EXECUTIVE_SUMMARY: "EXECUTIVE SUMMARY",
    Clause.RESERVATIONS: "RESERVATION PROCEDURES",
    Clause.TRAVEL_DESK: "TRAVEL DESK",
    Clause.SPOUSE_COMPANION: "SPOUSE/COMPANION TRAVEL",
    Clause.TRAVELING_TOGETHER: "EMPLOYEES TRAVELING TOGETHER",
    Clause.PERSONAL_VACATION: "PERSONAL/VACATION TRAVEL",
    Clause.RESTRICTED_COUNTRIES: "RESTRICTED/PROHIBITED COUNTRIES OR REGIONS",
    Clause.AIR_TRAVEL_GENERAL: "4. AIR TRAVEL",
    Clause.CLASS_OF_SERVICE: "CLASS OF SERVICE",
    Clause.DOMESTIC_CLASS: "DOMESTIC",
    Clause.INTERNATIONAL_CLASS: "INTERNATIONAL",
    Clause.ADVANCE_PURCHASE: "ADVANCE PURCHASE",
    Clause.LOWEST_AIRFARE: "LOWEST AIRFARE SELECTION",
    Clause.PREFERRED_AIRLINES: "PREFERED AIRLINES",
    Clause.FREQUENT_FLIER: "FREQUENT FLIER PROGRAMS",
    Clause.CHANGES: "CHANGES",
    Clause.DOUBLE_BOOKINGS: "DOUBLE-BOOKINGS",
    Clause.CANCELLATIONS: "CANCELLATIONS",
    Clause.MISCELLANEOUS_FEES: "MISCELLANEOUS FEES",
    Clause.ARRIVAL_LOUNGE: "INTERNATIONAL OVERNIGHT/MORNING ARRIVAL",
    Clause.PERSONAL_CAR: "PERSONAL CAR USAGE",
    Clause.NON_REIMBURSABLE: "NON-REIMBURSABLE EXPENSES",
    Clause.BILLABLE_TRAVEL: "APPENDIX C",
}

# The handbook's duration thresholds (the per-handbook duration hook; tests/test_duration.py tests both
# sides of each). ">" is strict ("exceeding"), ">=" inclusive ("or greater").
DURATION_RULES = (
    {"name": "international-long", "minutes": 480, "operator": ">", "lines": [402, 404],
     "quote": "Any international travel exceeding 8 hours (whether a single segment or multiple segments combined)"},
    {"name": "arrival-lounge", "minutes": 480, "operator": ">=", "lines": [544, 545],
     "quote": "For travelers on international flights of eight hours or greater"},
)
LIMITS = {rule["name"]: rule["minutes"] for rule in DURATION_RULES}

# Handbook-specific conventions shown by booking_requirements, beyond the template's (none here).
CONVENTIONS = ()

# Lines 427-429: a connecting itinerary counts toward the lowest available airfare when it has "no more than
# one layover (involving a plane change) each way, and such layover is no more than 2 hours".
MOST_LAYOVERS = 1
LONGEST_LAYOVER = 120
# Lines 286-287: "the number of Blackbaud employees traveling together on the same flight must not exceed
# three members of the Executive Leadership Team".
MOST_LEADERS_PER_FLIGHT = 3
# Lines 383-384 ("under four hours of driving time") and 408 ("a minimum 7 day"): soft rules that never
# change the decision; a trip they touch also accepts their section.
DRIVING_MINUTES = 240
ADVANCE_DAYS = 7

LONG_PHRASE = "exceeding 8 hours (whether a single segment or multiple segments combined)"
UPGRADEABLE_PHRASE = "can be booked in an upgradeable fare"


def over_minutes(rule, segments, elapsed):
    """``over`` on one direction's segments and elapsed minutes."""
    limit = LIMITS[rule]
    if rule == "international-long":
        if sum(segment.scheduled_minutes for segment in segments) > limit:
            return True
        return False if elapsed <= limit else None
    if rule == "arrival-lounge":
        if any(segment.scheduled_minutes >= limit for segment in segments):
            return True
        return False if elapsed < limit else None
    raise ValueError(f"unknown duration rule {rule!r}")


def over(rule, offer):
    """True, False or None (unclear): whether ``offer``'s outbound travel is over the handbook's ``rule``."""
    return over_minutes(rule, offer.segments, offer.elapsed_minutes)


def over_trip(offer):
    """The long-travel verdict of an offer, both directions of a round trip agreeing."""
    verdicts = {over("international-long", offer)}
    if offer.return_segments:
        verdicts.add(over_minutes("international-long", offer.return_segments, offer.return_elapsed_minutes))
    if len(verdicts) != 1:
        raise ValueError("a round trip whose two directions fall on different sides of the limit is not modelled")
    return verdicts.pop()


def by_value(items):
    return sorted(set(items), key=lambda item: item.value)


def answer(decision, offers, reasons, approvers, clauses, why, phrase=""):
    return {
        "decision": decision,
        "offer_ids": sorted(offer.offer_id for offer in offers),
        "cabins": by_value(offer.cabin for offer in offers) or [Cabin.NONE],
        "reason_codes": by_value(reasons),
        "approvers": by_value(approvers),
        "clauses": by_value(clauses),
        "unclear_phrase": phrase,
        "explanation": why,
    }


def refuse(reasons, clauses, why):
    return answer(Decision.REFUSE, [], reasons, [Approver.NONE], clauses, why)


def cheapest(offers):
    if not offers:
        return []
    low = min(offer.fare_cents for offer in offers)
    return [offer for offer in offers if offer.fare_cents == low]


def signed(trip, subject, roles):
    return [record for record in trip.sign_offs if record.subject == subject and record.role in roles]


def unused_sign_offs(trip):
    """Approvers a decision that relies on nobody accepts: NONE, and the role of any sign-off on file that the
    decision does not use (a business sign-off on an economy booking). The approver field names the sign-off
    a decision relies on; a reader may also name one that is on file and was weighed, so both are accepted."""
    return [Approver.NONE, *(record.role for record in trip.sign_offs)]


def relied_on(roles):
    """Approvers a BOOK that rests on sign-offs already on file accepts: their roles, and NONE, since readers
    split on whether a routine sign-off already given is one the decision "relies on" (template SYNC_NOTES 4').
    A hold accepts only the role it waits for."""
    return [Approver.NONE, *roles]


def is_upgradeable(trip, offer):
    return offer.cabin == Cabin.ECONOMY and any(
        rule.flight_number == offer.segments[0].flight_number and rule.fare_cents == offer.fare_cents
        for rule in trip.upgradeable_fares)


def leaders_ok(trip, offer):
    """Lines 286-288: with the traveller, no flight of the offer may carry more than three members of the
    Executive Leadership Team."""
    if not trip.on_leadership_team:
        return True
    flights = [(segment.flight_number, segment.depart_local[:10]) for segment in offer.segments + offer.return_segments]
    for flight in flights:
        others = sum(1 for colleague in trip.colleagues_on_flights
                     if colleague.on_leadership_team and (colleague.flight_number, colleague.date) == flight)
        if others + 1 > MOST_LEADERS_PER_FLIGHT:
            return False
    return True


def within_criteria(offer):
    """Lines 427-429: at most one plane change each way, each no longer than two hours."""
    for layovers in (offer.layover_minutes, offer.return_layover_minutes):
        if len(layovers) > MOST_LAYOVERS or any(minutes > LONGEST_LAYOVER for minutes in layovers):
            return False
    return True


def class_clauses(domestic):
    return [Clause.CLASS_OF_SERVICE, Clause.DOMESTIC_CLASS if domestic else Clause.INTERNATIONAL_CLASS]


def solve(trip, offers, hidden):
    """The answer key for one trip and the offers on its route and date: the decision, and every accepted
    offer id, cabin, reason, approver and section. ``hidden`` (the scenario's answer_key_inputs) is unused
    by this handbook."""
    if hidden:
        raise ValueError("this handbook's scenarios carry no answer_key_inputs")
    if trip.purpose_kind == Purpose.PERSONAL:
        return refuse([ReasonCode.PERSONAL_TRAVEL_NOT_COVERED, ReasonCode.OUTSIDE_POLICY_SCOPE],
                      [Clause.PERSONAL_VACATION, Clause.RESPONSIBILITY],
                      "Lines 296-298: employees are not permitted to book personal air travel using Concur and must "
                      "use their own payment methods; lines 128-129: the company pays for travel connected with company "
                      "business. The company buys no ticket.")
    if trip.tickets_held:
        same = [ticket for ticket in trip.tickets_held if (ticket.origin, ticket.destination, ticket.date) ==
                (trip.origin.code, trip.destination.code, trip.travel_date)]
        if not same:
            raise ValueError("a held ticket for another trip is not modelled")
        return refuse([ReasonCode.DOUBLE_BOOKING_PROHIBITED, ReasonCode.NO_COMPLIANT_OFFER], [Clause.DOUBLE_BOOKINGS],
                      "Line 455: double-bookings and back-to-back flights are prohibited; the traveller already "
                      "holds a ticket for this trip, so no second ticket is bought.")
    domestic = trip.origin.country == trip.destination.country == trip.home_country
    if trip.origin.country != trip.home_country:
        raise ValueError("a trip that does not start in the traveller's home country is not modelled")
    # Lines 412-413 and 432-433: the lowest available airfare, nonrefundable, never an upgradeable fare; the
    # leadership-team limit of lines 286-288 rules out a flight that would carry too many of its members.
    seated = [offer for offer in offers if offer.seats_available]
    allowed = [offer for offer in seated if not offer.refundable and not is_upgradeable(trip, offer)
               and leaders_ok(trip, offer)]
    economy = [offer for offer in allowed if offer.cabin == Cabin.ECONOMY]
    lowest = cheapest(economy)
    if not lowest:
        raise ValueError("no economy offer can be bought")
    if not all(within_criteria(offer) for offer in lowest):
        raise ValueError("a cheapest fare outside the connection criteria (lines 427-429) is not modelled")
    refundable_cheaper = any(offer.refundable and offer.fare_cents < lowest[0].fare_cents
                             for offer in seated if offer.cabin == Cabin.ECONOMY)
    leaders_moved = any(not leaders_ok(trip, offer) and offer.fare_cents < lowest[0].fare_cents
                        for offer in seated if offer.cabin == Cabin.ECONOMY)
    if trip.passenger == Passenger.SPOUSE_OR_COMPANION:
        return companion(trip, lowest)
    if trip.passenger != Passenger.EMPLOYEE:
        raise ValueError(f"a {trip.passenger.value} passenger is not modelled")
    if trip.requested_cabin == Cabin.BUSINESS:
        if trip.wants_upgradeable_fare or trip.loyalty_airline:
            raise ValueError("a business request with a fare or airline wish is not modelled")
        if domestic:
            return domestic_business(trip, allowed, lowest)
        return international_business(trip, seated, allowed, lowest)
    if trip.requested_cabin != Cabin.ECONOMY:
        raise ValueError(f"a {trip.requested_cabin.value} request is not modelled")
    if trip.wants_upgradeable_fare:
        return upgradeable(trip, seated, lowest, domestic)
    return economy_answer(trip, lowest, domestic, refundable_cheaper, leaders_moved)


def economy_answer(trip, lowest, domestic, refundable_cheaper, leaders_moved):
    """An economy request: the lowest available airfare (lines 402 and 412-413), with the sections of any rule
    that removed a cheaper offer or that the trip touches."""
    reasons, clauses = [ReasonCode.LOWEST_FARE], [Clause.LOWEST_AIRFARE, *class_clauses(domestic)]
    notes = ["lines 412-413: the lowest available airfare"]
    if refundable_cheaper:
        reasons.append(ReasonCode.REFUNDABLE_FARE_NOT_ALLOWED)
        notes.append("line 432 (and line 397 for a domestic trip): a cheaper refundable fare cannot be booked")
    if leaders_moved:
        reasons.append(ReasonCode.TRAVELLER_LIMIT_PER_FLIGHT)
        clauses.append(Clause.TRAVELING_TOGETHER)
        notes.append("lines 286-288: the cheaper flight already carries three leadership-team members")
    elif trip.on_leadership_team:
        clauses.append(Clause.TRAVELING_TOGETHER)
        notes.append("lines 286-288: the chosen flight keeps within three leadership-team members")
    if trip.loyalty_airline:
        if all(offer.carrier == trip.loyalty_airline for offer in lowest):
            raise ValueError("a loyalty wish that the lowest fare already meets is not modelled")
        reasons.append(ReasonCode.LOYALTY_PROGRAM_PREFERENCE)
        clauses.append(Clause.FREQUENT_FLIER)
        notes.append("lines 442-444: a frequent flier programme may not add cost beyond the lowest available airfare")
    if 0 < trip.driving_minutes < DRIVING_MINUTES:
        clauses.append(Clause.AIR_TRAVEL_GENERAL)
        notes.append("lines 383-384: driving must only be considered; the traveller has, and flies")
    if days_between(trip.booking_date, trip.travel_date) < ADVANCE_DAYS:
        clauses.append(Clause.ADVANCE_PURCHASE)
        notes.append("lines 408-409: the 7-day advance planning applies 'whenever possible', so a late booking still "
                     "gets the lowest fare")
    return answer(Decision.BOOK, lowest, reasons, unused_sign_offs(trip), clauses, "; ".join(notes) + ".")


def companion(trip, lowest):
    """Lines 267-271: a spouse or companion's expenses are reimbursed where the travel was authorized in advance
    by a Senior Vice President or higher, to help entertain clients' spouses."""
    roles = [Approver.SENIOR_VICE_PRESIDENT, Approver.CHIEF_EXECUTIVE]
    if trip.purpose_kind != Purpose.CLIENT_ENTERTAINING or not signed(trip, SignOffSubject.COMPANION_TRAVEL, roles):
        raise ValueError("a companion without a senior vice president's advance authorization is not modelled")
    if trip.requested_cabin != Cabin.ECONOMY or not trip.accompanies:
        raise ValueError("a companion outside economy, or with nobody accompanied, is not modelled")
    return answer(Decision.BOOK, lowest, [ReasonCode.COMPANION_TRAVEL_AUTHORIZED, ReasonCode.LOWEST_FARE],
                  relied_on([Approver.SENIOR_VICE_PRESIDENT]), [Clause.SPOUSE_COMPANION, Clause.LOWEST_AIRFARE],
                  "Lines 267-271: the companion's trip to help entertain clients' spouses was authorized in advance by "
                  "a Senior Vice President; lines 412-413: at the lowest available airfare.")


def business_offers(allowed):
    wanted = cheapest([offer for offer in allowed if offer.cabin == Cabin.BUSINESS])
    if not all(within_criteria(offer) for offer in wanted):
        raise ValueError("a cheapest business fare outside the connection criteria (lines 427-429) is not modelled")
    return wanted


def domestic_business(trip, allowed, lowest):
    """Lines 397-399: domestic air purchases are coach class, regardless of flight time; a medical exception
    needs the approval of both the travel department and the appropriate Vice President."""
    if trip.medical_need_on_file:
        needed = (Approver.TRAVEL_DEPARTMENT, Approver.VICE_PRESIDENT)
        have = {record.role for record in signed(trip, SignOffSubject.MEDICAL_EXCEPTION, needed)}
        if have != set(needed):
            raise ValueError("a medical exception missing one of its two approvals is not modelled")
        wanted = business_offers(allowed)
        if not wanted:
            raise ValueError("a medical exception with no business offer is not modelled")
        return answer(Decision.BOOK, wanted, [ReasonCode.MEDICAL_NEED], relied_on(needed), class_clauses(True),
                      "Lines 398-399: a medical exception approved by both the travel department and the Vice "
                      "President; the cheapest nonrefundable business fare.")
    return answer(Decision.BOOK, lowest,
                  [ReasonCode.UPGRADE_NOT_ELIGIBLE, ReasonCode.LOWEST_FARE, ReasonCode.LONG_FLIGHT_CONDITION_NOT_MET],
                  unused_sign_offs(trip), [*class_clauses(True), Clause.LOWEST_AIRFARE],
                  "Line 397: domestic air purchases are coach class, regardless of flight time, so a business sign-off "
                  "does not matter; the lowest available airfare.")


def long_verdict(allowed):
    verdicts = {over_trip(offer) for offer in allowed}
    if len(verdicts) != 1:
        raise ValueError("offers on different sides of the long-travel limit are not modelled (set background 0)")
    return verdicts.pop()


def international_business(trip, seated, allowed, lowest):
    """Lines 402-404: international travel exceeding 8 hours may be booked in business class with the prior
    approval of the traveller's Vice-President."""
    verdict = long_verdict(allowed)
    wanted = business_offers(allowed)
    if verdict is False:
        return answer(Decision.BOOK, lowest,
                      [ReasonCode.LONG_FLIGHT_CONDITION_NOT_MET, ReasonCode.UPGRADE_NOT_ELIGIBLE, ReasonCode.LOWEST_FARE],
                      unused_sign_offs(trip), [*class_clauses(False), Clause.LOWEST_AIRFARE],
                      "Lines 402-404: the travel does not exceed 480 minutes, so business is not available whoever "
                      "signed; line 402: the lowest possible airfare.")
    if not wanted:
        raise ValueError("a business request with no business offer is not modelled")
    approved = signed(trip, SignOffSubject.BUSINESS_CLASS, [Approver.VICE_PRESIDENT])
    if verdict is None:
        if not approved:
            raise ValueError("an unclear duration without the Vice-President's approval is not modelled")
        return answer(Decision.FLAG_FOR_APPROVAL, wanted, [ReasonCode.UNCLEAR_POLICY_TEXT],
                      [Approver.NOT_NAMED, Approver.TRAVEL_DEPARTMENT, Approver.VICE_PRESIDENT], class_clauses(False),
                      "Lines 402-404: the flights add up to 480 minutes or less but the journey with its connection "
                      "is longer; the handbook does not say whether ground time counts. Lines 139-141 send policy "
                      "questions to the Travel Desk; the held business fare also relies on the Vice-President's "
                      "sign-off on file.", phrase=LONG_PHRASE)
    if not approved:
        return answer(Decision.FLAG_FOR_APPROVAL, wanted, [ReasonCode.APPROVAL_REQUIRED], [Approver.VICE_PRESIDENT],
                      class_clauses(False),
                      "Lines 402-404: the travel exceeds 480 minutes, but business needs the prior approval of the "
                      "traveller's Vice-President, which is not on file: hold the business fare for it.")
    reasons = [ReasonCode.LONG_FLIGHT_APPROVED, ReasonCode.INTERNATIONAL_LONG_FLIGHT]
    clauses = class_clauses(False)
    if any(offer.refundable and offer.cabin == Cabin.BUSINESS and offer.fare_cents < wanted[0].fare_cents
           for offer in seated):
        reasons.append(ReasonCode.REFUNDABLE_FARE_NOT_ALLOWED)
        clauses.append(Clause.LOWEST_AIRFARE)
    return answer(Decision.BOOK, wanted, reasons, relied_on([Approver.VICE_PRESIDENT]), clauses,
                  "Lines 402-404: the travel exceeds 480 minutes and the traveller's Vice-President approved business "
                  "in advance; the cheapest nonrefundable business fare (line 432).")


def upgradeable(trip, seated, lowest, domestic):
    """An economy request for an upgradeable fare. Line 433: "Full Y fares, or upgradeable fares, are not
    allowed to be booked"; lines 402-404: international travel exceeding 8 hours "can be booked in an
    upgradeable fare". Within the limit only line 433 applies; over it the two lines contradict each other and
    the handbook states no order between them."""
    wanted = cheapest([offer for offer in seated if is_upgradeable(trip, offer) and not offer.refundable])
    if not wanted:
        raise ValueError("an upgradeable request with no upgradeable offer is not modelled")
    verdict = False if domestic else long_verdict([offer for offer in seated if not offer.refundable])
    if verdict is False:
        reasons = [ReasonCode.UPGRADE_NOT_ELIGIBLE, ReasonCode.LOWEST_FARE]
        if not domestic:
            reasons.append(ReasonCode.LONG_FLIGHT_CONDITION_NOT_MET)
        return answer(Decision.BOOK, lowest, reasons, unused_sign_offs(trip),
                      [Clause.LOWEST_AIRFARE, *class_clauses(domestic)],
                      "Line 433: upgradeable fares are not allowed to be booked, and the travel does not exceed 480 "
                      "minutes, so lines 402-404 do not reach it; the lowest available airfare.")
    if verdict is None:
        raise ValueError("an upgradeable request on an unclear duration is not modelled")
    return answer(Decision.FLAG_FOR_APPROVAL, wanted, [ReasonCode.UNCLEAR_POLICY_TEXT],
                  [Approver.NOT_NAMED, Approver.TRAVEL_DEPARTMENT],
                  [Clause.LOWEST_AIRFARE, *class_clauses(False)],
                  "Lines 402-404 let international travel over 480 minutes be booked in an upgradeable fare, but line "
                  "433 says upgradeable fares are not allowed to be booked, and the handbook gives no order between "
                  "them. Lines 139-141 send policy questions to the Travel Desk.", phrase=UPGRADEABLE_PHRASE)
