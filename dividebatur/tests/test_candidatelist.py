import os
import unittest

import dividebatur
from dividebatur.aecdata import CandidateList

datadir = os.path.join(os.path.dirname(dividebatur.__file__),
                       os.pardir, "aec_data")

class CandidateListTests(unittest.TestCase):

    def test_fed2013(self):
        all_candidates_csv = os.path.join(
            datadir, "fed2013", "common",
            "2013federalelection-all-candidates-nat-22-08.csv")
        senate_candidates_csv = os.path.join(
            datadir, "fed2013", "common",
            "SenateCandidatesDownload-17496.csv")

        cl = CandidateList("NSW", all_candidates_csv, senate_candidates_csv)

        self.assertEqual(110, len(cl.candidates))
        self.assertEqual(44, len(cl.groups))

        first_candidate = cl.candidates[0]
        self.assertEqual(24801, first_candidate.candidate_id)
        self.assertEqual("LEYONHJELM", first_candidate.surname)
        self.assertEqual("David", first_candidate.given_name)
        self.assertEqual(0, first_candidate.candidate_order)
        self.assertEqual("A", first_candidate.group_id)
        self.assertEqual(1, first_candidate.ballot_position)
        self.assertEqual("Liberal Democrats", first_candidate.party_name)
        self.assertEqual("LDP", first_candidate.party_abbreviation)

        last_candidate = cl.candidates[-1]
        self.assertEqual(24866, last_candidate.candidate_id)
        self.assertEqual("La MELA", last_candidate.surname)
        self.assertEqual("John", last_candidate.given_name)
        self.assertEqual(109, last_candidate.candidate_order)
        self.assertEqual("UG", last_candidate.group_id)
        self.assertEqual(4, last_candidate.ballot_position)
        self.assertEqual("Independent", last_candidate.party_name)
        self.assertEqual("IND", last_candidate.party_abbreviation)

        first_group = cl.groups[0]
        self.assertEqual("A", first_group.group_id)
        self.assertEqual("Liberal Democrats", first_group.party_name)
        self.assertEqual("LDP", first_group.party_abbreviation)
        self.assertEqual(2, len(first_group.candidates))
        self.assertIs(first_candidate, first_group.candidates[0])

        # Even though the "UG" candidates appear last on the ballot,
        # they do not count as a group.
        last_group = cl.groups[-1]
        self.assertEqual("AR", last_group.group_id)
        self.assertEqual("One Nation", last_group.party_name)
        self.assertEqual("ON", last_group.party_abbreviation)

        # Lookup by ID
        self.assertIs(first_candidate, cl.candidate_by_id[24801])
        self.assertIs(last_group, cl.group_by_id["AR"])

    def test_fed2016(self):
        all_candidates_csv = os.path.join(
            datadir, "fed2016", "common",
            "2016federalelection-all-candidates-nat-30-06-924.csv")
        senate_candidates_csv = os.path.join(
            datadir, "fed2016", "common",
            "SenateCandidatesDownload-20499.csv")

        cl = CandidateList("WA", all_candidates_csv, senate_candidates_csv)

        self.assertEqual(79, len(cl.candidates))
        self.assertEqual(28, len(cl.groups))

        first_candidate = cl.candidates[0]
        self.assertEqual(29437, first_candidate.candidate_id)
        self.assertEqual("IMISIDES", first_candidate.surname)
        self.assertEqual("Mark David", first_candidate.given_name)
        self.assertEqual(0, first_candidate.candidate_order)
        self.assertEqual("A", first_candidate.group_id)
        self.assertEqual(1, first_candidate.ballot_position)
        self.assertEqual("Christian Democratic Party (Fred Nile Group)",
                         first_candidate.party_name)
        self.assertEqual("CDP", first_candidate.party_abbreviation)

        last_candidate = cl.candidates[-1]
        self.assertEqual(29428, last_candidate.candidate_id)
        self.assertEqual("RAMSAY", last_candidate.surname)
        self.assertEqual("Norm", last_candidate.given_name)
        self.assertEqual(78, last_candidate.candidate_order)
        self.assertEqual("UG", last_candidate.group_id)
        self.assertEqual(6, last_candidate.ballot_position)
        self.assertEqual("Independent", last_candidate.party_name)
        self.assertEqual("IND", last_candidate.party_abbreviation)

        first_group = cl.groups[0]
        self.assertEqual("A", first_group.group_id)
        self.assertEqual("Christian Democratic Party (Fred Nile Group)",
                         first_group.party_name)
        self.assertEqual("CDP", first_group.party_abbreviation)
        self.assertEqual(2, len(first_group.candidates))
        self.assertIs(first_candidate, first_group.candidates[0])

        # Even though the "UG" candidates appear last on the ballot,
        # they do not count as a group.
        last_group = cl.groups[-1]
        self.assertEqual("AB", last_group.group_id)
        self.assertEqual("Family First Party", last_group.party_name)
        self.assertEqual("FFP", last_group.party_abbreviation)

        # Lookup by ID
        self.assertIs(first_candidate, cl.candidate_by_id[29437])
        self.assertIs(last_group, cl.group_by_id["AB"])
