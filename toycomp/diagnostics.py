import collections
import enum

from toycomp import color
from toycomp.translation import *


class DiagnosticSeverity(enum.Enum):
    error = 0


class Diagnostic:
    def __init__(self, severity, node, message):
        self.severity = DiagnosticSeverity(severity)
        self.node = node
        self.message = message


class DiagnosticConsumer:
    def __init__(self):
        self.message_count = collections.defaultdict(lambda: 0)

    def handle_diagnostic(self, diag):
        self.message_count[diag.severity] += 1

    def finish(self):
        pass


class DiagnosticPrinter(DiagnosticConsumer):
    def __init__(self, stream):
        super().__init__()
        self.stream = stream

    def handle_diagnostic(self, diag):
        super().handle_diagnostic(diag)

        if diag.node and diag.node.source_range:
            file, line, col = diag.node.source_range.begin
            pos_str = '{}:{}:{}: '.format(file.name, line + 1, col)
            squiggly = diag.node.source_range.to_squiggly()
        else:
            pos_str = ''
            squiggly = ''

        header = '{}{} {}'.format(pos_str, color.color('magenta', diag.severity.name + ':'), diag.message)
        print(header, file=self.stream)
        if squiggly:
            print(color.color('green', squiggly),
                  file=self.stream)

    def finish(self):
        super().finish()

        if self.message_count[DiagnosticSeverity.error]:
            count = self.message_count[DiagnosticSeverity.error]
            print(ntr('{} error generated.', '{} errors generated.', count).format(count),
                  file=self.stream)


class DiagnosticsEngine:
    def __init__(self, consumer):
        self.consumer = consumer

    def emit(self, diag):
        self.consumer.handle_diagnostic(diag)

    def error(self, node, message):
        self.emit(Diagnostic(DiagnosticSeverity.error,
                             node,
                             message))
