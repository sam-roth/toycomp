from collections import namedtuple
from abc import ABCMeta


class Expr(metaclass=ABCMeta):
    pass


NumberExpr = namedtuple('NumberExpr', 'value')
VariableExpr = namedtuple('VariableExpr', 'name')
BinaryExpr = namedtuple('BinaryExpr', 'op lhs rhs')
CallExpr = namedtuple('CallExpr', 'func args')
IfExpr = namedtuple('IfExpr', 'test true false')
ForExpr = namedtuple('ForExpr', 'name start end step body')


for t in [NumberExpr, VariableExpr, BinaryExpr, CallExpr, IfExpr, ForExpr]:
    Expr.register(t)


class Stmt(metaclass=ABCMeta):
    pass


Prototype = namedtuple('Prototype', 'name args')
Function = namedtuple('Function', 'proto body')


for t in [Prototype, Function]:
    Stmt.register(t)
