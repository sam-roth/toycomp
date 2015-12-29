from toycomp import parser, nameres, typechecker, autorepr, user_op_rewriter

code = '''

def binary > 10 (lhs:double rhs:double) -> double
    rhs < lhs;

def foo(x:int y:double) -> double
    x > y
'''

tree = list(parser.parse(code))

ow = user_op_rewriter.UserOpRewriter()
nr = nameres.NameResolver()
tc = typechecker.Typechecker()

for pass_ in [ow, nr, tc]:
    for node in tree:
        pass_.handle_function(node)

print(autorepr.yaml_dump_all(tree))
