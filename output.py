from jinja2 import Environment, FileSystemLoader
import sys, datetime

class LogEntry:
    def __init__(self, output, post=True):
        self.lines = []
        self.output_to = output
        self.post = post

    def __enter__(self):
        return self

    def log(self, line, echo=False, end=None):
        self.lines.append(line)
        if echo:
            print(line, file=sys.stderr, end=end)

    def __exit__(self, type, value, tb):
        self.output_to.note('\n'.join(self.lines), self.post)

class LogLine:
    def __init__(self, line, echo=False, end=None):
        self.line = line
        if echo:
            print(line, file=sys.stderr, end=end)

    def line(self):
        return self.line

class RoundLog(LogEntry):
    def __init__(self, number):
        self.number = number
        self.pre = []
        self.post = []
        self.elected = []
        self.excluded = None
        self.action = None

    def set_count(self, count):
        self.count = count

    def set_action(self, action):
        self.action = action

    def add_elected(self, candidate_title, pos, transfer):
        if transfer is not None:
            t = { 'excess' : transfer[0], 'value' : transfer[1] }
        else:
            t = None
        self.elected.append({
            'title' : candidate_title,
            'pos' : pos,
            'transfer' : t
            })

    def set_excluded(self, candidate_title, next_candidates, margin, transfer_values):
        self.excluded = {
            'title' : candidate_title,
            'margin' : margin,
            'next_candidates' : next_candidates,
            'transfers' : transfer_values
            }

    def note(self, message, post):
        if post:
            self.post.append(message)
        else:
            self.pre.append(message)

class HtmlOutput:
    def __init__(self, fname):
        self.rounds = []
        self.log = []
        self.fname = fname

    def log_line(self, *args, **kwargs):
        self.log.append(LogLine(*args, **kwargs))

    def add_round(self, round):
        self.rounds.append(round)

    def set_summary(self, summary_info):
        self.summary = summary_info

    def render(self, counter, template_vars):
        env = Environment(loader=FileSystemLoader('./templates/'))
        env.filters['numberfmt'] = lambda v: '{:,d}'.format(v)
        env.filters['f2'] = lambda v: '{:,.2f}'.format(v)
        template = env.get_template('base.html')
        with open(self.fname, 'w') as fd:
            print(template.render(
                log=self.log,
                counter=counter,
                rounds=self.rounds,
                number_rounds=len(self.rounds),
                summary=self.summary,
                dt=datetime.datetime.now(),
                **template_vars), file=fd)

