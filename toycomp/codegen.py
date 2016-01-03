from llvmlite import ir

from . import ast, color

builtin_ops = {'+', '-', '*', '<'}


def _llvm_ty(ty):
    if ty is None:
        return None
    return ty.llvm_ty


class Codegen(ast.ASTVisitor):
    def __init__(self):
        self.decl_consts = {}
        self.decl_values = {}
        self.builder = ir.IRBuilder()
        self.module = ir.Module(name='main_module')

    def emit_error(self, msg, *, node=None):
        print(color.color('magenta', 'Error: {}'.format(msg)))

    def add_alloca(self, name, ty):
        if ty is None:
            return None

        with self.builder.goto_entry_block():
            return self.builder.alloca(ty, name=name)

    def visit_ForExpr(self, expr):
        start_val = self.visit(expr.start)
        alloca = self.add_alloca(expr.name, _llvm_ty(expr.decl_ty))
        ok = True

        if alloca and start_val:
            self.builder.store(start_val, alloca)
        else:
            ok = False
        self.decl_values[expr] = alloca

        # generate loop
        for_block = self.builder.append_basic_block('for')
        exit_block = ir.Block(self.builder.function, name='for.exit')

        self.builder.branch(for_block)
        self.builder.position_at_end(for_block)

        # generate loop test
        end_val = self.visit(expr.end)
        if end_val:
            end_val_bool = self.builder.fcmp_ordered('==',
                                                     end_val,
                                                     ir.Constant(ir.DoubleType(), 0.0))
        else:
            end_val_bool = ir.Constant(ir.IntType(1), 0)
            ok = False

        with self.builder.if_then(end_val_bool):
            self.builder.branch(exit_block)

        # generate loop body
        if not self.visit(expr.body):
            ok = False

        # generate increment
        if alloca:
            indvar_val = self.builder.load(alloca)
            new_indvar_val = self.builder.fadd(indvar_val,
                                               ir.Constant(ir.DoubleType(), 1.0),
                                               expr.name)
            self.builder.store(new_indvar_val, alloca)

        # branch to loop entry
        self.builder.branch(for_block)

        self.builder.function.blocks.append(exit_block)
        self.builder.position_at_end(exit_block)

        if not ok:
            return None

        return ir.Constant(ir.DoubleType(), 0.0)

    def visit_NumberExpr(self, expr):
        return ir.Constant(_llvm_ty(expr.ty), expr.value)

    def visit_IfExpr(self, expr):
        test_val = self.visit(expr.test)

        if not test_val:
            return None

        test_val = self.builder.fcmp_ordered('!=',
                                             test_val,
                                             ir.Constant(ir.DoubleType(), 0.0),
                                             name='ifcond')

        with self.builder.if_else(test_val) as (then, else_):
            with then:
                true_val = self.visit(expr.true)
                true_block = self.builder.block

            with else_:
                false_val = self.visit(expr.false)
                false_block = self.builder.block

        phi = self.builder.phi(expr.ty.llvm_ty, name='iftmp')
        phi.add_incoming(true_val, true_block)
        phi.add_incoming(false_val, false_block)

        return phi

    def visit_Function(self, stmt):
        func = self.module.get_global(stmt.proto.name)

        if not func:
            func = self.visit(stmt.proto)

        if not func:
            return None

        if func.basic_blocks:
            self.emit_error('function {!r} already defined'.format(stmt.proto.name),
                            node=stmt.proto)
            return None

        # The entry basic block just holds alloca instructions. The IRBuilder
        # in the llvmlite LLVM bindings doesn't support restoring its position
        # after a jump to the end of a basic block.
        entry = func.append_basic_block(name='entry')
        bb = func.append_basic_block(name='prologue')

        self.builder.position_at_end(entry)
        self.builder.branch(bb)
        self.builder.position_at_end(bb)

        for arg, param in zip(func.args, stmt.proto.params):
            alloca = self.add_alloca(arg.name, arg.type)
            self.builder.store(arg, alloca)
            self.decl_values[param] = alloca

        result = self.visit(stmt.body)

        if not result:
            func.basic_blocks.clear()
            return None

        self.builder.ret(result)

        return func

    def visit_CallExpr(self, expr):
        callee = self.visit(expr.func)
        if not callee:
            return None

        arg_vals = [self.visit(a) for a in expr.args]
        if not all(arg_vals):
            return None

        return self.builder.call(callee, arg_vals, name='calltmp')

    def visit_Prototype(self, stmt):
        fty = stmt.decl_ty.llvm_ty

        f = ir.Function(self.module, fty, stmt.name)
        f.linkage = 'external'

        for param, llvm_arg in zip(stmt.params, f.args):
            llvm_arg.name = param.name

        self.decl_consts[stmt] = f

        return f

    def visit_LetExpr(self, expr):
        alloca = self.add_alloca(expr.name, expr.decl_ty.llvm_ty)
        init_val = self.visit(expr.init)
        self.builder.store(init_val, alloca)
        self.decl_values[expr] = alloca

        body_val = self.visit(expr.body)
        return body_val

    def visit_BinaryExpr(self, expr):
        # Special-case '=': Don't emit LHS as an expression.
        if expr.op == '=':
            if not isinstance(expr.lhs, ast.VariableExpr):
                self.emit_error('target of assignment must be a variable name', node=expr)
                return None

            rhs_val = self.visit(expr.rhs)
            if not rhs_val:
                return None

            var = self.decl_values.get(expr.lhs.decl)
            if not var:
                return None

            self.builder.store(rhs_val, var)

            return rhs_val

        l = self.visit(expr.lhs)
        r = self.visit(expr.rhs)

        if not (l and r):
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
            self.emit_error('invalid binary operator {!r}'.format(op), node=expr)
            return None

    def visit_VariableExpr(self, expr):
        ptr = self.decl_values.get(expr.decl)
        if ptr:
            return self.builder.load(ptr, name=expr.name)

        return self.decl_consts.get(expr.decl)

    def visit_FormalParamDecl(self, decl):
        # Not used.
        raise NotImplementedError
