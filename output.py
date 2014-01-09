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

class HtmlOutput:
    def __init__(self):
        self.log = []

    def log_line(self, *args, **kwargs):
        self.log.append(LogLine(*args, **kwargs))

    def render(self, counter, template_vars):
        env = Environment(loader=FileSystemLoader('./templates/'))
        template = env.get_template('base.html')
        print(template.render(
            log=self.log,
            counter=counter,
            dt=datetime.datetime.now(),
            **template_vars))

