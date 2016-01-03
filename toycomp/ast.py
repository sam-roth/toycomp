from abc import ABCMeta, abstractmethod

from toycomp import types
from toycomp.autorepr import autorepr


class Decl(metaclass=ABCMeta):
    name = None
    llvm_value = None
    decl_ty = None


@autorepr('name', 'ty')
class TypeDecl(Decl):
    def __init__(self, name, ty):
        self.name = name
        self.ty = ty


@autorepr()
class Undeclared(Decl):
    pass


class AST(metaclass=ABCMeta):
    ty = None


class Expr(AST, metaclass=ABCMeta):
    pass


@autorepr('value')
class NumberExpr(Expr):
    def __init__(self, value):
        self.value = value


@autorepr('name')
class VariableExpr(Expr):
    decl = None

    def __init__(self, name):
        self.name = name


@autorepr('op', 'lhs', 'rhs')
class BinaryExpr(Expr):
    def __init__(self, op, lhs, rhs):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs


@autorepr('func', 'args')
class CallExpr(Expr):
    def __init__(self, func, args):
        self.func = func
        self.args = args


@autorepr('test', 'true', 'false')
class IfExpr(Expr):
    def __init__(self, test, true, false):
        self.test = test
        self.true = true
        self.false = false


@autorepr('name', 'start', 'end', 'step', 'body')
class ForExpr(Expr, Decl):
    def __init__(self, name, start, end, step, body):
        self.name = name
        self.start = start
        self.end = end
        self.step = step
        self.body = body


@autorepr('name', 'init', 'body')
class LetExpr(Expr, Decl):
    def __init__(self, name, init, body):
        self.name = name
        self.init = init
        self.body = body


# noinspection PyPep8Naming
class ASTVisitor(metaclass=ABCMeta):
    @abstractmethod
    def visit_NumberExpr(self, expr):
        """:type expr: NumberExpr"""
        pass

    @abstractmethod
    def visit_VariableExpr(self, expr):
        pass

    @abstractmethod
    def visit_BinaryExpr(self, expr):
        pass

    @abstractmethod
    def visit_CallExpr(self, expr):
        pass

    @abstractmethod
    def visit_IfExpr(self, expr):
        pass

    @abstractmethod
    def visit_ForExpr(self, expr):
        pass

    @abstractmethod
    def visit_LetExpr(self, expr):
        pass

    @abstractmethod
    def visit_Prototype(self, stmt):
        pass

    @abstractmethod
    def visit_Function(self, stmt):
        pass

    @abstractmethod
    def visit_FormalParamDecl(self, decl):
        pass

    def visit(self, expr):
        type_name = type(expr).__name__
        method_name = 'visit_' + type_name
        return getattr(self, method_name)(expr)


class ASTRewriter(ASTVisitor):
    def visit_FormalParamDecl(self, decl):
        if decl.typename:
            decl.typename = self.visit(decl.typename)
        return decl

    def visit_Prototype(self, stmt):
        stmt.params = [self.visit(p) for p in stmt.params]
        if stmt.result_typename:
            stmt.result_typename = self.visit(stmt.result_typename)
        return stmt

    def visit_Function(self, stmt):
        stmt.proto = self.visit(stmt.proto)
        stmt.body = self.visit(stmt.body)
        return stmt

    def visit_VariableExpr(self, expr):
        return expr

    def visit_LetExpr(self, expr):
        expr.init = self.visit(expr.init)
        expr.body = self.visit(expr.body)
        return expr

    def visit_CallExpr(self, expr):
        expr.func = self.visit(expr.func)
        expr.args = [self.visit(a) for a in expr.args]
        return expr

    def visit_BinaryExpr(self, expr):
        expr.lhs = self.visit(expr.lhs)
        expr.rhs = self.visit(expr.rhs)
        return expr

    def visit_NumberExpr(self, expr):
        return expr

    def visit_IfExpr(self, expr):
        expr.test = self.visit(expr.test)
        expr.true = self.visit(expr.true)
        expr.false = self.visit(expr.false)
        return expr

    def visit_ForExpr(self, expr):
        expr.start = self.visit(expr.start)
        expr.end = self.visit(expr.end)
        expr.step = self.visit(expr.step)
        expr.body = self.visit(expr.body)
        return expr


class Stmt(metaclass=ABCMeta):
    pass


@autorepr('name', 'params', 'result_typename', 'decl_ty')
class Prototype(Stmt, Decl):
    def __init__(self, name, params, result_typename=None):
        self.name = name
        self.args = [p.name for p in params]  # legacy use only
        self.params = params
        self.result_typename = result_typename


@autorepr('name', 'typename', 'decl_ty')
class FormalParamDecl(Decl):
    def __init__(self, name, typename=None):
        self.name = name
        self.decl_ty = types.double_ty
        self.typename = typename


@autorepr('proto', 'body')
class Function(Stmt):
    def __init__(self, proto, body):
        self.proto = proto
        self.body = body
