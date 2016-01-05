from toycomp import ast, compilepass


builtin_ops = {'+', '-', '*', '<', '='}


class UserOpRewriter(ast.ASTRewriter, compilepass.Pass):
    """
    This `ExprRewriter` rewrites `BinaryExprs` for user-defined operators into
    function calls for the typechecker's sake.
    """
    def visit_BinaryExpr(self, expr):
        if expr.op not in builtin_ops:
            return ast.CallExpr(ast.VariableExpr('binary{}'.format(expr.op)),
                                [self.visit(expr.lhs),
                                 self.visit(expr.rhs)])

        return super().visit_BinaryExpr(expr)

