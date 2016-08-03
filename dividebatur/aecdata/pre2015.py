import itertools
import csv
from collections import defaultdict

from .utils import int_or_none, named_tuple_iter, ticket_sort_key
from ..counter import Ticket


class SenateATL:
    "parses AEC candidates Senate ATL data file (pre-2015)"

    def __init__(self, state_name, gvt_csv, firstprefs_csv):
        self.state_name = state_name
        self.gvt = defaultdict(list)
        self.ticket_votes = []
        self.individual_candidate_ids = []
        self.candidate_order = {}
        self.candidate_title = {}
        self.btl_firstprefs = {}
        self.raw_ticket_data = []
        self.load_tickets(gvt_csv)
        self.load_first_preferences(state_name, firstprefs_csv)

    def load_tickets(self, gvt_csv):
        with open(gvt_csv, 'rt') as fd:
            reader = csv.reader(fd)
            # skip introduction line
            next(reader)
            header = next(reader)
            it = sorted(
                named_tuple_iter('GvtRow', reader, header, PreferenceNo=int, TicketNo=int, CandidateID=int, OwnerTicket=lambda t: t.strip()),
                key=lambda gvt: (gvt.State, ticket_sort_key(gvt.OwnerTicket), gvt.TicketNo, gvt.PreferenceNo))
            for (state_ab, ticket, ticket_no), g in itertools.groupby(
                    it, lambda gvt: (gvt.State, gvt.OwnerTicket, gvt.TicketNo)):
                if state_ab != self.state_name:
                    continue
                prefs = []
                for ticket_entry in g:
                    prefs.append(
                        (ticket_entry.PreferenceNo, ticket_entry.CandidateID))

                non_none = [x for x in prefs if x[0] is not None]
                self.raw_ticket_data.append(sorted(non_none, key=lambda x: x[0]))
                self.gvt[ticket].append(Ticket(tuple(prefs)))

    def load_first_preferences(self, state_name, firstprefs_csv):
        with open(firstprefs_csv, 'rt') as fd:
            reader = csv.reader(fd)
            next(reader)  # skip the version
            header = next(reader)
            for idx, row in enumerate(
                named_tuple_iter(
                    'StateFirstPrefs', reader, header, TotalVotes=int, CandidateID=int)):
                if row.StateAb == state_name:
                    if row.CandidateDetails.endswith('Ticket Votes'):
                        self.ticket_votes.append((row.Ticket, row.TotalVotes))
                    elif row.CandidateDetails != 'Unapportioned':
                        assert(row.CandidateID not in self.btl_firstprefs)
                        self.btl_firstprefs[row.CandidateID] = row.TotalVotes
                        self.individual_candidate_ids.append(row.CandidateID)
                self.candidate_order[row.CandidateID] = idx
                self.candidate_title[row.CandidateID] = row.CandidateDetails

    def get_tickets(self):
        # GVT handling: see s272 of the electoral act (as collated in 2013)
        for group, n in self.ticket_votes:
            size = len(self.gvt[group])
            assert(size <= 3)
            remainder = n % size
            # TODO: implement some randomization here
            remainder_pattern = [1] * remainder + [0] * (size - remainder)
            remainder_pattern = [0] * (size - remainder) + [1] * (remainder)
            if remainder:
                print("NOTE: GVT split ticket remainder, AEO input needed:", remainder_pattern)
            # remainder_pattern = [0] * (size-remainder) + [1] * remainder
            for ticket, extra in zip(self.gvt[group], remainder_pattern):
                yield ticket, int(n / size) + extra

    def get_candidate_ids(self):
        return self.individual_candidate_ids

    def get_candidate_order(self, candidate_id):
        return self.candidate_order[candidate_id]

    def get_candidate_title(self, candidate_id):
        return self.candidate_title[candidate_id]


class SenateBTL:
    """
    build up Ticket instances for each below-the-line vote in the AEC dataset
    aggregate BTL votes with the same preference flow together
    (pre-2015)
    """

    def __init__(self, btl_csv):
        self.ticket_votes = defaultdict(int)
        self.raw_ticket_data = []
        self.load_btl(btl_csv)

    def load_btl(self, btl_csv):
        with open(btl_csv, 'rt') as fd:
            reader = csv.reader(fd)
            next(reader)  # skip the version
            header = next(reader)
            it = named_tuple_iter(
                'BtlRow',
                reader,
                header,
                Batch=int,
                Paper=int,
                Preference=int_or_none,
                CandidateId=int)
            self.total_ticket_data = []
            for key, g in itertools.groupby(it, lambda r: (r.Batch, r.Paper)):
                ticket_data = []
                for row in sorted(g, key=lambda x: x.CandidateId):
                    ticket_data.append((row.Preference, row.CandidateId))
                non_none = [x for x in ticket_data if x[0] is not None]
                self.raw_ticket_data.append(sorted(non_none, key=lambda x: x[0]))
                ticket = Ticket(ticket_data)
                self.ticket_votes[ticket] += 1

    def get_tickets(self):
        for ticket in sorted(self.ticket_votes, key=lambda x: self.ticket_votes[x]):
            yield ticket, self.ticket_votes[ticket]
