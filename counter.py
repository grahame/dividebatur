import sys, itertools, json, fractions, os
from output import HtmlOutput, RoundLog, LogEntry

class PreferenceFlow:
    """
    a preference flow; describes a preference flow and maintains state for it 
    during the count
    """
    def __init__(self, preferences):
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
        matches = []
        for pref, candidate in self.preferences:
            if pref == self.up_to_preference:
                matches.append(candidate)
        if len(matches) == 1:
            return matches[0]

    def __repr__(self):
        return "<PreferenceFlow>"

class Ticket:
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
            prefs = {}
            for preference_flow in ticket:
                preference = preference_flow.get_preference()
                if preference not in prefs:
                    prefs[preference] = []
                prefs[preference].append(preference_flow)
            for pref in prefs:
                if pref is not None:
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
    def __init__(self, vacancies, papers_for_count, candidate_ids, candidate_order, candidate_title, automated_responses, **template_vars):
        self.output = HtmlOutput()
        self.automated_responses = automated_responses
        self.vacancies, self.papers_for_count, self.candidate_ids, self.candidate_order, self.candidate_title = \
            vacancies, papers_for_count, candidate_ids, candidate_order, candidate_title
        self.next_automated = 0
        # senators elected; candidates excluded from the count; neither of these are
        # eligible to have papers distributed to them
        self.candidates_elected = []
        self.candidates_excluded = []
        # we maintain queues of distributions pending; for exclusions and elections. all exclusions
        # must be processed before any elections are processed, even if a part-completed distribution
        # leads to an election
        self.exclusion_distributions_pending = []
        self.election_distributions_pending = []
        # determine quota
        self.determine_quota()
        # initial assignment of tickets
        self.candidate_bundle_transactions = CandidateBundleTransactions(self.candidate_ids, self.papers_for_count)
        # execute the count
        self.count()
        # log who got elected/excluded
        self.summary()
        # render to HTML
        self.output.render(self, template_vars)

    def input_or_automated(self, entry, qn):
        if self.next_automated < len(self.automated_responses):
            resp = self.automated_responses[self.next_automated]
            entry.log("%s\nautomation: '%s' entered" % (qn, resp), echo=True)
            self.next_automated += 1
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
                            entry.log("%d) %s" % (idx+1, ', '.join([self.candidate_title(t) for t in permutation])))
                        choice = int(self.input_or_automated(entry, "choose election order: "))
                        for candidate_id in permutations[choice-1]:
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

    def distribute_bundle_transactions(self, entry, from_candidate_id, bundle_transactions_to_distribute, transfer_value, candidate_aggregates):
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
            entry.log("%7d votes (from %7d papers) distributed to %s" % (
                bundle_transaction.get_votes(), bundle_transaction.get_papers(),
                self.candidate_title(candidate_id)))

        exhausted_votes = int(exhausted_papers * transfer_value)
        entry.log("%7d votes exhausted (from %7d papers)" % (exhausted_votes, exhausted_papers))
        return candidate_votes, exhausted_votes, exhausted_papers

    def elect(self, round_log, candidate_aggregates, candidate_id):
        self.candidates_elected.append(candidate_id)
        with LogEntry(round_log) as entry:
            entry.log("\n%s elected #%d" % (self.candidate_title(candidate_id), len(self.candidates_elected)))
            if len(self.candidates_elected) != self.vacancies:
                excess_votes = candidate_aggregates.get_vote_count(candidate_id) - self.quota
                assert(excess_votes >= 0)
                transfer_value = fractions.Fraction(excess_votes, self.candidate_bundle_transactions.paper_count(candidate_id))
                assert(transfer_value >= 0)
                self.election_distributions_pending.append((candidate_id, transfer_value))
                entry.log("    %7d excess ballots to be distributed at a transfer value of %g" % (excess_votes, float(transfer_value)))

    def exclude(self, entry, candidate_id):
        self.candidates_excluded.append(candidate_id)
        entry.log("Candidate %s excluded." % self.candidate_title(candidate_id))
        transfer_values = set()
        for bundle_transaction in self.candidate_bundle_transactions.get(candidate_id):
            transfer_values.add(bundle_transaction.get_transfer_value())
        for transfer_value in reversed(sorted(transfer_values)):
            entry.log("    Queued distribution of preferences with transfer value %g" % (transfer_value))
            self.exclusion_distributions_pending.append((candidate_id, transfer_value))

    def process_election(self, round_log, distribution, last_total):
        distributed_candidate_id, transfer_value = distribution
        with LogEntry(round_log) as entry:
            entry.log("Distribution of elected candidate %s at transfer value %g:" % (self.candidate_title(distributed_candidate_id), transfer_value))

            total, exhausted_votes, exhausted_papers = self.distribute_bundle_transactions(
                entry,
                distributed_candidate_id,
                self.candidate_bundle_transactions.get(distributed_candidate_id),
                transfer_value,
                last_total)
            total[distributed_candidate_id] = self.quota
            return total, exhausted_votes, exhausted_papers

    def process_exclusion(self, round_log, distribution, last_total):
        distributed_candidate_id, transfer_value = distribution
        with LogEntry(round_log) as entry:
            entry.log("Exclusion of candidate %s: distribution of preferences with transfer value %g" % (self.candidate_title(distributed_candidate_id), transfer_value))
            bundles_to_distribute = []
            for bundle in self.candidate_bundle_transactions.get(distributed_candidate_id):
                if bundle.get_transfer_value() == transfer_value:
                    bundles_to_distribute.append(bundle)

            candidate_votes, exhausted_votes, exhausted_papers = self.distribute_bundle_transactions(
                entry,
                distributed_candidate_id,
                bundles_to_distribute,
                transfer_value,
                last_total)
            return candidate_votes, exhausted_votes, exhausted_papers

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
        log = []
        for candidate_id in self.candidate_ids_display(candidate_aggregates):
            log.append((self.candidate_title(candidate_id), candidate_aggregates.get_vote_count(candidate_id)))
        # naff, FIXME
        if os.access("./log/", os.W_OK):
            with open('log/round_%d.json' % (round_number), 'w') as fd:
                json.dump(log, fd, sort_keys=True,
                    indent=4, separators=(',', ': '))

    def print_round(self, round_number, last_candidate_aggregates, candidate_aggregates):
        header = []
        columns = []
        widths = []

        def candidates_column():
            c = []
            for candidate_id in self.candidate_ids_display(candidate_aggregates):
                c.append(self.candidate_title(candidate_id))
            c.append("Exhausted")
            c.append("Gain/loss")
            c.append("Total")
            return c

        def papers_column(agg):
            c = []
            for candidate_id in self.candidate_ids_display(agg):
                c.append(agg.get_paper_count(candidate_id))
            c.append(agg.get_exhausted_papers())
            c.append(agg.get_gain_loss_papers())
            c.append(sum(c))
            return c

        def votes_column(agg):
            c = []
            for candidate_id in self.candidate_ids_display(agg):
                c.append(agg.get_vote_count(candidate_id))
            c.append(agg.get_exhausted_votes())
            c.append(agg.get_gain_loss_votes())
            c.append(sum(c))
            return c

        def delta_column(c1, c2):
            assert(len(c1) == len(c2))
            c = []
            for row in range(len(c1)):
                c.append(c2[row] - c1[row])
            # no net changes!
            assert(sum(c) == 0)
            c.append(sum(c))
            return c

        def status_column():
            c = []
            for candidate_id in self.candidate_ids_display(candidate_aggregates):
                if candidate_id in self.candidates_elected:
                    c.append("✓")
                elif candidate_id in self.candidates_excluded:
                    c.append("✗")
                else:
                    c.append("")
            c.append("")
            c.append("")
            c.append("")
            return c

        header.append("Candidate")
        widths.append(25)
        columns.append(candidates_column())

        header.append("Status")
        widths.append(6)
        columns.append(status_column())

        nw = 12

        # paper columns
        if last_candidate_aggregates is not None:
            header.append("Papers @ %d"  % (round_number-1))
            widths.append(nw)
            columns.append(papers_column(last_candidate_aggregates))
        header.append("Papers @ %d"  % (round_number))
        widths.append(nw)
        columns.append(papers_column(candidate_aggregates))
        if last_candidate_aggregates is not None:
            header.insert(-1, "ΔPapers")
            widths.insert(-1, nw)
            columns.insert(-1, delta_column(columns[-2], columns[-1]))

        # vote columns
        if last_candidate_aggregates is not None:
            header.append("Votes @ %d"  % (round_number-1))
            widths.append(nw)
            columns.append(votes_column(last_candidate_aggregates))
        header.append("Votes @ %d"  % (round_number))
        widths.append(nw)
        columns.append(votes_column(candidate_aggregates))
        if last_candidate_aggregates is not None:
            header.insert(-1, "ΔVotes")
            widths.insert(-1, nw)
            columns.insert(-1, delta_column(columns[-2], columns[-1]))

        fmt = "  ".join("%%%ds" % (t) for t in widths)
        self.output.log_line(fmt % (tuple(header)))

        for row_idx in range(len(columns[0])):
            self.output.log_line(fmt % (tuple(column[row_idx] for column in columns)))

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
            entry.log("[%3d] - %s" % (idx+1, self.candidate_title(candidate_id)), echo=True)
        return sorted_candidate_ids[int(self.input_or_automated(entry, question)) - 1]

    def exclude_a_candidate(self, round_log, candidate_aggregates):
        eligible = lambda candidate_id: candidate_id not in self.candidates_elected and candidate_id not in self.candidates_excluded

        candidate_ids = [t for t in self.candidate_ids_display(candidate_aggregates) if eligible(t)]
        min_votes = min(candidate_aggregates.get_vote_count(t) for t in candidate_ids)
        
        candidates_with_more_than_min = [candidate_aggregates.get_vote_count(t) for t in candidate_ids if candidate_aggregates.get_vote_count(t) > min_votes]
        next_to_min_votes = None
        if len(candidates_with_more_than_min) > 0:
            next_to_min_votes = min(candidate_aggregates.get_vote_count(t) for t in candidate_ids if candidate_aggregates.get_vote_count(t) >= min_votes)
            candidates_next_excluded = [t for t in candidate_ids if candidate_aggregates.get_vote_count(t) == next_to_min_votes]

        candidates_for_exclusion = []
        for candidate_id in candidate_ids:
            if candidate_aggregates.get_vote_count(candidate_id) == min_votes:
                candidates_for_exclusion.append(candidate_id)

        if len(candidates_for_exclusion) > 1:
            with LogEntry(round_log) as entry:
                entry.log("\nMultiple candidates for exclusion holding %d votes:" % (min_votes))
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
        with LogEntry(round_log) as entry:
            self.exclude(entry, excluded_candidate_id)
            if next_to_min_votes is not None:
                entry.log("Exclusion margin from next candidate (%s): %d votes (%d vs. %d)" % (','.join(self.candidate_title(t) for t in candidates_next_excluded), next_to_min_votes - min_votes, min_votes, next_to_min_votes))

    def process_round(self, round_number, round_log):
        if round_number > 1:
            last_candidate_aggregates = self.round_candidate_aggregates[-1]
            exhausted_votes = last_candidate_aggregates.get_exhausted_votes()
            exhausted_papers = last_candidate_aggregates.get_exhausted_papers()
        else:
            last_candidate_aggregates = None
            exhausted_votes = exhausted_papers = 0

        if round_number == 1:
            candidate_votes, votes_exhausted_in_round, papers_exhausted_in_round = self.get_initial_totals()
        elif self.have_pending_exclusion_distribution():
            candidate_votes, votes_exhausted_in_round, papers_exhausted_in_round = self.process_exclusion_distribution(round_log, last_candidate_aggregates)
        elif len(self.election_distributions_pending) > 0:
            candidate_votes, votes_exhausted_in_round, papers_exhausted_in_round = self.process_election_distribution(round_log, last_candidate_aggregates)
        else:
            raise Exception("No distribution or exclusion this round. Nothing to do - unreachable.")

        candidate_aggregates = CandidateAggregates(self.total_papers, candidate_votes, self.candidate_bundle_transactions.candidate_paper_count(),
             exhausted_votes + votes_exhausted_in_round, exhausted_papers + papers_exhausted_in_round)
        self.round_candidate_aggregates.append(candidate_aggregates)

        self.json_log(round_number, candidate_aggregates)
        round_log.set_aggregates(last_candidate_aggregates, candidate_aggregates)
        self.print_round(round_number, last_candidate_aggregates, candidate_aggregates)

        elected = self.elected_candidates_in_order(round_log, candidate_aggregates)
        if len(elected) > 0:
            for candidate_id in elected:
                self.elect(round_log, candidate_aggregates, candidate_id)
                if len(self.candidates_elected) == self.vacancies:
                    round_log.post_note("All vacancies filled.")
                    return False
        elif not self.have_pending_election_distribution() and not self.have_pending_exclusion_distribution():
            # section 273(17); if we're down to two candidates in the running, the candidate with the highest number of votes wins - even 
            # if they don't have a quota
            in_the_running = list(set(self.candidate_ids_display(candidate_aggregates)) - set(self.candidates_elected) - set(self.candidates_excluded))
            if len(in_the_running) == 2:
                candidate_a = in_the_running[0]
                candidate_b = in_the_running[1]
                candidate_a_votes = candidate_aggregates.get_vote_count(candidate_a)
                candidate_b_votes = candidate_aggregates.get_vote_count(candidate_b)
                if candidate_a_votes > candidate_b_votes:
                    self.elect(round_log, candidate_aggregates, candidate_a)
                elif candidate_b_votes > candidate_a_votes:
                    self.elect(round_log, candidate_aggregates, candidate_b)
                else:
                    with LogEntry(round_log) as entry:
                        entry.log("Final two candidates lack a quota and are tied. Australian Electoral Officer for this state must decided the final election.", echo=True)
                        self.elect(round_log, self.ask_electoral_officer_tie(entry, "choose candidate to elect: ", in_the_running))
                return False
            # if a distribution doesn't generate any 
            while True:
                self.exclude_a_candidate(round_log, candidate_aggregates)
                if self.have_pending_exclusion_distribution():
                    break
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
        with LogEntry(round_log) as entry:
            entry.log("Candidates elected:")
            for idx, candidate_id in enumerate(self.candidates_elected):
                entry.log("    %3d - %s" % (idx+1, self.candidate_title(candidate_id)))
            entry.log("\nExclusion order:")
            for idx, candidate_id in enumerate(self.candidates_excluded):
                entry.log("    %3d - %s" % (idx+1, self.candidate_title(candidate_id)))

