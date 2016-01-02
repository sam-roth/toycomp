from toycomp import (parser,
                     nameres,
                     typechecker,
                     autorepr,
                     user_op_rewriter,
                     compilepass)

code = '''

def binary > 10 (lhs:double rhs:double) -> double
    rhs < lhs;

def foo(x:int y:double) -> double
    x > y
'''

tree = list(parser.parse(code))

pm = compilepass.PassManager([
    typechecker.Typechecker(),
    nameres.NameResolver(),
    user_op_rewriter.UserOpRewriter(),
])

for node in tree:
    pm.visit(node)

print(autorepr.yaml_dump_all(tree))
