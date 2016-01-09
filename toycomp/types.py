from llvmlite import ir
from toycomp import autorepr


@autorepr.autorepr('name')
class PrimitiveType:
    def __init__(self, name, llvm_ty):
        self.name = name
        self.llvm_ty = llvm_ty

    def __str__(self):
        return self.name

    def __repr__(self):
        return '<PrimitiveType {!r}>'.format(self.name)


@autorepr.autorepr('result', 'params')
class FunctionType:
    def __init__(self, result, params):
        self.result = result
        self.params = params

    def __str__(self):
        return '({}) -> {}'.format(', '.join(map(str, self.params)), self.result)

    def __repr__(self):
        return 'FunctionType({!r}, {!r})'.format(self.result, self.params)

    @property
    def llvm_ty(self):
        return ir.FunctionType(self.result.llvm_ty,
                               [t.llvm_ty for t in self.params])


double_ty = PrimitiveType('double', ir.DoubleType())
int_ty = PrimitiveType('int', ir.IntType(32))
bool_ty = PrimitiveType('bool', ir.IntType(1))
