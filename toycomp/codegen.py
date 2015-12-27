from llvmlite import ir

from . import ast, color


class Codegen:
    def __init__(self):
        self.named_values = {}
        self.builder = ir.IRBuilder()
        self.module = ir.Module(name='my cool jit')

    def error_value(self, msg):
        print(color.color('magenta', 'Error: {}'.format(msg)))
        return None

    def expr(self, expr):
        if isinstance(expr, ast.NumberExpr):
            return ir.Constant(ir.DoubleType(), expr.value)
        elif isinstance(expr, ast.VariableExpr):
            try:
                value = self.named_values[expr.name]
            except KeyError:
                value = self.error_value('undeclared variable {!r}'.format(expr.name))

            return value
        elif isinstance(expr, ast.BinaryExpr):
            l = self.expr(expr.lhs)
            r = self.expr(expr.rhs)

            if not all([l, r]):
                return None

            op = expr.op
            b = self.builder

            if op == '+':
                return b.fadd(l, r, name='addtmp')
            elif op == '-':
                return b.fsub(l, r, name='subtmp')
            elif op == '*':
                return b.fmul(l, r, name='multmp')
            elif op == '<':
                l = b.fcmp_unordered('<', l, r, name='cmptmp')
                return b.uitofp(l, ir.DoubleType(), name='booltmp')
            else:
                return self.error_value('invalid binary operator {!r}'.format(op))
        elif isinstance(expr, ast.CallExpr):
            if not isinstance(expr.func, ast.VariableExpr):
                return self.error_value('function to be called must be identifier; got {!r}'.format(expr.func))
            callee = self.module.get_global(expr.func.name)
            if not callee:
                return self.error_value('undeclared function {!r}'.format(expr.func.name))

            if len(expr.args) != len(callee.args):
                return self.error_value('function {!r} with {} parameters received {} arguments'.format(
                    expr.func, len(callee.args), len(expr.args)
                ))

            argvals = [self.expr(a) for a in expr.args]

            return self.builder.call(callee, argvals, name='calltmp')
        else:
            raise RuntimeError('Unexpected expression type: {!r}'.format(expr))

    def stmt(self, stmt):
        if isinstance(stmt, ast.Prototype):
            doubles = [ir.DoubleType()] * len(stmt.args)
            fty = ir.FunctionType(ir.DoubleType(), doubles)
            f = ir.Function(self.module, fty, stmt.name)
            f.linkage = 'external'

            for name, arg in zip(stmt.args, f.args):
                arg.name = name

            return f
        elif isinstance(stmt, ast.Function):
            func = self.module.get_global(stmt.proto.name)

            if not func:
                func = self.stmt(stmt.proto)

            if not func:
                return None

            if func.basic_blocks:
                return self.error_value('function {!r} already defined'.format(stmt.proto.name))

            bb = func.append_basic_block(name='entry')
            self.builder.position_at_end(bb)

            self.named_values.clear()

            for arg in func.args:
                self.named_values[arg.name] = arg

            result = self.expr(stmt.body)

            if not result:
                func.basic_blocks.clear()
                return None

            self.builder.ret(result)

            return func
        else:
            raise RuntimeError('Unexpected statement type: {!r}'.format(stmt))
