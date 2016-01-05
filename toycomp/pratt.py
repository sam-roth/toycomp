import re

from toycomp.sourceloc import SourceRange


class Grammar:
    def __init__(self):
        self.tokens = {}
        self.tokenspec = []

    def token(self, regex):
        def acceptor(klass):
            name = klass.__name__
            self.tokens[name] = klass
            self.tokenspec.append((name, regex))
            return klass

        return acceptor


class BidirectionalIterator:
    def __init__(self, iterator):
        self.iterator = iter(iterator)
        self._prev = []
        self._i = 0
        self._sentinel = object()
        self.next()

    def current(self):
        if not self._prev:
            raise RuntimeError('Must call next() first.')
        elif self._prev[self._i - 1] is self._sentinel:
            raise StopIteration

        return self._prev[self._i - 1]

    def next(self):
        if self._prev and self._prev[self._i - 1] is self._sentinel:
            raise StopIteration

        if self._i < len(self._prev):
            result = self._prev[self._i]
        else:
            result = next(self.iterator, self._sentinel)
            self._prev.append(result)

        self._i += 1

        if result is self._sentinel:
            raise StopIteration

        return result

    def prev(self):
        if self._i == 0:
            raise StopIteration

        self._i -= 1

        return self.current()

    def peek(self):
        try:
            self.next()
        except StopIteration:
            res = self._sentinel
        else:
            res = self.current()

        return res


class Token:
    lbp = 0
    ignore = False

    def __init__(self, value):
        self.value = value
        self.lineno = None
        self.offset = None
        self.pos = None

    def __repr__(self):
        return '{}({!r})'.format(type(self).__name__, self.value)

    def unary(self, parser):
        parser.error('no null denotation for token {!r}'.format(self.value))

    def binary(self, parser, left):
        parser.error('no left denotation for token {!r}'.format(self.value))

    def __eq__(self, other):
        return isinstance(other, type(self)) and self.value == other.value


class EndToken(Token):
    pass


class Tokenizer:
    def __init__(self, grammar):
        spec = grammar.tokenspec + [
            ('SKIP', r'[ \t\n]+'),
            ('MISMATCH', r'.')
        ]

        self._spec = spec
        self._grammar = grammar
        self._regex = '|'.join('(?P<%s>%s)' % pair for pair in self._spec)

    def tokenize(self, text):
        line_num = 1
        line_start = 0
        offset = 0
        pos = 0

        for mo in re.finditer(self._regex, text, re.MULTILINE):
            kindname = mo.lastgroup
            value = mo.group(kindname)

            if kindname == 'SKIP':
                pass
            elif kindname == 'MISMATCH':
                raise RuntimeError('Unexpected token %r' % value)
            else:
                t = self._grammar.tokens[kindname](value)
                if not t.ignore:
                    pos = mo.start()
                    offset = pos - line_start
                    t.lineno = line_num
                    t.offset = offset
                    t.pos = pos
                    yield t

            value_lines = sum(1 for c in value if c == '\n')
            if value_lines != 0:
                line_num += value_lines
                line_start += max(i for (i, c) in enumerate(value) if c == '\n') + 1

        et = EndToken(None)
        et.lineno = line_num
        et.offset = offset
        et.pos = pos
        yield et


class Parser:
    def __init__(self, tokens, file=None):
        self.file = file
        self.token_stream = BidirectionalIterator(tokens)

    @property
    def pos(self):
        return self.token_stream.current().pos

    def _make_source_range(self, start_pos, end_pos):
        if self.file:
            return SourceRange(self.file.offset_to_location(start_pos),
                               self.file.offset_to_location(end_pos))

        return None

    def expression(self, rbp=0):
        start_pos = self.pos
        t = self.token_stream.current()
        self.token_stream.next()
        left = t.unary(self)
        end_pos = self.pos
        left.source_range = self._make_source_range(start_pos, end_pos)

        while rbp < self.token_stream.current().lbp:
            # start_pos = self.pos
            t = self.token_stream.current()
            self.token_stream.next()
            left = t.binary(self, left)
            end_pos = self.pos
            left.source_range = self._make_source_range(start_pos, end_pos)

        return left

    def take(self, tokenty):
        cur = self.token_stream.current()
        if isinstance(tokenty, type):
            if not isinstance(cur, tokenty):
                return None
        else:
            if tokenty != cur:
                return None

        self.token_stream.next()
        return cur

    def expect(self, tokenty):
        cur = self.token_stream.current()
        if isinstance(tokenty, type):
            if not isinstance(cur, tokenty):
                self.error('expected {!r}, got {!r}'.format(tokenty.__name__, cur))
        else:
            if tokenty != cur:
                self.error('expected {!r}, got {!r}'.format(tokenty, cur))

        self.token_stream.next()
        return cur

    def parse(self):
        while not isinstance(self.token_stream.current(), EndToken):
            yield self.expression()

    def error(self, msg):
        se = SyntaxError(msg)
        se.lineno = self.token_stream.current().lineno
        se.offset = self.token_stream.current().offset
        raise se
