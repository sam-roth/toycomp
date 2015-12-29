from . import types, color

from toycomp import ast


class Typechecker(ast.ExprVisitor):
    def __init__(self):
        pass

    def emit_error(self, msg, *, node=None):
        print(color.color('magenta', 'Error: ' + str(msg)))

    def handle_proto(self, proto):
        # Only doubles allowed for now
        ok = True
        for param in proto.params:
            if param.typename:
                if not isinstance(param.typename.decl, ast.TypeDecl):
                    ok = False
                    if not isinstance(param.typename.decl, ast.Undeclared):
                        self.emit_error('not a type name', node=param.typename)
                else:
                    param.decl_ty = param.typename.decl.ty
            else:
                param.decl_ty = types.double_ty

        result_typename = None
        if not proto.result_typename:
            result_typename = types.double_ty
        elif not proto.result_typename.decl:
            ok = False
        elif not isinstance(proto.result_typename.decl, ast.TypeDecl):
            ok = False
            self.emit_error('not a type name', node=proto.result_typename)
        else:
            result_typename = proto.result_typename.decl.ty

        proto.decl_ty = types.FunctionType(result_typename,
                                           [param.decl_ty for param in proto.params])

        return ok

    def handle_function(self, func):
        proto_ok = self.handle_proto(func.proto)
        body_ok = self.visit(func.body)

        return body_ok and proto_ok

    def visit_ForExpr(self, expr):
        start_ok = self.visit(expr.start)
        expr.decl_ty = expr.start.ty

        end_ok = self.visit(expr.end)
        step_ok = self.visit(expr.step)
        body_ok = self.visit(expr.body)

        return all([
            start_ok,
            end_ok,
            step_ok,
            body_ok
        ])

    def visit_VariableExpr(self, expr):
        if not expr.decl or not expr.decl.decl_ty:
            return False

        expr.ty = expr.decl.decl_ty
        return True

    def visit_BinaryExpr(self, expr):
        # TODO: Analyze this correctly. Must add decl
        # ptr to BinaryExpr for overloading.

        left_ok = self.visit(expr.lhs)
        right_ok = self.visit(expr.rhs)

        if expr.lhs.ty != expr.rhs.ty:
            self.emit_error('LHS and RHS of infix operator expression must have same type')
            return False

        expr.ty = expr.lhs.ty

        return all([left_ok, right_ok])

    def visit_LetExpr(self, expr):
        init_ok = self.visit(expr.init)
        expr.decl_ty = expr.init.ty
        body_ok = self.visit(expr.body)
        expr.ty = expr.body.ty

        return all([init_ok, body_ok])

    def visit_IfExpr(self, expr):
        test_ok = self.visit(expr.test)
        true_ok = self.visit(expr.true)
        false_ok = self.visit(expr.false)

        if expr.true.ty != expr.false.ty:
            self.emit_error('true and false branches of `if` must have same result type')
            return False

        expr.ty = expr.true.ty

        return all([test_ok, true_ok, false_ok])

    def visit_CallExpr(self, expr):
        func_ok = self.visit(expr.func)
        args_ok = all(self.visit(a) for a in expr.args)

        if not isinstance(expr.func.ty, types.FunctionType):
            self.emit_error('expression is not a function', node=expr.func)
            return False

        actuals_ok = True

        if len(expr.func.ty.params) != len(expr.args):
            self.emit_error(
                    'wrong number of arguments to function: expected {}, got {}.'.format(
                            len(expr.func.ty.params), len(expr.args)),
                    node=expr)
            actuals_ok = False

        for param_ty, arg in zip(expr.func.ty.params, expr.args):
            if param_ty != arg.ty:
                self.emit_error(
                        'parameter type does not match argument type: expected {}, got {}.'.format(
                                param_ty, arg.ty),
                        node=expr)
                actuals_ok = False

        expr.ty = expr.func.ty.result

        return func_ok and args_ok and actuals_ok

    def visit_NumberExpr(self, expr):
        expr.ty = types.double_ty
        return True
