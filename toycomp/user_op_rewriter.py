from toycomp import ast, codegen


class UserOpRewriter(ast.ExprRewriter):
    """
    This `ExprRewriter` rewrites `BinaryExprs` for user-defined operators into
    function calls for the typechecker's sake.
    """
    def visit_BinaryExpr(self, expr):
        if expr.op not in codegen.builtin_ops:
            return ast.CallExpr(ast.VariableExpr('binary{}'.format(expr.op)),
                                [expr.lhs, expr.rhs])

        return expr

    def handle_function(self, func):
        func.body = self.visit(func.body)

