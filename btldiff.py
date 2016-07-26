#!/usr/bin/env python3

import sys
from senatecount import Candidates, SenateBTL

if __name__ == '__main__':
    candidates = Candidates(sys.argv[1])
    a = SenateBTL(candidates, sys.argv[2])
    b = SenateBTL(candidates, sys.argv[3])

    in_a = set(a.ticket_votes.keys())
    in_b = set(b.ticket_votes.keys())

    papers_removed = []
    papers_added = []

    def print_ticket(ticket):
        assert(len(ticket) == 1)  # BTL
        preference_flow = ticket.preference_flows[0]
        for preference, candidate_id in preference_flow.preferences:
            candidate = candidates.lookup_id(candidate_id)
            if preference is not None:
                p = "%2d" % preference
            else:
                p = " ?"
            print("    %2s. %s, %s" % (p, candidate.Surname, candidate.GivenNm))

    for ticket in (in_a - in_b):
        print("%d papers removed with ticket:" % (a.ticket_votes[ticket]))
        print_ticket(ticket)
        papers_removed += a.ticket_votes[ticket]

    for ticket in (in_b - in_a):
        print("%d papers added with ticket:" % (b.ticket_votes[ticket]))
        print_ticket(ticket)
        papers_added += b.ticket_votes[ticket]

    for ticket in in_a.intersection(in_b):
        before = a.ticket_votes[ticket]
        after = b.ticket_votes[ticket]
        if before != after:
            print("had %d papers, now have %d (change %d) with ticket:" % (
                before, after, after - before))
            print_ticket(ticket)
