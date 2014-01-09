from jinja2 import Environment, FileSystemLoader
import sys, datetime

class LogEntry:
    pass

class LogLine(LogEntry):
    def __init__(self, line, echo=False, end=None):
        super(LogLine, self).__init__()
        self.line = line
        if echo:
            print(line, file=sys.stderr, end=end)

    def line(self):
        return self.line

class RoundLog(LogEntry):
    def __init__(self, number):
        self.number = number
        self.post = []

    def post_note(self, message):
        self.post.append(message)

class HtmlOutput:
    def __init__(self):
        self.rounds = []
        self.log = []

    def log_line(self, *args, **kwargs):
        self.log.append(LogLine(*args, **kwargs))

    def add_round(self, round):
        self.rounds.append(round)

    def render(self, counter, template_vars):
        env = Environment(loader=FileSystemLoader('./templates/'))
        env.filters['numberfmt'] = lambda v: '{:,d}'.format(v)
        template = env.get_template('base.html')
        print(template.render(
            log=self.log,
            counter=counter,
            rounds=self.rounds,
            number_rounds=len(self.rounds),
            dt=datetime.datetime.now(),
            **template_vars))

