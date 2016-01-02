from toycomp import parser, ast


def assert_parses(input, *output):
    assert repr(list(parser.parse(input))) == repr(list(output))


def test_parse_var():
    assert_parses('xyz', ast.VariableExpr('xyz'))


def test_parse_binop():
    assert_parses('x + y', ast.BinaryExpr('+', ast.VariableExpr('x'), ast.VariableExpr('y')))


def test_parse_prec():
    assert_parses('v * w < x + y * z',
                  ast.BinaryExpr('<',
                                 ast.BinaryExpr('*', ast.VariableExpr('v'), ast.VariableExpr('w')),
                                 ast.BinaryExpr('+',
                                                ast.VariableExpr('x'),
                                                ast.BinaryExpr('*',
                                                               ast.VariableExpr('y'),
                                                               ast.VariableExpr('z')))))


def test_parse_multi_def():
    assert_parses('def f() a + b; def g() c',
                  ast.Function(ast.Prototype('f', []),
                               ast.BinaryExpr('+', ast.VariableExpr('a'), ast.VariableExpr('b'))),
                  ast.Function(ast.Prototype('g', []), ast.VariableExpr('c')))


def test_parse_multi_extern():
    assert_parses('extern f(); extern g()',
                  ast.Prototype('f', []),
                  ast.Prototype('g', []))


def test_parse_for():
    assert_parses('for x = 0, x < 10, 1 in x',
                  ast.ForExpr('x',
                              ast.NumberExpr(0.0),
                              ast.BinaryExpr('<',
                                             ast.VariableExpr('x'),
                                             ast.NumberExpr(10.0)),
                              ast.NumberExpr(1.0),
                              ast.VariableExpr('x')))
