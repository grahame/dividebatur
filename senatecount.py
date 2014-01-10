#!/usr/bin/env python3

import sys, os, csv, itertools, pickle, lzma, json
from collections import namedtuple
from counter import Ticket, PreferenceFlow, PapersForCount, SenateCounter

def named_tuple_iter(name, reader, header, **kwargs):
    field_names = [ t for t in [t.strip().replace('-', '_') for t in header] if t ]
    typ = namedtuple(name, field_names)
    mappings = []
    for field_name in kwargs:
        idx = field_names.index(field_name)
        mappings.append((idx, kwargs[field_name]))
    for row in reader:
        for idx, map_fn in mappings:
            row[idx] = map_fn(row[idx])
        yield typ(*row)

def int_or_none(s):
    try:
        return int(s)
    except ValueError:
        return None

class Candidates:
    def __init__(self, candidates_csv):
        self.by_id = {}
        self.by_name_party = {}
        self.candidates = []
        self.load(candidates_csv)

    def load(self, candidates_csv):
        with lzma.open(candidates_csv, 'rt') as fd:
            reader = csv.reader(fd)
            version = next(reader)
            header = next(reader)
            for candidate in named_tuple_iter('Candidate', reader, header, CandidateID=int):
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

class SenateATL:
    def __init__(self, state_name, candidates, gvt_csv, firstprefs_csv):
        self.gvt = {}
        self.ticket_votes = []
        self.individual_candidate_ids =[]
        self.candidate_order = {}
        self.candidate_title = {}
        self.btl_firstprefs = {}
        self.load_tickets(candidates, gvt_csv)
        self.load_first_preferences(state_name, firstprefs_csv)

    def load_tickets(self, candidates, gvt_csv):
        with lzma.open(gvt_csv, 'rt') as fd:
            reader = csv.reader(fd)
            header = next(reader)
            it = sorted(named_tuple_iter('GvtRow', reader, header, Preference=int, TicketNo=int, Ticket=lambda t: t.strip()), key=lambda gvt: (gvt.StateAb, gvt.Ticket, gvt.TicketNo, gvt.Preference))
            for (state_ab, ticket, ticket_no), g in itertools.groupby(it, lambda gvt: (gvt.StateAb, gvt.Ticket, gvt.TicketNo)):
                prefs = []
                for ticket_entry in g:
                    candidate = candidates.lookup_name_party(ticket_entry.Surname, ticket_entry.GivenName, ticket_entry.Party)
                    prefs.append((ticket_entry.Preference, candidate.CandidateID))
                if ticket not in self.gvt:
                    self.gvt[ticket] = []
                self.gvt[ticket].append(PreferenceFlow(tuple(prefs)))

    def load_first_preferences(self, state_name, firstprefs_csv):
        with lzma.open(firstprefs_csv, 'rt') as fd:
            reader = csv.reader(fd)
            version = next(reader)
            header = next(reader)
            for idx, row in enumerate(named_tuple_iter('StateFirstPrefs', reader, header, TotalVotes=int, CandidateID=int)):
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
        for group, n in self.ticket_votes:
            yield Ticket(tuple(self.gvt[group])), n

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
    """

    def __init__(self, candidates, btl_csv):
        self.ticket_votes = {}
        self.load_btl(candidates, btl_csv)

    def load_btl(self, candidates, btl_csv):
        with lzma.open(btl_csv, 'rt') as fd:
            reader = csv.reader(fd)
            version = next(reader)
            header = next(reader)
            it = named_tuple_iter('BtlRow', reader, header, Batch=int, Paper=int, Preference=int_or_none, CandidateId=int)
            for key, g in itertools.groupby(it, lambda r: (r.Batch, r.Paper)):
                ticket_data = []
                for row in sorted(g, key=lambda x: x.CandidateId):
                    ticket_data.append((row.Preference, row.CandidateId))
                ticket = Ticket((PreferenceFlow(ticket_data),))
                if ticket not in self.ticket_votes:
                    self.ticket_votes[ticket] = 0
                self.ticket_votes[ticket] += 1

    def get_tickets(self):
        for ticket in sorted(self.ticket_votes, key=lambda x: self.ticket_votes[x]):
            yield ticket, self.ticket_votes[ticket]

def senate_count(state_name, vacancies, data_dir, automation, **kwargs):
    def load_tickets(ticket_obj):
        if ticket_obj is None:
            return
        for ticket, n in ticket_obj.get_tickets():
            tickets_for_count.add_ticket(ticket, n)
    df = lambda x: os.path.join(data_dir, x)
    candidates = Candidates(df('SenateCandidatesDownload-17496.csv.xz'))
    atl = SenateATL(state_name, candidates, df('wa-gvt.csv.xz'), df('SenateFirstPrefsByStateByVoteTypeDownload-17496.csv.xz'))
    btl = SenateBTL(candidates, df('SenateStateBTLPreferences-17496-WA.csv.xz'))
    tickets_for_count = PapersForCount()
    load_tickets(atl)
    load_tickets(btl)
    counter = SenateCounter(
        vacancies,
        tickets_for_count,
        atl.get_candidate_ids(),
        lambda candidate_id: atl.get_candidate_order(candidate_id),
        lambda candidate_id: atl.get_candidate_title(candidate_id),
        automation,
        **kwargs)

def main():
    config_file = sys.argv[1]
    base_dir = os.path.dirname(os.path.abspath(config_file))
    with open(config_file) as fd:
        config = json.load(fd)
    for count in config['count']:
        data_dir = os.path.join(base_dir, count['path'])
        senate_count(
            config['state'], config['vacancies'], data_dir,
            count.get('automation') or [],
            name=count.get('name'),
            description=count.get('description'),
            house=config['house'],
            state=config['state'])

if __name__ == '__main__':
    main()
