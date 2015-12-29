from toycomp.pratt import Parser
from .pratt import Token, Grammar, Tokenizer
from . import ast

grammar = Grammar()


def _parse_proto(parser):
    name = parser.expect(IdentToken).value

    suffix = ''
    if name in ('unary', 'binary'):
        suffix = parser.expect(OperatorToken).value

    if name == 'binary':
        lbp = int(parser.expect(NumberToken).value)
        OperatorToken.op_lbp[suffix] = lbp

    parser.expect(LParenToken)

    params = []

    while isinstance(parser.token_stream.current(), IdentToken):
        arg_name = parser.token_stream.current().value
        parser.token_stream.next()

        if parser.take(OperatorToken(':')):
            typename = parser.expression()
        else:
            typename = None

        params.append(ast.FormalParamDecl(arg_name, typename))

    parser.expect(RParenToken)

    if parser.take(OperatorToken('->')):
        result_typename = parser.expression()
    else:
        result_typename = None

    return ast.Prototype(name + suffix, params, result_typename)


@grammar.token(r'\bdef\b')
class DefToken(Token):
    def unary(self, parser):
        proto = _parse_proto(parser)
        body = parser.expression()
        parser.take(OperatorToken(';'))

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


@grammar.token(r'\bfor\b')
class ForToken(Token):
    def unary(self, parser):
        name = parser.expect(IdentToken).value
        parser.expect(OperatorToken('='))

        start = parser.expression()
        parser.expect(CommaToken)

        end = parser.expression()

        if parser.take(CommaToken):
            step = parser.expression()
        else:
            step = ast.NumberExpr(1)

        parser.expect(IdentToken('in'))

        body = parser.expression()

        return ast.ForExpr(name, start, end, step, body)


@grammar.token(r'\blet\b')
class LetToken(Token):
    def unary(self, parser):
        name = parser.expect(IdentToken).value
        parser.expect(OperatorToken('='))
        init = parser.expression()
        parser.expect(IdentToken('in'))
        body = parser.expression()

        return ast.LetExpr(name, init, body)


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


@grammar.token(r'[^\s()a-zA-Z0-9_]+')
class OperatorToken(Token):
    op_lbp = {
        '=': 2,
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

    def unary(self, parser):
        # Emit function call
        return ast.CallExpr(ast.VariableExpr('unary' + self.value), [parser.expression()])


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
