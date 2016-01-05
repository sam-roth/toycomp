import bisect
from collections import namedtuple


class SourceFile:
    def __init__(self, source, name=None):
        self.name = name
        self.lines = source.splitlines(keepends=True)
        self._line_offsets = []

        offset = 0
        for line in self.lines:
            self._line_offsets.append(offset)
            offset += len(line)

    def offset_to_location(self, offset):
        linenum = bisect.bisect_right(self._line_offsets, offset) - 1
        if linenum < 0 or linenum >= len(self.lines):
            raise IndexError

        col = offset - self._line_offsets[linenum]

        return SourceLocation(self, linenum, col)


class SourceLocation(namedtuple('SourceLocation', ['file', 'line', 'column'])):
    pass


class SourceRange(namedtuple('SourceRange', ['begin', 'end'])):
    def __new__(cls, begin, end):
        assert isinstance(begin, SourceLocation)
        assert isinstance(end, SourceLocation)
        assert begin.file == end.file

        return super().__new__(cls, begin, end)

    def to_squiggly(self, indent='  '):
        (file, line1, col1), (_, line2, col2) = self
        res = []
        for linenum in range(line1, line2 + 1):
            line = file.lines[linenum]
            line_col1 = 0
            if linenum == line1:
                line_col1 = col1
            line_col2 = len(line)
            if linenum == line2:
                line_col2 = col2

            res.append(indent + line.rstrip())
            res.append(indent + (' ' * line_col1) + ('~' * (line_col2 - line_col1)))

        return '\n'.join(res)
