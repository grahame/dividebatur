import lzma
import csv
import itertools
from collections import namedtuple
from . counter import Ticket


def int_or_none(s):
    try:
        return int(s)
    except ValueError:
        return None


def ticket_sort_key(ticket):
    "sort key for an ATL ticket, eg. A..Z, AA..ZZ"
    return (len(ticket), ticket)


def named_tuple_iter(name, reader, header, **kwargs):
    field_names = [t for t in [t.strip().replace('-', '_')
                               for t in header] if t]
    typ = namedtuple(name, field_names)
    mappings = []
    for field_name in kwargs:
        idx = field_names.index(field_name)
        mappings.append((idx, kwargs[field_name]))
    for row in reader:
        for idx, map_fn in mappings:
            row[idx] = map_fn(row[idx])
        yield typ(*row)


class AllCandidates:
    "parse AEC 'all candidates' CSV file"

    def __init__(self, csv_file, state):
        self.state = state
        self.load(csv_file)

    def load(self, csv_file):
        self.groups = {}
        with lzma.open(csv_file, 'rt') as fd:
            reader = csv.reader(fd)
            header = next(reader)
            for candidate in sorted(named_tuple_iter('AllCandidate', reader, header, ballot_position=int), key=lambda row: (ticket_sort_key(row.ticket), row.ballot_position)):
                if candidate.state_ab != self.state:
                    continue
                if candidate.nom_ty != 'S':
                    continue
                if candidate.ticket not in self.groups:
                    self.groups[candidate.ticket] = []
                self.groups[candidate.ticket].append(candidate)


class SenateFlows:
    "work out the flow per group above the line (post 2015)"

    def __init__(self, candidates, all_candidates):
        self.groups = []
        self.flows = {}
        self.btl = []
        self.candidate_title = {}
        self.match(candidates, all_candidates)

    def get_candidate_ids(self):
        return list(self.btl)

    def get_candidate_title(self, candidate_id):
        return self.candidate_title[candidate_id]

    def get_candidate_order(self, candidate_id):
        return self.btl.index(candidate_id)

    def match(self, candidates, all_candidates):
        # UG: ungrouped (not a real group, placing a '1' in this ATL is a trap). doesn't
        # count for ATL flows, but does count for BTL ordering
        all_groups = [t for t in sorted(all_candidates.groups.keys(), key=ticket_sort_key)]
        for group in all_groups:
            ac = all_candidates.groups[group]
            for all_candidate in ac:
                k = (all_candidate.surname, all_candidate.ballot_given_nm, all_candidate.party_ballot_nm)
                matched = candidates.by_name_party[k]
                if group != 'UG':
                    if group not in self.flows:
                        self.flows[group] = []
                    self.flows[group].append(matched.CandidateID)
                self.btl.append(matched.CandidateID)
                self.candidate_title[matched.CandidateID] = matched.Surname + ', ' + matched.GivenNm
        self.groups = [t for t in all_groups if t != 'UG']


class FormalPreferences:
    "parse AEC 'formal preferences' CSV file"

    def __init__(self, csv_file):
        self._csv_file = csv_file

    def __iter__(self):
        def parse_prefs(s):
            ", delimited, with * and / meaning 1"
            return [int_or_none(t) for t in s.replace('*', '1').replace('/', '1').split(',')]
        with lzma.open(self._csv_file, 'rt') as fd:
            reader = csv.reader(fd)
            header = next(reader)
            dummy = next(reader)
            assert(dummy == ['------------', '---------------------', '---------------------', '-------', '-------', '-----------'])
            for pref in named_tuple_iter('FormalPref', reader, header, Preferences=parse_prefs):
                yield pref


class Candidates:
    "parses AEC candidates CSV file"

    def __init__(self, candidates_csv):
        self.by_id = {}
        self.by_name_party = {}
        self.candidates = []
        self.load(candidates_csv)

    def load(self, candidates_csv):
        with lzma.open(candidates_csv, 'rt') as fd:
            reader = csv.reader(fd)
            next(reader)  # skip the version
            header = next(reader)
            for candidate in named_tuple_iter(
                    'Candidate', reader, header, CandidateID=int):
                self.candidates.append(candidate)
                assert(candidate.CandidateID not in self.by_id)
                self.by_id[candidate.CandidateID] = candidate
                k = (candidate.Surname, candidate.GivenNm, candidate.PartyNm)
                assert(k not in self.by_name_party)
                self.by_name_party[k] = candidate

    def lookup_id(self, candidate_id):
        return self.by_id[candidate_id]

    def lookup_name_party(self, surname, given_name, party):
        return self.by_name_party[(surname, given_name, party)]

    def get_parties(self):
        return dict((t.PartyAb, t.PartyNm) for t in self.candidates if t)


class SenateATL:
    "parses AEC candidates Senate ATL data file (pre-2015)"

    def __init__(self, state_name, candidates, gvt_csv, firstprefs_csv):
        self.state_name = state_name
        self.gvt = {}
        self.ticket_votes = []
        self.individual_candidate_ids = []
        self.candidate_order = {}
        self.candidate_title = {}
        self.btl_firstprefs = {}
        self.raw_ticket_data = []
        self.load_tickets(candidates, gvt_csv)
        self.load_first_preferences(state_name, firstprefs_csv)

    def load_tickets(self, candidates, gvt_csv):
        with lzma.open(gvt_csv, 'rt') as fd:
            reader = csv.reader(fd)
            # skip introduction line
            next(reader)
            header = next(reader)
            it = sorted(
                named_tuple_iter('GvtRow', reader, header, PreferenceNo=int, TicketNo=int, OwnerTicket=lambda t: t.strip()),
                key=lambda gvt: (gvt.State, ticket_sort_key(gvt.OwnerTicket), gvt.TicketNo, gvt.PreferenceNo))
            for (state_ab, ticket, ticket_no), g in itertools.groupby(
                    it, lambda gvt: (gvt.State, gvt.OwnerTicket, gvt.TicketNo)):
                if state_ab != self.state_name:
                    continue
                prefs = []
                for ticket_entry in g:
                    candidate = candidates.lookup_name_party(
                        ticket_entry.Surname, ticket_entry.GivenNm, ticket_entry.PartyNm)
                    prefs.append(
                        (ticket_entry.PreferenceNo, candidate.CandidateID))

                non_none = [x for x in prefs if x[0] is not None]
                self.raw_ticket_data.append(sorted(non_none, key=lambda x: x[0]))
                if ticket not in self.gvt:
                    self.gvt[ticket] = []
                self.gvt[ticket].append(Ticket(tuple(prefs)))

    def load_first_preferences(self, state_name, firstprefs_csv):
        with lzma.open(firstprefs_csv, 'rt') as fd:
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
            if remainder:
                print("NOTE: GVT remainder AEO input needed: ", remainder_pattern)
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

    def __init__(self, candidates, btl_csv):
        self.ticket_votes = {}
        self.raw_ticket_data = []
        self.load_btl(candidates, btl_csv)

    def load_btl(self, candidates, btl_csv):
        with lzma.open(btl_csv, 'rt') as fd:
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
                if ticket not in self.ticket_votes:
                    self.ticket_votes[ticket] = 0
                self.ticket_votes[ticket] += 1

    def get_tickets(self):
        for ticket in sorted(self.ticket_votes, key=lambda x: self.ticket_votes[x]):
            yield ticket, self.ticket_votes[ticket]
