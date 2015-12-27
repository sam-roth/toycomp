from toycomp.pratt import Parser
from .pratt import Token, Grammar, Tokenizer
from . import ast

grammar = Grammar()


def _parse_proto(parser):
    name = parser.expect(IdentToken).value

    parser.expect(LParenToken)

    args = []
    while isinstance(parser.token_stream.current(), IdentToken):
        args.append(parser.token_stream.current().value)
        parser.token_stream.next()

    parser.expect(RParenToken)

    return ast.Prototype(name, args)


@grammar.token(r'\bdef\b')
class DefToken(Token):
    def unary(self, parser):
        proto = _parse_proto(parser)
        body = parser.expression(rbp=1)

        return ast.Function(proto, body)


@grammar.token(r'\bextern\b')
class ExternToken(Token):
    def unary(self, parser):
        return _parse_proto(parser)


@grammar.token(r'\bthen\b')
class ThenToken(Token):
    pass


@grammar.token(r'\belse\b')
class ElseToken(Token):
    pass


@grammar.token(r'\bif\b')
class IfToken(Token):
    def unary(self, parser):
        test = parser.expression()
        parser.expect(ThenToken)
        true_block = parser.expression()
        parser.expect(ElseToken)
        false_block = parser.expression()

        return ast.IfExpr(test, true_block, false_block)


@grammar.token(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b')
class IdentToken(Token):
    def unary(self, parser):
        return ast.VariableExpr(self.value)


@grammar.token(r'[0-9]*\.[0-9]+|[0-9]+(?:\.[0-9]*)?')
class NumberToken(Token):
    def unary(self, parser):
        return ast.NumberExpr(float(self.value))


@grammar.token(r'#.*$')
class CommentToken(Token):
    ignore = True


@grammar.token(r'\(')
class LParenToken(Token):
    lbp = 100

    def unary(self, parser):
        expr = parser.expression()
        parser.expect(RParenToken)
        return expr

    def binary(self, parser, left):
        args = []
        while not isinstance(parser.token_stream.current(), RParenToken):
            args.append(parser.expression())
            if isinstance(parser.token_stream.current(), CommaToken):
                parser.token_stream.next()

        parser.expect(RParenToken)

        return ast.CallExpr(left, args)


@grammar.token(r'\)')
class RParenToken(Token):
    pass


@grammar.token(r',')
class CommaToken(Token):
    pass


@grammar.token(r'[^\s]')
class OperatorToken(Token):
    op_lbp = {
        '<': 10,
        '+': 20,
        '-': 20,
        '*': 40,
    }

    @property
    def lbp(self):
        return self.op_lbp.get(self.value, 0)

    def binary(self, parser, left):
        return ast.BinaryExpr(self.value, left, parser.expression(self.lbp))


def parse(program):
    t = Tokenizer(grammar)
    return Parser(t.tokenize(program)).parse()


if __name__ == '__main__':
    t = Tokenizer(grammar)
    print(list(t.tokenize('def foo 123.456 # abcdjd\n'
                          '.456 0.1 1212 .1')))

    p = Parser(t.tokenize('123.456 * abc + 789 * efg'))
    print(p.expression())

    p = Parser(t.tokenize('def foo() 123.456 * abc + 789 * efg def bar() 0'))
    print(list(p.parse()))
