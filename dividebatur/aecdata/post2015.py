import csv
import re
from collections import Counter

from .utils import int_or_none


class FormalPreferences:
    "parse AEC 'formal preferences' CSV file"

    def __init__(self, csv_file):
        self._csv_file = csv_file

    def __iter__(self):
        sub_re = re.compile('\*|/')

        def parse_prefs(s):
            ", delimited, with * and / meaning 1"
            return tuple(int_or_none(t) for t in sub_re.sub('1', s).split(','))
        with open(self._csv_file, 'rt') as fd:
            reader = csv.reader(fd)
            header = next(reader)
            assert(header == ['ElectorateNm', 'VoteCollectionPointNm', 'VoteCollectionPointId', 'BatchNo', 'PaperNo', 'Preferences'])
            dummy = next(reader)
            assert(dummy == ['------------', '---------------------', '---------------------', '-------', '-------', '-----------'])
            form_count = Counter(t[5] for t in reader)
            for form, count in form_count.items():
                yield parse_prefs(form), count
