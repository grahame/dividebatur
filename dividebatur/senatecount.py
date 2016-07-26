#!/usr/bin/env python3

import sys
import os
import csv
import itertools
import lzma
import json
import tempfile
import difflib
import re
import glob
from pprint import pprint, pformat
from collections import namedtuple
from . counter import Ticket, PreferenceFlow, PapersForCount, SenateCounter


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
    def __init__(self, state_name, candidates, gvt_csv, firstprefs_csv):
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
            header = next(reader)
            it = sorted(
                named_tuple_iter(
                    'GvtRow',
                    reader,
                    header,
                    Preference=int,
                    TicketNo=int,
                    Ticket=lambda t: t.strip()),
                key=lambda gvt: (
                    gvt.StateAb,
                    gvt.Ticket,
                    gvt.TicketNo,
                    gvt.Preference))
            for (state_ab, ticket, ticket_no), g in itertools.groupby(
                    it, lambda gvt: (gvt.StateAb, gvt.Ticket, gvt.TicketNo)):
                prefs = []
                for ticket_entry in g:
                    candidate = candidates.lookup_name_party(
                        ticket_entry.Surname, ticket_entry.GivenName, ticket_entry.Party)
                    prefs.append(
                        (ticket_entry.Preference, candidate.CandidateID))

                non_none = [x for x in prefs if x[0] is not None]
                self.raw_ticket_data.append(sorted(non_none, key=lambda x: x[0]))
                if ticket not in self.gvt:
                    self.gvt[ticket] = []
                self.gvt[ticket].append(PreferenceFlow(tuple(prefs)))

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
                ticket = Ticket((PreferenceFlow(ticket_data),))
                if ticket not in self.ticket_votes:
                    self.ticket_votes[ticket] = 0
                self.ticket_votes[ticket] += 1

    def get_tickets(self):
        for ticket in sorted(
                self.ticket_votes,
                key=lambda x: self.ticket_votes[x]):
            yield ticket, self.ticket_votes[ticket]


class SenateCountPre2015:
    def __init__(self, state_name, data_dir):
        def df(x):
            return glob.glob(os.path.join(data_dir, x))[0]

        self.candidates = Candidates(df('SenateCandidatesDownload-*.csv.xz'))
        self.atl = SenateATL(
            state_name, self.candidates, df('wa-gvt.csv.xz'),
            df('SenateFirstPrefsByStateByVoteTypeDownload-*.csv.xz'))
        self.btl = SenateBTL(self.candidates, df('SenateStateBTLPreferences-*-WA.csv.xz'))

        def load_tickets(ticket_obj):
            if ticket_obj is None:
                return
            for ticket, n in ticket_obj.get_tickets():
                self.tickets_for_count.add_ticket(ticket, n)
        self.tickets_for_count = PapersForCount()
        load_tickets(self.atl)
        load_tickets(self.btl)

    def get_tickets_for_count(self):
        return self.tickets_for_count

    def get_candidate_ids(self):
        return self.atl.get_candidate_ids()

    def get_parties(self):
        return self.candidates.get_parties()

    def get_candidate_title(self, candidate_id):
        return self.atl.get_candidate_title(candidate_id)

    def get_candidate_order(self, candidate_id):
        return self.atl.get_candidate_order(candidate_id)

    def get_candidate_party(self, candidate_id):
        return self.candidates.lookup_id(candidate_id).PartyAb,


def senate_count_run(fname, vacancies, tickets_for_count, candidates, atl, btl, *args, **kwargs):
    SenateCounter(
        fname,
        vacancies,
        tickets_for_count,
        candidates.get_parties(),
        atl.get_candidate_ids(),
        lambda candidate_id: atl.get_candidate_order(candidate_id),
        lambda candidate_id: atl.get_candidate_title(candidate_id),
        lambda candidate_id: candidates.lookup_id(candidate_id).PartyAb,
        *args,
        **kwargs)


def verify_test_logs(verified_dir, test_log_dir):
    test_re = re.compile(r'^round_(\d+)\.json')
    rounds = []
    for fname in os.listdir(verified_dir):
        m = test_re.match(fname)
        if m:
            rounds.append(int(m.groups()[0]))

    def fname(d, r):
        return os.path.join(d, 'round_%d.json' % r)

    def getlog(d, r):
        with open(fname(d, r)) as fd:
            return json.load(fd)
    ok = True
    for idx in sorted(rounds):
        v = getlog(verified_dir, idx)
        t = getlog(test_log_dir, idx)
        if v != t:
            print("Round %d: FAIL" % idx)
            print("Log should be:")
            pprint(v)
            print("Log is:")
            pprint(t)
            print("Diff:")
            print(
                '\n'.join(
                    difflib.unified_diff(
                        pformat(v).split('\n'),
                        pformat(t).split('\n'))))
            ok = False
        else:
            print("Round %d: OK" % idx)
    if ok:
        for fname in os.listdir(test_log_dir):
            if test_re.match(fname):
                os.unlink(os.path.join(test_log_dir, fname))
        os.rmdir(test_log_dir)
    return ok


def get_data(config_file, out_dir):
    base_dir = os.path.dirname(os.path.abspath(config_file))
    with open(config_file) as fd:
        config = json.load(fd)
    json_f = os.path.join(out_dir, 'count.json')
    with open(json_f, 'w') as fd:
        obj = {
            'house': config['house'],
            'state': config['state']
        }
        obj['counts'] = [{
            'name': count['name'],
            'description': count['description'],
            'path': count['shortname']}
            for count in config['count']]
        json.dump(obj, fd)

    senate_count_data = []
    for count in config['count']:
        data_dir = os.path.join(base_dir, count['path'])
        count = SenateCountPre2015(config['state'], data_dir)
        senate_count_data.append(count)
    return senate_count_data


def get_outcome(config_file, out_dir, senate_count_data):
    base_dir = os.path.dirname(os.path.abspath(config_file))
    with open(config_file) as fd:
        config = json.load(fd)
    test_logs_okay = True
    for count, count_data in zip(config['count'], senate_count_data):
        test_log_dir = None
        if 'verified' in count:
            test_log_dir = tempfile.mkdtemp(prefix='dividebatur_tmp')
        outf = os.path.join(out_dir, count['shortname'] + '.json')
        print("counting %s -> %s" % (count['name'], outf))
        SenateCounter(
            outf,
            config['vacancies'],
            count_data.get_tickets_for_count(),
            count_data.get_parties(),
            count_data.get_candidate_ids(),
            count_data.get_candidate_order,
            count_data.get_candidate_title,
            count_data.get_candidate_party,
            count.get('automation', []),
            test_log_dir,
            name=count.get('name'),
            description=count.get('description'),
            house=config['house'],
            state=config['state'])
        if test_log_dir is not None:
            if not verify_test_logs(
                    os.path.join(
                        base_dir,
                        count['verified']),
                    test_log_dir):
                test_logs_okay = False
    if not test_logs_okay:
        print("** TESTS FAILED **")
        sys.exit(1)


def main_separate(config_file, out_dir):
    data = get_data(config_file, out_dir)
    get_outcome(config_file, out_dir, data)


def main(config_file, out_dir):
    config_file = sys.argv[1]
    out_dir = sys.argv[2]
    main_separate(config_file, out_dir)

if __name__ == '__main__':
    config_file = sys.argv[1]
    out_dir = sys.argv[2]
    main(config_file=config_file, out_dir=out_dir)
