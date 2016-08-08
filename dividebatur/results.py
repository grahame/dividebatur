"""
This module tracks the result of a count, and provides a base class to be
implemented and used by callers of for reporting or analysis

The exposed class, BaseResults, is an abstract base class.
Your implementation should inherit from BaseResults.
"""

import datetime
import json
import abc
import os

from .common import logger


class ExclusionDistributionPerformed:
    """
    Information on any exclusion distribution which is performed during a
    counting round.
    """

    def __init__(self, candidates, transfer_value):
        """
        candidates: a List of candidate_ids
        transfer_value: transfer value, as a Fraction
        """
        self.candidates = candidates
        self.transfer_value = transfer_value


class ElectionDistributionPerformed:
    """
    Information on any election distribution which is performed during a
    counting round.
    """

    def __init__(self, candidate_id, transfer_value):
        """
        transfer_value is a Fraction instance
        """
        self.candidate_id = candidate_id
        self.transfer_value = transfer_value


class CandidateElected:
    """
    Information on the election of a candidate.
    """

    def __init__(self, candidate_id, order, excess_votes, paper_count, transfer_value):
        """
        candidate_id: the candidate elected
        order: the number of the spot the candidate was elected to [1..N_vacancies]
        excess_votes: the number of excess votes the candidate received
        paper_count: the number of papers the candidate held at time of elect
        transfer_value: the transfer value for the excess papers (0 if no excess papers)
        """

        self.candidate_id = candidate_id
        self.order = order
        self.excess_votes = excess_votes
        self.paper_count = paper_count
        self.transfer_value = transfer_value


class CandidatesExcluded:
    """
    Information on the exclusion of one or more candidates.
    """

    def __init__(self, candidates, transfer_values, reason):
        """
        candidates: list of candidate_ids of those candidates elected
        transfer_values: the transfer values of papers to be distributed (a list of Fraction instances)
        reason: an instance of ExclusionReason
        """
        self.candidates = candidates
        self.transfer_values = transfer_values
        self.reason = reason


class ExclusionReason:
    """
    information of interest about an exclusion of one or more
    candidates.

    simply to make this information available to users of this
    counter, this data is not used to make any decisions which
    affect count results.
    """
    def __init__(self, reason, info):
        """
        reason: a string identifying the reason
        info: additional information
        """
        self.reason, self.info = reason, info


class ActProvision:
    """
    Note that a provision of the Act has been used.
    """

    def __init__(self, text):
        """
        text: textual description of the provision used.
        """

        self.text = text


class BaseResults(metaclass=abc.ABCMeta):
    """
    Base class, with callback hooks for each event type which may occur.

    Each callback represents an event as the senate election progresses.
    The concrete implementation is responsible for tracking events.
    """

    @abc.abstractmethod
    def round_begin(self, round_number):
        """
        Called by the counter at the commencement of a counting round.
        """
        pass

    @abc.abstractmethod
    def round_complete(self):
        """
        Called by the counter at the conclusion of a counting round.
        """
        self.round_info = None

    @abc.abstractmethod
    def exclusion_distribution_performed(self, obj):
        """
        Called by the counter any time a distribution of papers is performed.
        ``obj`` is an instance of ExclusionDistributionPerformed.
        """
        pass

    @abc.abstractmethod
    def election_distribution_performed(self, obj):
        """
        Called by the counter any time a distribution of papers is performed.
        ``obj`` is an instance of ElectionDistributionPerformed.
        """
        pass

    @abc.abstractmethod
    def candidate_aggregates(self, obj):
        """
        Called by the counter after all papers have been distributed for the
        round. ``obj`` is an instance of CandidateAggregates.
        """
        pass

    @abc.abstractmethod
    def candidate_elected(self, obj):
        """
        Called by the counter when a candidate is elected.
        ``obj`` is an instance of CandidateElected.
        """
        pass

    @abc.abstractmethod
    def candidates_excluded(self, obj):
        """
        Called by the counter when candidate(s) are excluded.
        ``obj`` is an instance of CandidatesExcluded
        """
        pass

    @abc.abstractmethod
    def provision_used(self, obj):
        """
        Called by the counter when a provision of the act
        is used - for example, to resolve a tie, or to
        terminate the count.
        ``obj``: an instance of ProvisionUsed
        ``total_papers``: the total number of formal papers
        ``quota``: the quota to be elected
        """
        pass

    @abc.abstractmethod
    def started(self, vacancies, total_papers, quota):
        """
        Called by the counter when the election count begins.
        vacancies: the number of vacancies to be filled.
        """
        pass

    @abc.abstractmethod
    def finished(self):
        """
        Called by the counter when the election count has finished.
        """
        pass


class JSONResults(BaseResults):
    def __init__(self, filename, test_log_dir, candidate_ids, parties, candidate_order_fn, get_candidate_title, get_candidate_party, **kwargs):
        self.filename = filename
        self.test_log_dir = test_log_dir
        self.candidate_ids = candidate_ids
        self.parties = parties
        self.candidate_order_fn = candidate_order_fn
        self.get_candidate_title = get_candidate_title
        self.get_candidate_party = get_candidate_party
        self.template_variables = kwargs

        self.aggregates = []
        self.vacancies = None
        self.candidates_affected_by_round = None
        self.rounds = []
        self._number_excluded = 0
        self._start_time = datetime.datetime.now()
        # track events by candidate_id
        self._candidates_elected = {}
        self._candidates_excluded = {}

    def started(self, vacancies, total_papers, quota):
        self.vacancies = vacancies
        self.total_papers = total_papers
        self.quota = quota

    def round_begin(self, round_number):
        self.current_round = round_number
        self.candidates_affected_by_round = set()
        self.round_info = {
            'number': round_number,
            'note': '',
            'elected': [],
            'exclusion': None,
            'distribution': None
        }

    def election_distribution_performed(self, obj):
        self.candidates_affected_by_round.add(obj.candidate_id)
        self.round_info['distribution'] = {
            'type': 'election',
            'distributed_candidates': [obj.candidate_id],
            'transfer_value': float(obj.transfer_value)
        }

    def exclusion_distribution_performed(self, obj):
        for candidate_id in obj.candidates:
            self.candidates_affected_by_round.add(candidate_id)
        self.round_info['distribution'] = {
            'type': 'exclusion',
            'distributed_candidates': [obj.candidates],
            'transfer_value': float(obj.transfer_value)
        }

    def candidate_aggregates(self, obj):
        self.aggregates.append(obj)
        self.json_log(obj)

    def candidate_elected(self, obj):
        self._candidates_elected[obj.candidate_id] = (self.current_round, obj)
        self.candidates_affected_by_round.add(obj.candidate_id)
        info = {
            'id': obj.candidate_id,
            'pos': obj.order,
        }
        if obj.excess_votes is not None and obj.paper_count is not None:
            info['transfer'] = {
                'excess': obj.excess_votes,
                'paper_count': obj.paper_count,
                'value': float(obj.transfer_value)
            }
        self.round_info['elected'].append(info)

    def candidates_excluded(self, obj):
        for candidate_id in obj.candidates:
            self._number_excluded += 1
            self._candidates_excluded[candidate_id] = (self.current_round, self._number_excluded, obj)
            self.candidates_affected_by_round.add(candidate_id)
        info = {
            'candidates': obj.candidates,
            'reason': obj.reason.reason,
            'transfers': [float(t) for t in obj.transfer_values],
        }
        info.update(obj.reason.info)
        self.round_info['exclusion'] = info

    def provision_used(self, obj):
        self.round_info['note'] += obj.text

    def candidate_ids_display(self, candidate_aggregates):
        return sorted(self.candidate_ids, key=self.candidate_order_fn)

    def candidate_election_order(self, candidate_id):
        if candidate_id not in self._candidates_elected:
            return self.vacancies + 1
        _, obj = self._candidates_elected[candidate_id]
        return obj.order

    def round_count(self):
        def exloss(a):
            return {
                'exhausted_papers': a.get_exhausted_papers(),
                'exhausted_votes': a.get_exhausted_votes(),
                'gain_loss_papers': a.get_gain_loss_papers(),
                'gain_loss_votes': a.get_gain_loss_votes(),
            }

        def agg(a):
            return {
                'votes': a.get_vote_count(candidate_id),
                'papers': a.get_paper_count(candidate_id)
            }

        last_candidate_aggregates = None
        if len(self.aggregates) > 1:
            last_candidate_aggregates = self.aggregates[-2]
        candidate_aggregates = None
        if len(self.aggregates) > 0:
            candidate_aggregates = self.aggregates[-1]

        r = {
            'candidates': [],
            'after': exloss(candidate_aggregates)
        }

        if last_candidate_aggregates is not None:
            before = exloss(last_candidate_aggregates)
            r['delta'] = dict((t, r['after'][t] - before[t]) for t in before)

        for candidate_id in reversed(sorted(
                self.candidate_ids,
                key=lambda x: (candidate_aggregates.get_vote_count(x), self.vacancies - self.candidate_election_order(x)))):
            entry = {
                'id': candidate_id,
                'after': agg(candidate_aggregates),
            }
            if candidate_id in self._candidates_elected:
                _, obj = self._candidates_elected[candidate_id]
                entry['elected'] = obj.order
            if candidate_id in self._candidates_excluded:
                _, entry['excluded'], _ = self._candidates_excluded[candidate_id]
            done = False
            if entry.get('excluded'):
                if candidate_id not in self.candidates_affected_by_round and \
                        not candidate_aggregates.get_candidate_has_papers(candidate_id):
                    done = True
            if last_candidate_aggregates is not None:
                before = agg(last_candidate_aggregates)
                entry['delta'] = dict((t, entry['after'][t] - before[t]) for t in before)
            if not done:
                r['candidates'].append(entry)
        r['total'] = {
            'papers': sum(t['after']['papers'] for t in r['candidates']) + r['after']['exhausted_papers'] + r['after']['gain_loss_papers'],
            'votes': sum(t['after']['votes'] for t in r['candidates']) + r['after']['exhausted_votes'] + r['after']['gain_loss_votes'],
        }
        return r

    def round_complete(self):
        self.round_info['count'] = self.round_count()
        self.rounds.append(self.round_info)

    def finished(self):
        self._end_time = datetime.datetime.now()
        self.write_json()

    def summary(self):
        r = {
            'elected': [],
            'excluded': []
        }

        def in_order(l):
            return enumerate(sorted(l, key=lambda k: l[k]['order']))

        def elected_json(candidate_id):
            round_number, obj = self._candidates_elected[candidate_id]
            r = {
                'id': candidate_id,
                'round': round_number,
                'order': obj.order,
                'excess_votes': obj.excess_votes,
                'paper_count': obj.paper_count,
                'transfer_value': float(obj.transfer_value)
            }
            return r

        def excluded_json(candidate_id):
            round_number, order, obj = self._candidates_excluded[candidate_id]
            r = {
                'id': candidate_id,
                'round': round_number,
                'order': order,
                'transfer_values': [float(t) for t in obj.transfer_values],
                'reason': obj.reason.reason
            }
            r.update(obj.reason.info)
            return r

        for candidate_id in sorted(self._candidates_elected, key=lambda x: self._candidates_elected[x][1].order):
            r['elected'].append(elected_json(candidate_id))
        for candidate_id in sorted(self._candidates_excluded, key=lambda x: self._candidates_excluded[x][1]):
            r['excluded'].append(excluded_json(candidate_id))
        return r

    def party_json(self):
        return dict((party, {
            'name': self.parties[party],
        }) for party in self.parties)

    def candidate_json(self):
        return dict((candidate_id, {
            'title': self.get_candidate_title(candidate_id),
            'party': self.get_candidate_party(candidate_id),
            'id': candidate_id
        }) for candidate_id in self.candidate_ids)

    def json_log(self, candidate_aggregates):
        if self.test_log_dir is None:
            return
        log = []
        for candidate_id in self.candidate_ids_display(candidate_aggregates):
            log.append((self.get_candidate_title(candidate_id), candidate_aggregates.get_vote_count(candidate_id)))
        with open(os.path.join(self.test_log_dir, 'round_%d.json' % (self.current_round)), 'w') as fd:
            json.dump(log, fd)

    def write_json(self):
        params = {
            'total_papers': self.total_papers,
            'quota': self.quota,
            'vacancies': self.vacancies,
            'started': self._start_time.strftime("%Y-%m-%d %H:%M"),
            'finished': self._end_time.strftime("%Y-%m-%d %H:%M")
        }
        params.update(self.template_variables)
        obj = {
            'candidates': self.candidate_json(),
            'parties': self.party_json(),
            'parameters': params,
            'rounds': self.rounds,
            'summary': self.summary(),
        }
        with open(self.filename, 'w') as fd:
            try:
                json.dump(obj, fd)
            except TypeError:
                logger.error("failed to serialise data")
                logger.error("%s" % (repr(obj)))
                raise
