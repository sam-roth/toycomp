from llvmlite import ir

from . import ast, color


_builtin_ops = {'+', '-', '*', '<'}


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
            # Rewrite to function call if user-defined.
            if expr.op not in _builtin_ops:
                call = ast.CallExpr(ast.VariableExpr('binary' + expr.op), [expr.lhs, expr.rhs])
                return self.expr(call)

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
        elif isinstance(expr, ast.IfExpr):
            test_v = self.expr(expr.test)

            if not test_v:
                return None

            test_v = self.builder.fcmp_ordered('!=', test_v, ir.Constant(ir.DoubleType(), 0.0), name='ifcond')

            func = self.builder.block.parent

            assert isinstance(func, ir.Function)

            true_block = ir.Block(func, name='true')
            false_block = ir.Block(func, name='false')
            merge_block = ir.Block(func, name='endif')

            self.builder.cbranch(test_v, true_block, false_block)

            func.blocks.append(true_block)
            self.builder.position_at_end(true_block)
            true_v = self.expr(expr.true)
            if not true_v:
                return None
            self.builder.branch(merge_block)
            # Actual block can be changed by self.expr(...)
            true_block = self.builder.block

            func.blocks.append(false_block)
            self.builder.position_at_end(false_block)
            false_v = self.expr(expr.false)
            if not false_v:
                return None
            self.builder.branch(merge_block)
            false_block = self.builder.block

            func.blocks.append(merge_block)
            self.builder.position_at_end(merge_block)

            phi = self.builder.phi(ir.DoubleType(), name='iftmp')

            phi.add_incoming(true_v, true_block)
            phi.add_incoming(false_v, false_block)

            return phi
        elif isinstance(expr, ast.ForExpr):
            start_val = self.expr(expr.start)

            if not start_val:
                return None

            func = self.builder.block.parent
            pre_header_block = self.builder.block
            loop_block = func.append_basic_block('loop')

            self.builder.branch(loop_block)
            self.builder.position_at_end(loop_block)

            var = self.builder.phi(ir.DoubleType(), name=expr.name)
            var.add_incoming(start_val, pre_header_block)

            sentinel = object()
            old_val = self.named_values.get(expr.name, sentinel)
            try:
                self.named_values[expr.name] = var

                if not self.expr(expr.body):
                    return None

                step_val = self.expr(expr.step)
                if not step_val:
                    return None

                next_var = self.builder.fadd(var, step_val, name='nextvar')

                end_val = self.expr(expr.end)
                if not end_val:
                    return None

                end_val = self.builder.fcmp_ordered('!=', end_val, ir.Constant(ir.DoubleType(), 0.0), name='loopcond')

                end_block = func.append_basic_block('endfor')

                var.add_incoming(next_var, self.builder.block)
                self.builder.cbranch(end_val, loop_block, end_block)
                self.builder.position_at_end(end_block)
            finally:
                if old_val is not sentinel:
                    self.named_values[expr.name] = old_val

            return ir.Constant(ir.DoubleType(), 0.0)
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
