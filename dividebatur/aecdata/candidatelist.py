import csv
import collections

from .utils import ticket_sort_key, named_tuple_iter


Candidate = collections.namedtuple('Candidate', [
    'candidate_id',
    'surname',
    'given_name',
    'candidate_order',  # Position within the entire ballot, 0 based.
    'group_id',         # Group ID
    'ballot_position',  # Position within group, 1 based.
    'party_name',
    'party_abbreviation',
])


Group = collections.namedtuple('Group', [
    'group_id',
    'party_name',
    'party_abbreviation',
    'candidates',       # Ordered list of candidates in group
])


class CandidateList:
    """CandidateList provides a list of senate candidates and groups.

    The following members are publicly accessible:

      - candidates: a list of all candidates, in the order they appear
        on the ballot.
      - candidate_by_id: a dictionary mapping candidate IDs to the candidate.
      - groups: a list of groups, in the order they appear on the
        ballot.  Does not include the ungrouped candidates.
      - group_by_id: a dictionary mapping group IDs (e.g. A, B, ...)
        to the group.
    """

    def __init__(self, state, all_candidates_csv, senate_candidates_csv):
        self.state = state
        self._load(all_candidates_csv, senate_candidates_csv)

    def _load(self, all_candidates_csv, senate_candidates_csv):
        self.candidates = []
        self.candidate_by_id = {}
        self.groups = []
        self.group_by_id = {}

        candidate_by_name_party, party_ab = self._load_senate_candidates(
            senate_candidates_csv)
        current_group = None
        current_party = None
        current_candidates = []
        for c in self._load_all_candidates(all_candidates_csv):
            if c.ticket != current_group:
                if current_group is not None and current_group != "UG":
                    group = Group(current_group,
                                  current_party,
                                  party_ab[current_party],
                                  tuple(current_candidates))
                    self.groups.append(group)
                    self.group_by_id[group.group_id] = group
                current_group = c.ticket
                current_party = c.party_ballot_nm
                current_candidates = []

            candidate_id = candidate_by_name_party[
                c.surname, c.ballot_given_nm, c.party_ballot_nm]
            candidate = Candidate(candidate_id,
                                  c.surname,
                                  c.ballot_given_nm,
                                  len(self.candidates),
                                  current_group,
                                  c.ballot_position,
                                  c.party_ballot_nm,
                                  party_ab[c.party_ballot_nm])
            self.candidates.append(candidate)
            self.candidate_by_id[candidate.candidate_id] = candidate
            current_candidates.append(candidate)

        # Add the final group, assuming it isn't the ungrouped candidates
        if current_group is not None and current_group != "UG":
            group = Group(current_group,
                          current_party,
                          party_ab[current_party],
                          tuple(current_candidates))
            self.groups.append(group)
            self.group_by_id[group.group_id] = group

    def _load_all_candidates(self, all_candidates_csv):
        candidates = []
        with open(all_candidates_csv, 'rt') as fd:
            reader = csv.reader(fd)
            header = next(reader)
            for candidate in sorted(named_tuple_iter('AllCandidate', reader, header, ballot_position=int), key=lambda row: (ticket_sort_key(row.ticket), row.ballot_position)):
                if candidate.state_ab != self.state:
                    continue
                if candidate.nom_ty != 'S':
                    continue
                candidates.append(candidate)
        return candidates

    def _load_senate_candidates(self, senate_candidates_csv):
        by_name_party = {}
        party_ab = {}
        seen_ids = set()
        with open(senate_candidates_csv, 'rt') as fd:
            reader = csv.reader(fd)
            next(reader)  # skip the version
            header = next(reader)
            for candidate in named_tuple_iter(
                    'Candidate', reader, header, CandidateID=int):
                if candidate.StateAb != self.state:
                    continue
                k = (candidate.Surname, candidate.GivenNm, candidate.PartyNm)
                assert candidate.CandidateID not in seen_ids
                assert k not in by_name_party
                by_name_party[k] = candidate.CandidateID
                seen_ids.add(candidate.CandidateID)
                party_ab[candidate.PartyNm] = candidate.PartyAb
        return by_name_party, party_ab

    def get_candidate_id(self, surname, given_name):
        for candidate in self.candidates:
            if candidate.surname == surname and candidate.given_name == given_name:
                return candidate.candidate_id
        raise KeyError((surname, given_name))
