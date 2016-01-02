import collections
from contextlib import contextmanager

from toycomp import color
from . import ast, types


class NameResolver(ast.ASTVisitor):
    def __init__(self):
        self.globals = {
            'double': ast.TypeDecl('double', types.double_ty),
            'int': ast.TypeDecl('int', types.int_ty),
        }
        self.scope = collections.ChainMap(self.globals)

    def visit_FormalParamDecl(self, decl):
        return self.declare(decl)

    def visit_Prototype(self, stmt):
        return self.declare(stmt)

    def emit_error(self, msg, *, node=None):
        print(color.color('magenta', 'Error: ' + str(msg)))

    def declare(self, decl):
        """
        :type decl: ast.Decl
        """

        if decl.name in self.scope.maps[0] and self.scope[decl.name] is not decl:
            self.emit_error('redeclaration of {!r} in same scope'.format(decl.name), node=decl)
            return False

        self.scope[decl.name] = decl
        return True

    def visit_Function(self, func):
        """
        :type func: ast.Function
        """
        decl_ok = self.visit(func.proto)

        with self.new_scope():
            param_ok = all([self.visit(param) for param in func.proto.params])
            param_tys_ok = all([self.visit(param.typename)
                                for param in func.proto.params
                                if param.typename])
            body_ok = self.visit(func.body)

            return all([decl_ok, param_ok, param_tys_ok, body_ok])

    @contextmanager
    def new_scope(self):
        old_scope = self.scope
        try:
            self.scope = self.scope.new_child()
            yield
        finally:
            self.scope = old_scope

    def visit_IfExpr(self, expr):
        return all([
            self.visit(expr.test),
            self.visit(expr.true),
            self.visit(expr.false)
        ])

    def visit_ForExpr(self, expr):
        start_ok = self.visit(expr.start)
        with self.new_scope():
            self.declare(expr)
            return all([
                start_ok,
                self.visit(expr.end),
                self.visit(expr.step),
                self.visit(expr.body)
            ])

    def visit_LetExpr(self, expr):
        init_ok = self.visit(expr.init)
        with self.new_scope():
            self.declare(expr)
            return all([
                init_ok,
                self.visit(expr.body)
            ])

    def visit_BinaryExpr(self, expr):
        return all([
            self.visit(expr.lhs),
            self.visit(expr.rhs)
        ])

    def visit_NumberExpr(self, expr):
        return True

    def visit_VariableExpr(self, expr):
        try:
            decl = self.scope[expr.name]
        except KeyError:
            expr.decl = ast.Undeclared()
            self.emit_error('undeclared symbol {!r}'.format(expr.name), node=expr)
            return False

        expr.decl = decl
        return True

    def visit_CallExpr(self, expr):
        return all([
            self.visit(expr.func),
            all([self.visit(a) for a in expr.args])
        ])
