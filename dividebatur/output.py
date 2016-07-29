import sys
import datetime
import json


class LogEntry:

    def __init__(self, output):
        self.lines = []
        self.output_to = output

    def __enter__(self):
        return self

    def log(self, line, echo=False, end=None):
        self.lines.append(line)
        if echo:
            print(line, file=sys.stderr, end=end)

    def __exit__(self, type, value, tb):
        self.output_to.add_note('\n'.join(self.lines))


class RoundLog(LogEntry):

    def __init__(self, number):
        self.number = number
        self.note = []
        self.elected = []
        self.exclusion = None
        self.distribution = None
        self.count = None

    def json(self):
        return {
            'number': self.number,
            'note': self.note,
            'elected': self.elected,
            'exclusion': self.exclusion,
            'distribution': self.distribution,
            'count': self.count
        }

    def set_count(self, count):
        self.count = count

    def set_distribution(self, distribution):
        self.distribution = distribution

    def add_elected(self, candidate_id, pos, transfer):
        if transfer is not None:
            t = {'excess': transfer[0], 'value': transfer[1]}
        else:
            t = None
        self.elected.append({
            'id': candidate_id,
            'pos': pos,
            'transfer': t
        })

    def set_exclusion(self, candidates, transfers, reason):
        info = {
            'candidates': candidates,
            'reason': reason.reason,
            'transfers': [float(t) for t in transfers]
        }
        info.update(reason.info)
        self.exclusion = info

    def add_note(self, message):
        self.note.append(message)


class JsonOutput:

    def __init__(self, fname):
        self.rounds = []
        self.fname = fname
        self.summary = None

    def add_round(self, round):
        self.rounds.append(round)

    def set_summary(self, summary_info):
        self.summary = summary_info

    def render(self, counter, template_vars):
        params = {
            'total_papers': counter.total_papers,
            'quota': counter.quota,
            'vacancies': counter.vacancies,
            'dt': datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        params.update(template_vars)
        obj = {
            'candidates': counter.candidate_json(),
            'parties': counter.party_json(),
            'parameters': params,
            'rounds': [t.json() for t in self.rounds],
            'summary': self.summary,
        }
        with open(self.fname, 'w') as fd:
            json.dump(obj, fd, indent=4)
