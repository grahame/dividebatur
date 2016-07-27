#!/usr/bin/env python3

import sys
import os
import json
import tempfile
import difflib
import re
import glob
from pprint import pprint, pformat
from .counter import PapersForCount, SenateCounter, Ticket, PreferenceFlow
from .aecdata import Candidates, SenateATL, SenateBTL, AllCandidates, SenateFlows, FormalPreferences


class SenateCountPost2015:
    def __init__(self, state_name, data_dir):
        def df(x):
            return glob.glob(os.path.join(data_dir, x))[0]

        self.candidates = Candidates(df('SenateCandidatesDownload-*.csv.xz'))
        self.all_candidates = AllCandidates(df('*all-candidates-*.csv.xz'), state_name)
        self.flows = SenateFlows(self.candidates, self.all_candidates)
        self.tickets_for_count = PapersForCount()

        def atl_flow(form):
            by_pref = {}
            for pref, group in zip(form, self.flows.groups):
                if pref is None:
                    continue
                if pref not in by_pref:
                    by_pref[pref] = []
                by_pref[pref].append(group)
            prefs = []
            for i in range(1, len(form) + 1):
                at_pref = by_pref.get(i)
                if not at_pref or len(at_pref) != 1:
                    break
                the_pref = at_pref[0]
                for candidate_id in self.flows.flows[the_pref]:
                    prefs.append((len(prefs) + 1, candidate_id))
            if not prefs:
                return None
            return Ticket((PreferenceFlow(tuple(prefs)), ))

        def btl_flow(form):
            by_pref = {}
            for pref, candidate_id in zip(form, self.flows.btl):
                if pref is None:
                    continue
                if pref not in by_pref:
                    by_pref[pref] = []
                by_pref[pref].append(candidate_id)
            prefs = []
            for i in range(1, len(form) + 1):
                at_pref = by_pref.get(i)
                if not at_pref or len(at_pref) != 1:
                    # must have unique prefs for 1..6, or informal
                    if i <= 6:
                        return None
                    break
                candidate_id = at_pref[0]
                prefs.append((i, candidate_id))
            return Ticket((PreferenceFlow(tuple(prefs)), ))

        atl_n = len(self.flows.groups)
        btl_n = len(self.flows.btl)
        for pref in FormalPreferences(df('*formalpreferences-*.csv.xz')):
            raw_form = pref.Preferences
            assert(len(raw_form) == atl_n + btl_n)
            # BTL takes precedence
            atl = raw_form[:atl_n]
            btl = raw_form[atl_n:]
            form = btl_flow(btl) or atl_flow(atl)
            if form:
                self.tickets_for_count.add_ticket(form, 1)
            else:
                print("informal:", atl, btl)

    def get_tickets_for_count(self):
        return self.tickets_for_count

    def get_candidate_ids(self):
        return self.flows.get_candidate_ids()

    def get_parties(self):
        return self.candidates.get_parties()

    def get_candidate_title(self, candidate_id):
        return self.flows.get_candidate_title(candidate_id)

    def get_candidate_order(self, candidate_id):
        return self.flows.get_candidate_order(candidate_id)

    def get_candidate_party(self, candidate_id):
        return self.candidates.lookup_id(candidate_id).PartyAb


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
        return self.candidates.lookup_id(candidate_id).PartyAb


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
    if ok and len(rounds) > 0:
        for fname in os.listdir(test_log_dir):
            if test_re.match(fname):
                os.unlink(os.path.join(test_log_dir, fname))
        os.rmdir(test_log_dir)
    return ok


def read_config(config_file):
    with open(config_file) as fd:
        return json.load(fd)


def write_angular_json(config, out_dir):
    json_f = os.path.join(out_dir, 'count.json')
    with open(json_f, 'w') as fd:
        obj = {
            'title': config['title']
        }
        obj['counts'] = [{
            'name': count['name'],
            'description': count['description'],
            'path': count['shortname']}
            for count in config['count']]
        json.dump(obj, fd)


def get_data(method_cls, base_dir, count):
    data_dir = os.path.join(base_dir, count['path'])
    return method_cls(count['state'], data_dir)


def make_automation(answers):
    done = []

    def __auto_fn():
        if len(done) == len(answers):
            return None
        resp = answers[len(done)]
        done.append(resp)
        return resp
    return __auto_fn


def get_outcome(count, count_data, base_dir, out_dir):
    test_logs_okay = True
    test_log_dir = None
    if 'verified' in count:
        test_log_dir = tempfile.mkdtemp(prefix='dividebatur_tmp')
        print("test logs are written to: %s" % (test_log_dir))
    outf = os.path.join(out_dir, count['shortname'] + '.json')
    print("counting %s -> %s" % (count['name'], outf))
    counter = SenateCounter(
        outf,
        count['vacancies'],
        count_data.get_tickets_for_count(),
        count_data.get_parties(),
        count_data.get_candidate_ids(),
        count_data.get_candidate_order,
        count_data.get_candidate_title,
        count_data.get_candidate_party,
        test_log_dir,
        name=count.get('name'),
        description=count.get('description'),
        house=count['house'],
        state=count['state'])
    counter.set_automation_callback(make_automation(count.get('automation', [])))
    counter.run()
    if test_log_dir is not None:
        if not verify_test_logs(os.path.join(base_dir, count['verified']), test_log_dir):
            test_logs_okay = False
    if not test_logs_okay:
        print("** TESTS FAILED **")
        sys.exit(1)


def get_counting_method(method):
    # determine the counting method
    if method == 'AusSenatePre2015':
        return SenateCountPre2015
    elif method == 'AusSenatePost2015':
        return SenateCountPost2015


def main(config_file, out_dir):
    base_dir = os.path.dirname(os.path.abspath(config_file))
    config = read_config(config_file)
    # global config for the angular frontend
    write_angular_json(config, out_dir)
    method_cls = get_counting_method(config['method'])
    if method_cls is None:
        raise Exception("unsupported counting method `%s' requested" % (config['method']))
    for count in config['count']:
        print("reading data for count: `%s'" % (count['name']))
        data = get_data(method_cls, base_dir, count)
        print("determining outcome for count: `%s'" % (count['name']))
        get_outcome(count, data, base_dir, out_dir)


if __name__ == '__main__':
    # really should use the CLI program
    main(*sys.argv[1:])
