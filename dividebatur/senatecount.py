#!/usr/bin/env python3

import sys
import os
import json
import tempfile
import difflib
import re
import glob
from pprint import pprint, pformat
from .counter import PapersForCount, SenateCounter
from .aecdata import Candidates, SenateATL, SenateBTL


class SenateCountPost2015:
    def __init__(self, state_name, data_dir):
        def df(x):
            return glob.glob(os.path.join(data_dir, x))[0]

        self.candidates = Candidates(df('SenateCandidatesDownload-*.csv.xz'))


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

    method_cls = None
    if config['method'] == 'AusSenatePre2015':
        method_cls = SenateCountPre2015
    elif config['method'] == 'AusSenatePost2015':
        method_cls = SenateCountPost2015
    senate_count_data = []
    for count in config['count']:
        data_dir = os.path.join(base_dir, count['path'])
        count = method_cls(config['state'], data_dir)
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
