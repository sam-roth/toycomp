import gnureadline as readline
import os
import ctypes
import faulthandler
import atexit

from toycomp import ast
from llvmlite import binding as llvm

from . import parser, pratt, codegen, color, nativelib


def create_execution_engine():
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    backing_mod = llvm.parse_assembly(nativelib.code)
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)
    return engine


def main_loop():
    faulthandler.enable()

    llvm.initialize()
    llvm.initialize_native_target()
    llvm.initialize_native_asmprinter()
    anon_count = 0

    cg = codegen.Codegen()
    tokenizer = pratt.Tokenizer(parser.grammar)
    tokens = []

    while True:
        if tokens:
            prompt = '   ... '
        else:
            prompt = 'ready> '

        try:
            line = input(prompt)
        except EOFError:
            print()
            break

        readline.redisplay()
        line_tokens = list(tokenizer.tokenize(line))

        tokens.extend(line_tokens[:-1])

        if (len(line_tokens) >= 2 and
                isinstance(line_tokens[-2], parser.OperatorToken) and
                line_tokens[-2].value == ';'):

            try:
                astval = list(pratt.Parser(tokens[:-1] + [pratt.EndToken(None)]).parse())
            except SyntaxError as exc:
                print(color.color('magenta', '{}:{}:{}'.format(exc.lineno, exc.offset, exc)))
            else:
                print(color.color('blue', repr(astval)))
                for stmt in astval:
                    if isinstance(stmt, ast.Stmt):
                        print(color.color('cyan', cg.stmt(stmt)))
                    elif isinstance(stmt, ast.Expr):
                        proto = ast.Prototype('__anon{}'.format(anon_count), [])
                        anon_count += 1
                        func = ast.Function(proto, stmt)
                        code = cg.stmt(func)
                        if code:
                            print(color.color('cyan', code))

                            engine = create_execution_engine()
                            engine.add_module(llvm.parse_assembly(str(cg.module)))
                            engine.finalize_object()

                            pfunc = engine.get_function_address(proto.name)

                            cfunc = ctypes.CFUNCTYPE(ctypes.c_double)(pfunc)

                            res = cfunc()
                            print('=>', color.color('green', res))
                    elif stmt is None:
                        pass
                    else:
                        raise RuntimeError('expected stmt or expr; got {!r}'.format(stmt))

            tokens.clear()


def main():
    histfile = os.path.join(os.path.expanduser('~'),
                            '.toycomp16_history')

    try:
        readline.read_history_file(histfile)
    except FileNotFoundError:
        pass

    readline.parse_and_bind('tab: complete')
    atexit.register(readline.write_history_file, histfile)

    main_loop()


if __name__ == "__main__":
    main()
