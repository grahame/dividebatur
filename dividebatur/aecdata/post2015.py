import csv
from collections import Counter


class FormalPreferences:
    "parse AEC 'formal preferences' CSV file"

    def __init__(self, csv_file):
        """
        csv_file: preferences file to read

        candidate_count: used to build a fast lookup table for the text
        representation of preferences, and defines the highest possible
        preference that can be cast above or below the line
        """
        self._csv_file = csv_file

    def __iter__(self):
        # this is a bit of a hack: it'll blow up if someone numbers a box
        # >= 1024, and the AEC enter that data in. however, it fails harmlessly
        # with an Exception, rather than introducing incorrect data into the
        # count, and it's twice as fast as other ways I've come up with to
        # write this code.
        pref_hash = dict((str(i), i) for i in range(1, 1024))
        pref_hash['*'] = 1
        pref_hash['/'] = 1
        pref_hash[''] = None
        with open(self._csv_file, 'rt') as fd:
            reader = csv.reader(fd)
            header = next(reader)
            assert(header == ['ElectorateNm', 'VoteCollectionPointNm', 'VoteCollectionPointId', 'BatchNo', 'PaperNo', 'Preferences'])
            dummy = next(reader)
            assert(dummy == ['------------', '---------------------', '---------------------', '-------', '-------', '-----------'])
            form_count = Counter(t[5] for t in reader)
            for form, count in form_count.items():
                yield tuple(pref_hash[t] for t in form.split(',')), count
