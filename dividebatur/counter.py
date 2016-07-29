import itertools
import json
import fractions
import os
from .output import JsonOutput, RoundLog, LogEntry


class PreferenceFlow:
    """
    a preference flow; describes a preference flow and maintains state for it
    during the count
    """

    def __init__(self, preferences):
        "preferences is a list, [(PreferenceNo, CandidateId), ...]"
        self.preferences = tuple(sorted(preferences, key=lambda x: x[1]))
        self.transfer_value = fractions.Fraction(1, 1)
        self.transfers = []
        self.up_to_preference = 1

    def __eq__(self, other):
        return other.preferences == self.preferences

    def __hash__(self):
        return hash(self.preferences)

    def next_preference(self):
        self.up_to_preference += 1

    def get_preference(self):
        "note that if there are multiple preferences for the current pref, returns None (exhausts)"
        matches = []
        for pref, candidate in self.preferences:
            if pref == self.up_to_preference:
                matches.append(candidate)
        if len(matches) == 1:
            return matches[0]

    def __repr__(self):
        return "<PreferenceFlow>"


class Ticket:
    """
    represents the form of a ballot. note that prior to 2015, it was
    possible for a ballot to have more than one preference flow, in
    the case of "split tickets". This only ever occurred above-the-line;
    A party could lodge more than one Group Voting Ticket, which then applied
    to the ballots cast above the line for that Group.

    This class is hashable, so that PapersForCount can sum up equivalent papers
    (to reduce memory use, and speed up the count.)
    """

    def __init__(self, preference_flows):
        self.preference_flows = preference_flows
        assert(isinstance(preference_flows, tuple))
        for preference_flow in self.preference_flows:
            assert(isinstance(preference_flow, PreferenceFlow))

    def __eq__(self, other):
        return self.preference_flows == other.preference_flows

    def __hash__(self):
        return hash(self.preference_flows)

    def __iter__(self):
        return iter(self.preference_flows)

    def __len__(self):
        return len(self.preference_flows)

    def __repr__(self):
        return "<Ticket>"


class PapersForCount:
    """
    defines the inital state of the count; eg. the tickets and the number of papers with that ticket
    """

    def __init__(self):
        self.papers = {}

    def add_ticket(self, ticket, n):
        assert(isinstance(ticket, Ticket))
        if ticket not in self.papers:
            self.papers[ticket] = 0
        self.papers[ticket] += n

    def __iter__(self):
        return iter(self.papers.items())


class PaperBundle:
    """
    a bundle is a collection of papers, all with the same ticket, and with a transfer value they
    were distributed under
    """

    def __init__(self, ticket, size, transfer_value):
        self.ticket, self.size, self.transfer_value = ticket, size, transfer_value

    def get_size(self):
        return self.size

    def get_ticket(self):
        return self.ticket

    def get_transfer_value(self):
        return self.transfer_value


class BundleTransaction:
    """
    a group of bundles which have been transferred to a candidate
    this is stored because we may need to know the number of votes
    contained within the bundle transfer if we later remove it
    """

    def __init__(self, bundles):
        assert(len(bundles) > 0)
        self.bundles = bundles
        self.transfer_value = None
        # it's impossible for a transfer to occur with bundles at different
        # transfer values; so we can do a little cross-check here
        for bundle in self.bundles:
            if self.transfer_value is None:
                self.transfer_value = bundle.get_transfer_value()
            else:
                assert(self.transfer_value == bundle.get_transfer_value())
        self.votes_fraction = 0
        for bundle in self.bundles:
            self.votes_fraction += bundle.get_size() * self.transfer_value
        self.votes = int(self.votes_fraction)

    def get_transfer_value(self):
        return self.transfer_value

    def get_votes(self):
        return self.votes

    def get_votes_fraction(self):
        return self.votes_fraction

    def get_papers(self):
        return sum(bundle.get_size() for bundle in self.bundles)

    def __iter__(self):
        return iter(self.bundles)


class CandidateBundleTransactions:
    """
    describes which bundles a particular candidate is holding throughout the count
    """

    def __init__(self, candidate_ids, papers_for_count):
        """
        build initial bundles by first preference, and distribute
        """
        self.candidate_bundle_transactions = {}
        # create an entry for every candidate (even if they don't hold any papers)
        for candidate_id in candidate_ids:
            self.candidate_bundle_transactions[candidate_id] = []
        # go through each ticket and count in the papers and assign by first preference
        # handle split first preference
        bundles_to_candidate = {}
        for ticket, count in papers_for_count:
            # first preferences, by flow
            prefs = {}
            for preference_flow in ticket:
                preference = preference_flow.get_preference()
                if preference not in prefs:
                    prefs[preference] = []
                prefs[preference].append(preference_flow)
            for pref in prefs:
                if pref is None:
                    continue
                preference_flows = prefs[pref]
                mult = fractions.Fraction(len(preference_flows), len(ticket))
                pref_count = int(mult * count)
                if pref not in bundles_to_candidate:
                    bundles_to_candidate[pref] = []
                bundles_to_candidate[pref].append(PaperBundle(Ticket(tuple(preference_flows)), pref_count, fractions.Fraction(1, 1)))
        for candidate_id in bundles_to_candidate:
            self.candidate_bundle_transactions[candidate_id].append(BundleTransaction(bundles_to_candidate[candidate_id]))

    def paper_count(self, candidate_id):
        """
        returns the number of papers held by the candidate
        """
        papers = 0
        for bundle_transaction in self.candidate_bundle_transactions[candidate_id]:
            for bundle in bundle_transaction:
                papers += bundle.get_size()
        return papers

    def candidate_paper_count(self):
        return dict((candidate_id, self.paper_count(candidate_id)) for candidate_id in self.candidate_bundle_transactions)

    def get(self, candidate_id):
        return self.candidate_bundle_transactions[candidate_id].copy()

    def transfer_to(self, candidate_id, bundle):
        self.candidate_bundle_transactions[candidate_id].append(bundle)

    def transfer_from(self, candidate_id, bundle):
        self.candidate_bundle_transactions[candidate_id].remove(bundle)


class CandidateAggregates:
    """
    stores the number of votes, and the number of papers, held by each candidate at the end of a round
    the number of exhausted papers/votes and the number of votes gained/lost by fraction is also stored
    """

    def __init__(self, original_paper_count, candidate_votes, candidate_papers, exhausted_votes, exhausted_papers):
        self.candidate_votes = candidate_votes
        self.candidate_papers = candidate_papers
        self.exhausted_votes = exhausted_votes
        self.exhausted_papers = exhausted_papers
        self.gain_loss_votes = original_paper_count - sum(candidate_votes.values()) - self.exhausted_votes
        self.gain_loss_papers = original_paper_count - sum(candidate_papers.values()) - self.exhausted_papers

    def get_candidate_votes(self):
        return self.candidate_votes.copy()

    def get_paper_count(self, candidate_id):
        return self.candidate_papers[candidate_id]

    def get_vote_count(self, candidate_id):
        return self.candidate_votes[candidate_id]

    def candidate_votes_iter(self):
        return iter(self.candidate_votes.items())

    def get_exhausted_papers(self):
        return self.exhausted_papers

    def get_exhausted_votes(self):
        return self.exhausted_votes

    def get_gain_loss_papers(self):
        return self.gain_loss_papers

    def get_gain_loss_votes(self):
        return self.gain_loss_votes


class SenateCounter:
    def __init__(self, fname, vacancies, papers_for_count, parties, candidate_ids, candidate_order, candidate_title, candidate_party, test_log_dir, **kwargs):
        self.output = JsonOutput(fname)
        self.vacancies, self.papers_for_count, self.parties, self.candidate_ids, self.candidate_order, self.candidate_title, self.candidate_party = \
            vacancies, papers_for_count, parties, candidate_ids, candidate_order, candidate_title, candidate_party
        self.test_log_dir = test_log_dir
        self.next_automated = 0
        self.template_vars = kwargs
        # senators elected; candidates excluded from the count; neither of these are
        # eligible to have papers distributed to them
        self.candidates_elected = {}
        self.candidates_excluded = {}
        # we maintain queues of distributions pending; for exclusions and elections. all exclusions
        # must be processed before any elections are processed, even if a part-completed distribution
        # leads to an election
        self.exclusion_distributions_pending = []
        self.election_distributions_pending = []
        self.has_run = False
        self.set_automation_callback(None)

    def set_automation_callback(self, cb):
        self.automation_callback = cb

    def run(self):
        assert(self.has_run is False)
        self.has_run = True
        # determine quota
        self.determine_quota()
        # initial assignment of tickets
        self.candidate_bundle_transactions = CandidateBundleTransactions(self.candidate_ids, self.papers_for_count)
        # execute the count
        self.count()
        # log who got elected/excluded
        self.output.set_summary(self.summary())
        # render to HTML
        self.output.render(self, self.template_vars)

    def party_json(self):
        return dict((party, {
            'name': self.parties[party],
        }) for party in self.parties)

    def candidate_json(self):
        return dict((candidate_id, {
            'title': self.candidate_title(candidate_id),
            'party': self.candidate_party(candidate_id),
            'id': candidate_id
        }) for candidate_id in self.candidate_ids)

    def input_or_automated(self, entry, qn):
        resp = None
        if self.automation_callback is not None:
            resp = self.automation_callback()
        if resp is not None:
            entry.log("%s\nautomation: '%s' entered" % (qn, resp), echo=True)
            return resp
        else:
            entry.log(qn, echo=True, end='')
            return input()

    def determine_quota(self):
        self.total_papers = sum(count for _, count in self.papers_for_count)
        self.quota = int(self.total_papers / (self.vacancies + 1)) + 1

    def set_candidate_order(self, fn):
        self.candidate_order = fn

    def set_candidate_title(self, fn):
        self.candidate_title = fn

    def elected_candidates_in_order(self, round_log, candidate_votes):
        """
        determine all candidates with at least a quota of votes in `candidate_votes'. returns results in
        order of decreasing vote count
        """
        eligible_by_vote = {}
        for candidate_id, votes in candidate_votes.candidate_votes_iter():
            if candidate_id in self.candidates_elected:
                continue
            if votes < self.quota:
                continue
            if votes not in eligible_by_vote:
                eligible_by_vote[votes] = []
            eligible_by_vote[votes].append(candidate_id)

        elected = []
        for votes in reversed(sorted(eligible_by_vote)):
            candidate_ids = eligible_by_vote[votes]
            if len(candidate_ids) == 1:
                elected.append(candidate_ids[0])
            else:
                with LogEntry(round_log) as entry:
                    entry.log("Multiple candidates elected with %d votes." % (votes), echo=True)
                    for candidate_id in candidate_ids:
                        entry.log("    %s" % (self.candidate_title[candidate_id]), echo=True)
                    tie_breaker_round = self.find_tie_breaker(candidate_ids)
                    if tie_breaker_round is not None:
                        entry.log("Tie broken from previous totals", echo=True)
                        for candidate_id in reversed(sorted(candidate_ids, key=tie_breaker_round.get_vote_count)):
                            elected.append(candidate_id)
                    else:
                        entry.log("No tie breaker round: input required from Australian Electoral Officer. Elect candidates in order:", echo=True)
                        permutations = itertools.permutations(candidate_ids)
                        for idx, permutation in enumerate(permutations):
                            entry.log("%d) %s" % (idx + 1, ', '.join([self.candidate_title(t) for t in permutation])))
                        choice = int(self.input_or_automated(entry, "choose election order: "))
                        for candidate_id in permutations[choice - 1]:
                            elected.append(candidate_id)
        return elected

    def get_initial_totals(self):
        "determine the initial total for each candidate. only call this at the start of round 1"
        candidate_votes = {}
        # initialise to zero for every individual candidate
        for candidate_id in self.candidate_ids:
            candidate_votes[candidate_id] = 0
        for candidate_id in self.candidate_ids:
            candidate_votes[candidate_id] = self.candidate_bundle_transactions.paper_count(candidate_id)
        for candidate_id in candidate_votes:
            candidate_votes[candidate_id] = int(candidate_votes[candidate_id])
        return candidate_votes, 0, 0

    def get_next_preference(self, ticket):
        """
        returns the next preference expressed in the ticket, skipping any elected/excluded candidates
        if no preferences remain (exhauseted ballot) returns None
        """
        while True:
            ticket.next_preference()
            candidate_id = ticket.get_preference()
            if candidate_id is None:
                return
            if candidate_id not in self.candidates_elected and candidate_id not in self.candidates_excluded:
                return candidate_id

    def distribute_bundle_transactions(self, from_candidate_id, bundle_transactions_to_distribute, transfer_value, candidate_aggregates):
        # figure out how many net votes, and which ticket_tpls, go where
        incoming_tickets = {}
        exhausted_papers = 0

        candidate_votes = candidate_aggregates.get_candidate_votes()

        # remaining aware of split tickets, determine how many papers go to
        # each candidate; effectively we unpack each bundle into preference flows,
        # split as needed, and then repack into new bundles
        votes_from = 0
        for bundle_transaction in bundle_transactions_to_distribute:
            # take the bundle away from the candidate
            votes_from += bundle_transaction.get_votes()
            self.candidate_bundle_transactions.transfer_from(from_candidate_id, bundle_transaction)

            for bundle in bundle_transaction:
                to_candidates = {}
                for preference_flow in bundle.get_ticket():
                    to_candidate = self.get_next_preference(preference_flow)
                    if to_candidate is None:
                        exhausted_papers += bundle.get_size()
                        continue
                    if to_candidate not in to_candidates:
                        to_candidates[to_candidate] = []
                    to_candidates[to_candidate].append(preference_flow)

                for to_candidate in to_candidates:
                    preference_flows = to_candidates[to_candidate]
                    frac_of_total = fractions.Fraction(len(preference_flows), len(bundle.get_ticket()))
                    tickets_count = int(frac_of_total * bundle.get_size())
                    if to_candidate not in incoming_tickets:
                        incoming_tickets[to_candidate] = []
                    incoming_tickets[to_candidate].append((tuple(preference_flows), tickets_count))
        candidate_votes[from_candidate_id] -= votes_from

        for candidate_id in sorted(incoming_tickets, key=self.candidate_order):
            bundles_moving = []
            for preference_flows, new_count in incoming_tickets[candidate_id]:
                bundles_moving.append(PaperBundle(Ticket(preference_flows), new_count, transfer_value))
            bundle_transaction = BundleTransaction(bundles_moving)
            self.candidate_bundle_transactions.transfer_to(candidate_id, bundle_transaction)
            candidate_votes[candidate_id] += bundle_transaction.get_votes()

        exhausted_votes = int(exhausted_papers * transfer_value)
        return candidate_votes, exhausted_votes, exhausted_papers

    def elect(self, round_log, round_number, candidate_aggregates, candidate_id):
        self.candidates_elected[candidate_id] = {
            'order': len(self.candidates_elected) + 1,
            'round': round_number
        }
        transfer = None
        if len(self.candidates_elected) != self.vacancies:
            excess_votes = candidate_aggregates.get_vote_count(candidate_id) - self.quota
            assert(excess_votes >= 0)
            transfer_value = fractions.Fraction(excess_votes, self.candidate_bundle_transactions.paper_count(candidate_id))
            assert(transfer_value >= 0)
            self.election_distributions_pending.append((candidate_id, transfer_value))
            transfer = excess_votes, float(transfer_value)
        round_log.add_elected(candidate_id, len(self.candidates_elected), transfer)

    def exclude(self, round_log, round_number, candidate_id, next_to_min_votes, min_votes, next_candidates):
        margin = None
        if next_to_min_votes is not None:
            margin = next_to_min_votes - min_votes
        self.candidates_excluded[candidate_id] = {
            'order': len(self.candidates_excluded) + 1,
            'round': round_number,
            'margin': margin or 0
        }
        transfer_values = set()
        for bundle_transaction in self.candidate_bundle_transactions.get(candidate_id):
            transfer_values.add(bundle_transaction.get_transfer_value())

        round_log.set_excluded(
            candidate_id,
            next_candidates,
            margin,
            [float(t) for t in reversed(sorted(transfer_values))])

        for transfer_value in reversed(sorted(transfer_values)):
            self.exclusion_distributions_pending.append((candidate_id, transfer_value))

    def process_election(self, round_log, distribution, last_total):
        distributed_candidate_id, transfer_value = distribution
        round_log.set_distribution({
            'type': 'election',
            'candidate_id': distributed_candidate_id,
            'transfer_value': float(transfer_value)})
        total, exhausted_votes, exhausted_papers = self.distribute_bundle_transactions(
            distributed_candidate_id,
            self.candidate_bundle_transactions.get(distributed_candidate_id),
            transfer_value,
            last_total)
        total[distributed_candidate_id] = self.quota
        return distributed_candidate_id, total, exhausted_votes, exhausted_papers

    def process_exclusion(self, round_log, distribution, last_total):
        distributed_candidate_id, transfer_value = distribution
        round_log.set_distribution({
            'type': 'exclusion',
            'candidate_id': distributed_candidate_id,
            'transfer_value': float(transfer_value)})
        bundles_to_distribute = []
        for bundle in self.candidate_bundle_transactions.get(distributed_candidate_id):
            if bundle.get_transfer_value() == transfer_value:
                bundles_to_distribute.append(bundle)

        candidate_votes, exhausted_votes, exhausted_papers = self.distribute_bundle_transactions(
            distributed_candidate_id,
            bundles_to_distribute,
            transfer_value,
            last_total)
        return distributed_candidate_id, candidate_votes, exhausted_votes, exhausted_papers

    def have_pending_exclusion_distribution(self):
        return len(self.exclusion_distributions_pending) > 0

    def process_exclusion_distribution(self, round_log, last_candidate_aggregates):
        distribution, *self.exclusion_distributions_pending = self.exclusion_distributions_pending
        return self.process_exclusion(round_log, distribution, last_candidate_aggregates)

    def have_pending_election_distribution(self):
        return len(self.election_distributions_pending) > 0

    def process_election_distribution(self, round_log, last_candidate_aggregates):
        distribution, *self.election_distributions_pending = self.election_distributions_pending
        return self.process_election(round_log, distribution, last_candidate_aggregates)

    def candidate_ids_display(self, candidate_aggregates):
        """
        iterator of candidate ids in display order
        """
        return sorted(candidate_aggregates.get_candidate_votes(), key=self.candidate_order)

    def json_log(self, round_number, candidate_aggregates):
        if self.test_log_dir is None:
            return
        log = []
        for candidate_id in self.candidate_ids_display(candidate_aggregates):
            log.append((self.candidate_title(candidate_id), candidate_aggregates.get_vote_count(candidate_id)))
        with open(os.path.join(self.test_log_dir, 'round_%d.json' % (round_number)), 'w') as fd:
            json.dump(log, fd, sort_keys=True,
                      indent=4, separators=(',', ': '))

    def candidate_election_order(self, candidate_id):
        """only for use in sorting for output"""
        if candidate_id not in self.candidates_elected:
            return self.vacancies + 1
        return self.candidates_elected[candidate_id]['order']

    def log_round_count(self, round_log, affected, last_candidate_aggregates, candidate_aggregates):
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

        r = {
            'candidates': [],
            'after': exloss(candidate_aggregates)
        }
        if last_candidate_aggregates is not None:
            before = exloss(last_candidate_aggregates)
            r['delta'] = dict((t, r['after'][t] - before[t]) for t in before)
        for candidate_id in reversed(sorted(self.candidate_ids_display(candidate_aggregates), key=lambda x: (candidate_aggregates.get_vote_count(x), self.vacancies - self.candidate_election_order(x)))):
            entry = {
                'id': candidate_id,
                'after': agg(candidate_aggregates),
            }
            if candidate_id in self.candidates_elected:
                entry['elected'] = self.candidates_elected[candidate_id]['order']
            if candidate_id in self.candidates_excluded:
                entry['excluded'] = self.candidates_excluded[candidate_id]['order']
            done = False
            if entry.get('excluded'):
                if candidate_id not in affected and \
                        candidate_id not in (t[0] for t in self.exclusion_distributions_pending) and \
                        candidate_id not in (t[0] for t in self.election_distributions_pending):
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

    def find_tie_breaker(self, candidate_ids):
        """
        finds a round in the count history in which the candidate_ids each had different vote counts
        if no such round exists, returns None
        """
        for candidate_aggregates in reversed(self.round_candidate_aggregates):
            candidates_on_vote = {}
            for candidate_id in candidate_ids:
                votes = candidate_aggregates.get_vote_count(candidate_id)
                if votes not in candidates_on_vote:
                    candidates_on_vote[votes] = 0
                candidates_on_vote[votes] += 1
            if max(candidates_on_vote.values()) == 1:
                return candidate_aggregates

    def ask_electoral_officer_tie(self, entry, question, candidate_ids):
        sorted_candidate_ids = list(sorted(candidate_ids, key=self.candidate_title))
        for idx, candidate_id in enumerate(sorted_candidate_ids):
            entry.log("[%3d] - %s" % (idx + 1, self.candidate_title(candidate_id)), echo=True)
        return sorted_candidate_ids[int(self.input_or_automated(entry, question)) - 1]

    def exclude_a_candidate(self, round_log, round_number, candidate_aggregates):
        def eligible(candidate_id):
            return candidate_id not in self.candidates_elected and candidate_id not in self.candidates_excluded

        candidate_ids = [t for t in self.candidate_ids_display(candidate_aggregates) if eligible(t)]
        min_votes = min(candidate_aggregates.get_vote_count(t) for t in candidate_ids)

        candidates_for_exclusion = []
        for candidate_id in candidate_ids:
            if candidate_aggregates.get_vote_count(candidate_id) == min_votes:
                candidates_for_exclusion.append(candidate_id)

        next_to_min_votes = None
        candidates_next_excluded = None
        if len(candidates_for_exclusion) > 1:
            with LogEntry(round_log) as entry:
                entry.log("Multiple candidates for exclusion holding %d votes:" % (min_votes))
                for candidate_id in candidates_for_exclusion:
                    entry.log("    %s" % self.candidate_title(candidate_id))
                tie_breaker_round = self.find_tie_breaker(candidates_for_exclusion)
                if tie_breaker_round is not None:
                    excluded_votes = dict((tie_breaker_round.get_vote_count(candidate_id), candidate_id) for candidate_id in candidates_for_exclusion)
                    entry.log("Tie broken from previous totals")
                    lowest_vote = min(excluded_votes)
                    excluded_candidate_id = excluded_votes[lowest_vote]
                else:
                    entry.log("No tie breaker round: input required from Australian Electoral Officer. Exclude candidate:", echo=True)
                    excluded_candidate_id = self.ask_electoral_officer_tie(entry, "exclude candidate: ", candidates_for_exclusion)
        else:
            excluded_candidate_id = candidates_for_exclusion[0]
            candidates_with_more_than_min = [candidate_aggregates.get_vote_count(t) for t in candidate_ids if candidate_aggregates.get_vote_count(t) > min_votes]
            if len(candidates_with_more_than_min) > 0:
                next_to_min_votes = min(candidate_aggregates.get_vote_count(t) for t in candidate_ids if candidate_aggregates.get_vote_count(t) > min_votes)
                candidates_next_excluded = [t for t in candidate_ids if candidate_aggregates.get_vote_count(t) == next_to_min_votes]

        self.exclude(round_log, round_number, excluded_candidate_id, next_to_min_votes, min_votes, candidates_next_excluded)

    def process_round(self, round_number, round_log):
        if round_number > 1:
            last_candidate_aggregates = self.round_candidate_aggregates[-1]
            exhausted_votes = last_candidate_aggregates.get_exhausted_votes()
            exhausted_papers = last_candidate_aggregates.get_exhausted_papers()
        else:
            last_candidate_aggregates = None
            exhausted_votes = exhausted_papers = 0

        #
        # we will always have something to do in each round.
        # we maintain two queues - a queue of exclusion distributions,
        # a queue of election distributions. the exclusion distribution
        # queue takes precedence.
        #
        affected = set()
        if round_number == 1:
            candidate_votes, votes_exhausted_in_round, papers_exhausted_in_round = \
                self.get_initial_totals()
        elif self.have_pending_exclusion_distribution():
            candidate_id, candidate_votes, votes_exhausted_in_round, papers_exhausted_in_round = \
                self.process_exclusion_distribution(round_log, last_candidate_aggregates)
            affected.add(candidate_id)
        elif len(self.election_distributions_pending) > 0:
            candidate_id, candidate_votes, votes_exhausted_in_round, papers_exhausted_in_round = \
                self.process_election_distribution(round_log, last_candidate_aggregates)
            affected.add(candidate_id)
        else:
            raise Exception("No distribution or exclusion this round. Nothing to do - unreachable.")

        candidate_aggregates = CandidateAggregates(self.total_papers, candidate_votes, self.candidate_bundle_transactions.candidate_paper_count(),
                                                   exhausted_votes + votes_exhausted_in_round, exhausted_papers + papers_exhausted_in_round)
        self.round_candidate_aggregates.append(candidate_aggregates)

        self.json_log(round_number, candidate_aggregates)

        #
        # determine actions for this round (if any)
        #
        # if anyone has a quota, elect them; otherwise,  if we're not distribution over-quota,
        # and we're not distributing the result of an exclusion, find someone to exclude (or
        # go with various end-state catch-alls)
        #
        try:
            elected = self.elected_candidates_in_order(round_log, candidate_aggregates)
            if len(elected) > 0:
                for candidate_id in elected:
                    self.elect(round_log, round_number, candidate_aggregates, candidate_id)
                    affected.add(candidate_id)
                    if len(self.candidates_elected) == self.vacancies:
                        return False
            elif not self.have_pending_election_distribution() and not self.have_pending_exclusion_distribution():
                in_the_running = list(set(self.candidate_ids_display(candidate_aggregates)) - set(self.candidates_elected) - set(self.candidates_excluded))
                still_to_elect = self.vacancies - len(self.candidates_elected)
                # section 273(18); if we're down to N candidates in the running, with N vacancies, the remaining candidates are elected
                if len(in_the_running) == still_to_elect:
                    with LogEntry(round_log) as entry:
                        entry.log("Final %d vacancies filled from last candidates standing, in accordance with section 273(18)." % (still_to_elect), echo=True)
                        for candidate in reversed(sorted(in_the_running, key=lambda c: candidate_aggregates.get_vote_count(c))):
                            self.elect(round_log, round_number, candidate_aggregates, candidate_id)
                            affected.add(candidate_id)
                    return False
                # section 273(17); if we're down to two candidates in the running, the candidate with the highest number of votes wins - even
                # if they don't have a quota
                if len(in_the_running) == 2:
                    candidate_a = in_the_running[0]
                    candidate_b = in_the_running[1]
                    candidate_a_votes = candidate_aggregates.get_vote_count(candidate_a)
                    candidate_b_votes = candidate_aggregates.get_vote_count(candidate_b)
                    if candidate_a_votes == candidate_b_votes:
                        with LogEntry(round_log) as entry:
                            entry.log("Final two candidates lack a quota and are tied. Australian Electoral Officer for this state must decide the final election.", echo=True)
                            candidate_id = self.ask_electoral_officer_tie(entry, "choose candidate to elect: ", in_the_running)
                            self.elect(round_log, round_number, candidate_id)
                            affected.add(candidate_id)
                    else:
                        with LogEntry(round_log) as entry:
                            entry.log("Two candidates remain, with no candidate holding a quota. In accordance with 273(17), candidate with highest total is elected.", echo=True)
                        if candidate_a_votes > candidate_b_votes:
                            self.elect(round_log, round_number, candidate_aggregates, candidate_a)
                            affected.add(candidate_a)
                        elif candidate_b_votes > candidate_a_votes:
                            self.elect(round_log, round_number, candidate_aggregates, candidate_b)
                            affected.add(candidate_b)
                    return False
                # if a distribution doesn't generate any
                while True:
                    self.exclude_a_candidate(round_log, round_number, candidate_aggregates)
                    if self.have_pending_exclusion_distribution():
                        break
        finally:
            # we want to log elected candidates from this round
            round_log.set_count(self.log_round_count(round_log, affected, last_candidate_aggregates, candidate_aggregates))
        # keep going
        return True

    def count(self):
        self.round_candidate_aggregates = []
        # this is the definitive data structure recording which votes go to which candidate
        # and how many votes that candidate has. it is mutated each round.
        for round_number in itertools.count(1):
            round_log = RoundLog(round_number)
            self.output.add_round(round_log)
            if not self.process_round(round_number, round_log):
                break

    def summary(self):
        r = {
            'elected': [],
            'excluded': []
        }

        def in_order(l):
            return enumerate(sorted(l, key=lambda k: l[k]['order']))

        def outcome(candidate_id, d):
            r = d[candidate_id].copy()
            r['id'] = candidate_id
            return r

        for idx, candidate_id in in_order(self.candidates_elected):
            r['elected'].append(outcome(candidate_id, self.candidates_elected))
        for idx, candidate_id in in_order(self.candidates_excluded):
            r['excluded'].append(outcome(candidate_id, self.candidates_excluded))
        return r
