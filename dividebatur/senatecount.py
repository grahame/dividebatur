#!/usr/bin/env python3

import argparse
import tempfile
import logging
import difflib
import glob
import json
import sys
import os
import re
from pprint import pformat
from .counter import PapersForCount, SenateCounter
from .aecdata import CandidateList, SenateATL, SenateBTL, FormalPreferences
from .common import logger
from .results import JSONResults


class SenateCountPost2015:
    disable_bulk_exclusions = True

    def __init__(self, state_name, get_input_file, **kwargs):
        self.candidates = CandidateList(state_name,
                                        get_input_file('all-candidates'),
                                        get_input_file('senate-candidates'))
        self.tickets_for_count = PapersForCount()

        self.s282_candidates = kwargs.get('s282_candidates')
        self.s282_method = kwargs.get('s282_method')
        self.max_ballots = kwargs['max_ballots'] if 'max_ballots' in kwargs else None

        self.remove_candidates = None
        self.remove_method = kwargs.get('remove_method')
        remove = kwargs.get('remove_candidates')
        if remove:
            self.remove_candidates = [self.candidates.get_candidate_id(*t) for t in remove]
        if self.remove_candidates:
            self.remove_atl_only = kwargs.get('remove_atl_only')
            if self.remove_atl_only is None:
                self.remove_atl_only = [False for t in self.remove_candidates]

        def atl_flow(form):
            by_pref = {}
            for pref, group in zip(form, self.candidates.groups):
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
                for candidate in the_pref.candidates:
                    candidate_id = candidate.candidate_id
                    prefs.append(candidate_id)
            if not prefs:
                return None
            return prefs

        def btl_flow(form):
            by_pref = {}
            for pref, candidate in zip(form, self.candidates.candidates):
                if pref is None:
                    continue
                if pref not in by_pref:
                    by_pref[pref] = []
                by_pref[pref].append(candidate.candidate_id)
            prefs = []
            for i in range(1, len(form) + 1):
                at_pref = by_pref.get(i)
                if not at_pref or len(at_pref) != 1:
                    break
                candidate_id = at_pref[0]
                prefs.append(candidate_id)
            # must have unique prefs for 1..6, or informal
            if len(prefs) < 6:
                return None
            return prefs

        def resolve_non_s282(atl, btl):
            "resolve the formal form from ATL and BTL forms. BTL takes precedence, if formal"
            return btl_flow(btl) or atl_flow(atl)

        def resolve_s282_restrict_form(atl, btl):
            "resolve the formal form as for resolve_non_s282, but restrict to s282 candidates"
            expanded = btl_flow(btl) or atl_flow(atl)
            restricted = [candidate_id for candidate_id in expanded if candidate_id in self.s282_candidates]
            if len(restricted) == 0:
                return None
            return restricted

        def resolve_remove_candidates(atl, btl, min_candidates):
            "resolve the formal form, removing the listed candidates from eligibiity"
            restricted = None
            btl_expanded = btl_flow(btl)
            if btl_expanded:
                btl_remove = [t for (t, atl_only) in zip(self.remove_candidates, self.remove_atl_only) if not atl_only]
                restricted = [candidate_id for candidate_id in btl_expanded if candidate_id not in btl_remove]
                if min_candidates is not None and len(restricted) < min_candidates:
                    restricted = None
            if restricted is None:
                atl_expanded = atl_flow(atl)
                if atl_expanded:
                    restricted = [candidate_id for candidate_id in atl_expanded if candidate_id not in self.remove_candidates]
                    if len(restricted) == 0:
                        restricted = None
            return restricted

        def resolve_s282_restrict_form_with_savings(atl, btl):
            "resolve the formal form as for resolve_non_s282, but restrict to s282 candidates"
            restricted = None
            # if we were formal BTL in a non-s282 count, restrict the form. if at least one
            # preference, we're formal
            btl_expanded = btl_flow(btl)
            if btl_expanded:
                restricted = [candidate_id for candidate_id in btl_expanded if candidate_id in self.s282_candidates]
                if len(restricted) == 0:
                    restricted = None
            # if, before or after restriction, we are not formal BTL, try restricting the ATL form
            if restricted is None:
                atl_expanded = atl_flow(atl)
                if atl_expanded:
                    restricted = [candidate_id for candidate_id in atl_expanded if candidate_id in self.s282_candidates]
                    if len(restricted) == 0:
                        restricted = None
            return restricted

        atl_n = len(self.candidates.groups)
        btl_n = len(self.candidates.candidates)
        assert(atl_n > 0 and btl_n > 0)
        informal_n = 0
        n_ballots = 0
        resolution_fn = resolve_non_s282
        if self.s282_candidates:
            if self.s282_method == 'restrict_form':
                resolution_fn = resolve_s282_restrict_form
            elif self.s282_method == 'restrict_form_with_savings':
                resolution_fn = resolve_s282_restrict_form_with_savings
            else:
                raise Exception("unknown s282 method: `%s'" % (self.s282_method))
        if self.remove_candidates:
            if self.remove_method == 'relaxed':
                resolution_fn = lambda atl, btl: resolve_remove_candidates(atl, btl, None)
            elif self.remove_method == 'strict':
                resolution_fn = lambda atl, btl: resolve_remove_candidates(atl, btl, 6)
        # the (extremely) busy loop reading preferences and expanding them into
        # forms to be entered into the count
        for raw_form, count in FormalPreferences(get_input_file('formal-preferences')):
            if self.max_ballots and n_ballots >= self.max_ballots:
                break
            atl = raw_form[:atl_n]
            btl = raw_form[atl_n:]
            form = resolution_fn(atl, btl)
            if form is not None:
                self.tickets_for_count.add_ticket(tuple(form), count)
            else:
                informal_n += count
            n_ballots += count
        # slightly paranoid check, but outside the busy loop
        assert(len(raw_form) == atl_n + btl_n)
        if informal_n > 0:
            logger.info("%d ballots are informal and were excluded from the count" % (informal_n))

    def get_papers_for_count(self):
        return self.tickets_for_count

    def get_candidate_ids(self):
        candidate_ids = [c.candidate_id for c in self.candidates.candidates]
        if self.s282_candidates:
            candidate_ids = [t for t in candidate_ids if t in self.s282_candidates]
        if self.remove_candidates:
            strip_candidates = [t for (t, atl_only) in zip(self.remove_candidates, self.remove_atl_only) if not atl_only]
            candidate_ids = [t for t in candidate_ids if t not in strip_candidates]
        return candidate_ids

    def get_parties(self):
        return dict((c.party_abbreviation, c.party_name)
                    for c in self.candidates.candidates)

    def get_candidate_title(self, candidate_id):
        c = self.candidates.candidate_by_id[candidate_id]
        return "{}, {}".format(c.surname, c.given_name)

    def get_candidate_order(self, candidate_id):
        return self.candidates.candidate_by_id[candidate_id].candidate_order

    def get_candidate_party(self, candidate_id):
        return self.candidates.candidate_by_id[candidate_id].party_abbreviation


class SenateCountPre2015:
    disable_bulk_exclusions = False

    def __init__(self, state_name, get_input_file, **kwargs):
        if 's282_recount' in kwargs:
            raise Exception('s282 recount not implemented for pre2015 data')

        self.candidates = CandidateList(state_name,
                                        get_input_file('all-candidates'),
                                        get_input_file('senate-candidates'))
        self.atl = SenateATL(
            state_name,
            get_input_file('group-voting-tickets'),
            get_input_file('first-preferences'))
        self.btl = SenateBTL(get_input_file('btl-preferences'))

        def load_tickets(ticket_obj):
            if ticket_obj is None:
                return
            for form, n in ticket_obj.get_tickets():
                self.tickets_for_count.add_ticket(form, n)
        self.tickets_for_count = PapersForCount()
        load_tickets(self.atl)
        load_tickets(self.btl)

    def get_papers_for_count(self):
        return self.tickets_for_count

    def get_candidate_ids(self):
        return [c.candidate_id for c in self.candidates.candidates]

    def get_parties(self):
        return dict((c.party_abbreviation, c.party_name)
                    for c in self.candidates.candidates)

    def get_candidate_title(self, candidate_id):
        c = self.candidates.candidate_by_id[candidate_id]
        return "{}, {}".format(c.surname, c.given_name)

    def get_candidate_order(self, candidate_id):
        return self.candidates.candidate_by_id[candidate_id].candidate_order

    def get_candidate_party(self, candidate_id):
        return self.candidates.candidate_by_id[candidate_id].party_abbreviation


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
        try:
            with open(fname(d, r)) as fd:
                return json.load(fd)
        except FileNotFoundError:
            return {}
    ok = True
    for idx in sorted(rounds):
        v = getlog(verified_dir, idx)
        t = getlog(test_log_dir, idx)
        if v != t:
            logger.error("Round %d: FAIL" % (idx))
            logger.error("Log should be:")
            logger.error(pformat(v))
            logger.error("Log is:")
            logger.error(pformat(t))
            logger.error("Diff:")
            logger.error(
                '\n'.join(
                    difflib.unified_diff(
                        pformat(v).split('\n'),
                        pformat(t).split('\n'))))
            ok = False
        else:
            logger.debug("Round %d: OK" % (idx))
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
        logger.debug("cleanup: removing `%s'" % (fname))
        os.unlink(fname)


def write_angular_json(config, out_dir):
    json_f = os.path.join(out_dir, 'count.json')
    with open(json_f, 'w') as fd:
        obj = {
            'title': config['title']
        }
        obj['counts'] = [{
            'name': count['name'],
            'state': count['state'],
            'description': count['description'],
            'path': count['shortname']}
            for count in config['count']]
        json.dump(obj, fd, sort_keys=True, indent=4, separators=(',', ': '))


def get_data(input_cls, base_dir, count, **kwargs):
    aec_data = count['aec-data']

    def input_file(name):
        return os.path.join(base_dir, aec_data[name])
    return input_cls(count['state'], input_file, **kwargs)


class AutomationException(Exception):
    pass


class Automation:
    def __init__(self, name, automation_data, count_data):
        """
        name: name of this automation instance, for logging
        automation_data: list of questions and responses [ [ question, response ], ... ]
        """
        self._name = name
        self._data = automation_data
        self._count_data = count_data
        self._upto = 0

    def _qstr(self, question):
        "we need to cope with a list, or a list of lists"
        parts = []
        for entry in question:
            if type(entry) is list:
                parts.append(self._qstr(entry))
            else:
                parts.append('"%s"<%d>' % (self._count_data.get_candidate_title(entry), entry))
        return ', '.join(parts)

    def create_callback(self):
        """
        create a callback, suitable to be passed to SenateCounter
        """
        def __callback(question_posed):
            logger.debug("%s: asked to choose between: %s" % (self._name, self._qstr(question_posed)))
            if self._upto == self._data:
                logger.error("%s: out of automation data, requested to pick between %s" % (self._name, self._qstr(question_posed)))
                raise AutomationException("out of automation data")
            question_archived, answer = self._data[self._upto]
            if question_archived != question_posed:
                logger.error("%s: automation data mismatch, expected question `%s', got question `%s'" % (self._name, self._qstr(question_archived), self._qstr(question_posed)))
            resp = question_posed.index(answer)
            self._upto += 1
            return resp
        return __callback

    def check_complete(self):
        if self._upto != len(self._data):
            logger.error("%s: not all automation data was consumed (upto %d/%d)" % (self._name, self._upto, len(self._data)))
            return False
        return True


def json_count_path(out_dir, shortname):
    return os.path.join(out_dir, shortname + '.json')


def get_outcome(count, count_data, base_dir, out_dir):
    test_logs_okay = True
    test_log_dir = None
    if 'verified' in count:
        test_log_dir = tempfile.mkdtemp(prefix='dividebatur_tmp')
        logger.debug("test logs are written to: %s" % (test_log_dir))
    outf = json_count_path(out_dir, count['shortname'])
    logger.info("counting `%s'. output written to `%s'" % (count['name'], outf))
    result_writer = JSONResults(
        outf,
        test_log_dir,
        count_data.get_candidate_ids(),
        count_data.get_parties(),
        count_data.get_candidate_order,
        count_data.get_candidate_title,
        count_data.get_candidate_party,
        name=count.get('name'),
        description=count.get('description'),
        house=count['house'],
        state=count['state'])
    disable_bulk_exclusions = count.get('disable_bulk_exclusions', count_data.disable_bulk_exclusions)
    logger.debug("disable bulk exclusions: %s" % (disable_bulk_exclusions))
    election_order_auto = Automation('election order', count['election_order_ties'], count_data)
    exclusion_tie_auto = Automation('exclusion tie', count['exclusion_ties'], count_data)
    election_tie_auto = Automation('election tie', count['election_ties'], count_data)
    counter = SenateCounter(
        result_writer,
        count['vacancies'],
        count_data.get_papers_for_count(),
        election_order_auto.create_callback(),
        exclusion_tie_auto.create_callback(),
        election_tie_auto.create_callback(),
        count_data.get_candidate_ids(),
        count_data.get_candidate_order,
        disable_bulk_exclusions)
    counter.run()
    if any(not t.check_complete() for t in (election_order_auto, exclusion_tie_auto, election_tie_auto)):
        logger.error("** Not all automation data consumed. Failed. **")
        sys.exit(1)
    if test_log_dir is not None:
        if not verify_test_logs(os.path.join(base_dir, count['verified']), test_log_dir):
            test_logs_okay = False
    if not test_logs_okay:
        logger.error("** TESTS FAILED **")
        sys.exit(1)
    return (outf, result_writer.summary())


def get_input_method(format):
    # determine the counting method
    if format == 'AusSenatePre2015':
        return SenateCountPre2015
    elif format == 'AusSenatePost2015':
        return SenateCountPost2015


def check_counting_method_valid(method_cls, data_format):
    if method_cls is None:
        raise Exception("unsupported AEC data format '%s' requested" % (data_format))


def s282_options(out_dir, count, written):
    options = {}
    s282_config = count.get('s282')
    if not s282_config:
        return options
    options = {
        's282_method': s282_config['method']
    }
    shortname = s282_config['recount_from']
    if not shortname:
        return options
    fname = json_count_path(out_dir, shortname)
    if fname not in written:
        logger.error("error: `%s' needed for s282 recount has not been calculated during this dividebatur run." % (fname))
        sys.exit(1)
    with open(fname) as fd:
        data = json.load(fd)
    options['s282_candidates'] = [t['id'] for t in data['summary']['elected']]
    return options


def remove_candidates_options(count):
    options = {}
    remove = count.get('remove')
    if remove is None:
        return options
    options['remove_candidates'] = remove['candidates']
    options['remove_method'] = remove['method']
    options['remove_atl_only'] = remove.get('atl_only')
    return options


def check_config(config):
    "basic checks that the configuration file is valid"
    shortnames = [count['shortname'] for count in config['count']]
    if len(shortnames) != len(set(shortnames)):
        logger.error("error: duplicate `shortname' in count configuration.")
        return False
    return True


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-q', '--quiet',
        action='store_true', help="Disable informational output")
    parser.add_argument(
        '-v', '--verbose',
        action='store_true', help="Enable debug output")
    parser.add_argument(
        '--max-ballots',
        type=int, help="Maximum number of ballots to read")
    parser.add_argument(
        '--only',
        type=str, help="Only run the count with this shortname")
    parser.add_argument(
        '--only-verified',
        action='store_true', help="Only run verified counts")
    parser.add_argument(
        'config_file',
        type=str,
        help='JSON config file for counts')
    parser.add_argument(
        'out_dir',
        type=str,
        help='Output directory')
    return parser.parse_args()


def execute_counts(out_dir, config_file, only, only_verified, max_ballots=None):
    base_dir = os.path.dirname(os.path.abspath(config_file))
    config = read_config(config_file)
    if not check_config(config):
        return

    # global config for the angular frontend
    cleanup_json(out_dir)
    write_angular_json(config, out_dir)
    written = set()
    for count in config['count']:
        if only is not None and count['shortname'] != only:
            continue
        if only_verified and 'verified' not in count:
            continue
        aec_data_config = count['aec-data']
        data_format = aec_data_config['format']
        input_cls = get_input_method(data_format)
        check_counting_method_valid(input_cls, data_format)
        count_options = {}
        count_options.update(s282_options(out_dir, count, written))
        count_options.update(remove_candidates_options(count))
        if max_ballots is not None:
            count_options.update({'max_ballots': max_ballots})
        logger.debug("reading data for count: `%s'" % (count['name']))
        data = get_data(input_cls, base_dir, count, **count_options)
        logger.debug("determining outcome for count: `%s'" % (count['name']))
        outf, _ = get_outcome(count, data, base_dir, out_dir)
        written.add(outf)


def main():
    args = parse_args()
    if args.quiet:
        logger.setLevel(logging.ERROR)
    elif args.verbose:
        logger.setLevel(logging.DEBUG)
    execute_counts(args.out_dir, args.config_file, args.only, args.only_verified, max_ballots=args.max_ballots)


if __name__ == '__main__':
    main()
