"""
Simple tests to see if codegen works without errors on valid inputs and fails on a selection of invalid inputs.

If these tests fail, codegen is broken, but if they pass, it does **not** mean that codegen actually works.
"""
import sys

import pytest
from llvmlite import ir
from toycomp import (
    codegen,
    compilepass,
    nameres,
    typechecker,
    user_op_rewriter,
    parser
)
from toycomp.diagnostics import DiagnosticsEngine, DiagnosticPrinter


@pytest.fixture
def passmgr():
    engine = DiagnosticsEngine(DiagnosticPrinter(sys.stderr))
    return compilepass.PassManager([
        nameres.NameResolver(engine),
        typechecker.Typechecker(engine),
        user_op_rewriter.UserOpRewriter(),
    ])


@pytest.fixture
def cg():
    return codegen.Codegen()


@pytest.fixture
def run_compiler(passmgr, cg):
    def result(src):
        exprs = list(parser.parse(src))

        passes_ok = all([passmgr.visit(expr) for expr in exprs])
        assert passes_ok

        return [cg.visit(expr) for expr in exprs]

    return result


@pytest.fixture
def assert_compiles(run_compiler):
    def result(src):
        assert all(run_compiler(src))

    return result


@pytest.fixture
def assert_does_not_compile(run_compiler):
    def result(src):
        try:
            res = run_compiler(src)
        except AssertionError:
            pass
        else:
            assert not all(res), 'compilation succeeded when not expected'

    return result


def test_codegen_proto(passmgr, cg):
    source = '''
    extern foo(bar:int) -> double
    '''

    [expr] = parser.parse(source)

    passes_ok = passmgr.visit(expr)
    assert passes_ok

    code = cg.visit(expr)
    assert code

    assert isinstance(code, ir.Function)
    assert not code.blocks
    assert len(code.args) == 1
    assert code.args[0].name == 'bar'
    assert code.function_type == ir.FunctionType(ir.DoubleType(), [ir.IntType(32)])


def parametrize_auto_id(argnames, argvalues):
    return pytest.mark.parametrize(
            argnames,
            argvalues,
            ids=[str(v) for v in argvalues]
    )


def test_codegen_function(assert_compiles):
    source = '''
    def foo(bar:int) -> int
        foo(bar)
    '''

    assert_compiles(source)


def test_fail_on_arg_type_mismatch(assert_does_not_compile):
    source = '''
    def foo(a:int) -> double
        0.0

    def bar(a:double) -> double
        foo(a)
    '''

    assert_does_not_compile(source)


def test_fail_on_ret_type_mismatch(assert_does_not_compile):
    source = '''
    def foo(a:int) -> double
        a
    '''

    assert_does_not_compile(source)


@parametrize_auto_id('expr',
                     ['bar()',
                      'bar',
                      'a && b'])
def test_fail_on_undeclared(expr, assert_does_not_compile):
    source = '''
    def foo(a:double b:double) -> double
        {}
    '''.format(expr)

    print(source)

    assert_does_not_compile(source)


def test_if(assert_compiles):
    source = '''
    def test_if(x:double) -> double
        if x == 0
            then 1
            else 0
    '''

    assert_compiles(source)


def test_let(assert_compiles):
    source = '''
    def test_let() -> double
        let x = 1 in
            x
    '''

    assert_compiles(source)


def test_for(assert_compiles):
    source = '''
    extern do_something_with(i:double) -> double

    def test_for() -> double
        for i = 0, i < 10, 1 in
            do_something_with(i)
    '''

    assert_compiles(source)
