#!/usr/bin/env python3

import sys
import os
import json
import tempfile
import difflib
import re
import glob
from pprint import pprint, pformat
from .counter import PapersForCount, SenateCounter, Ticket
from .aecdata import Candidates, SenateATL, SenateBTL, AllCandidates, SenateFlows, FormalPreferences


class SenateCountPost2015:
    def __init__(self, state_name, get_input_file, **kwargs):
        self.candidates = Candidates(get_input_file('senate-candidates'))
        self.all_candidates = AllCandidates(get_input_file('all-candidates'), state_name)
        self.flows = SenateFlows(self.candidates, self.all_candidates)
        self.tickets_for_count = PapersForCount()

        self.s282_candidates = kwargs.get('s282_candidates')

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
                    # s282: exclude candidates not elected in first (full senate) count
                    if self.s282_candidates and candidate_id not in self.s282_candidates:
                        continue
                    prefs.append((len(prefs) + 1, candidate_id))
            if not prefs:
                return None
            return Ticket(tuple(prefs))

        def btl_flow(form):
            if self.s282_candidates:
                # s282: only 273(7) to (30) apply, so don't exclude informal BTL votes
                min_prefs = 1
            else:
                min_prefs = 6
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
                    break
                candidate_id = at_pref[0]
                # s282: exclude candidates not elected in first (full senate) count
                if self.s282_candidates and candidate_id not in self.s282_candidates:
                    continue
                prefs.append((len(prefs) + 1, candidate_id))
            # must have unique prefs for 1..6, or informal
            if len(prefs) < min_prefs:
                return None
            return Ticket(tuple(prefs))

        atl_n = len(self.flows.groups)
        btl_n = len(self.flows.btl)
        informal_n = 0
        for pref in FormalPreferences(get_input_file('formal-preferences')):
            raw_form = pref.Preferences
            assert(len(raw_form) == atl_n + btl_n)
            # BTL takes precedence
            atl = raw_form[:atl_n]
            btl = raw_form[atl_n:]
            form = btl_flow(btl) or atl_flow(atl)
            if form:
                self.tickets_for_count.add_ticket(form, 1)
            else:
                informal_n += 1
        print("note: %d ballots informal and excluded from the count" % informal_n)

    def get_tickets_for_count(self):
        return self.tickets_for_count

    def get_candidate_ids(self):
        if not self.s282_candidates:
            return self.flows.get_candidate_ids()
        return [t for t in self.flows.get_candidate_ids() if t in self.s282_candidates]

    def get_parties(self):
        return self.candidates.get_parties()

    def get_candidate_title(self, candidate_id):
        return self.flows.get_candidate_title(candidate_id)

    def get_candidate_order(self, candidate_id):
        return self.flows.get_candidate_order(candidate_id)

    def get_candidate_party(self, candidate_id):
        return self.candidates.lookup_id(candidate_id).PartyAb


class SenateCountPre2015:
    def __init__(self, state_name, get_input_file, **kwargs):
        if 's282_recount' in kwargs:
            raise Exception('s282 recount not implemented for pre2015 data')

        self.candidates = Candidates(get_input_file('senate-candidates'))
        self.atl = SenateATL(
            state_name,
            self.candidates,
            get_input_file('group-voting-tickets'),
            get_input_file('first-preferences'))
        self.btl = SenateBTL(self.candidates, get_input_file('btl-preferences'))

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


def cleanup_json(out_dir):
    for fname in glob.glob(out_dir + '/*.json'):
        print("cleanup: removing `%s'" % (fname))
        os.unlink(fname)


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


def get_data(input_cls, base_dir, count, **kwargs):
    aec_data = count['aec-data']

    def input_file(name):
        return os.path.join(base_dir, aec_data[name])
    return input_cls(count['state'], input_file, **kwargs)


def make_automation(answers):
    done = []

    def __auto_fn():
        if len(done) == len(answers):
            return None
        resp = answers[len(done)]
        done.append(resp)
        return resp
    return __auto_fn


def json_count_path(out_dir, shortname):
    return os.path.join(out_dir, shortname + '.json')


def get_outcome(count, count_data, base_dir, out_dir):
    test_logs_okay = True
    test_log_dir = None
    if 'verified' in count:
        test_log_dir = tempfile.mkdtemp(prefix='dividebatur_tmp')
        print("test logs are written to: %s" % (test_log_dir))
    outf = json_count_path(out_dir, count['shortname'])
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
        count.get('disable_bulk_exclusions'),
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
    return outf


def get_input_method(format):
    # determine the counting method
    if format == 'AusSenatePre2015':
        return SenateCountPre2015
    elif format == 'AusSenatePost2015':
        return SenateCountPost2015


def s282_recount_get_candidates(out_dir, count, written):
    shortname = count.get('s282_recount')
    if not shortname:
        return
    fname = json_count_path(out_dir, shortname)
    if fname not in written:
        print("error: `%s' needed for s282 recount was not calculated yet." % (fname))
        sys.exit(1)
    with open(fname) as fd:
        data = json.load(fd)
        elected = [t['id'] for t in data['summary']['elected']]
        return elected


def main(config_file, out_dir):
    base_dir = os.path.dirname(os.path.abspath(config_file))
    config = read_config(config_file)
    # global config for the angular frontend
    cleanup_json(out_dir)
    write_angular_json(config, out_dir)
    written = set()
    for count in config['count']:
        aec_data_config = count['aec-data']
        input_cls = get_input_method(aec_data_config['format'])
        if input_cls is None:
            raise Exception("unsupported AEC data format '%s' requested" % (config['method']))
        s282_candidates = s282_recount_get_candidates(out_dir, count, written)
        print("reading data for count: `%s'" % (count['name']))
        data = get_data(input_cls, base_dir, count, s282_candidates=s282_candidates)
        print("determining outcome for count: `%s'" % (count['name']))
        outf = get_outcome(count, data, base_dir, out_dir)
        written.add(outf)


if __name__ == '__main__':
    # really should use the CLI program
    main(*sys.argv[1:])
