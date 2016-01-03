import argparse

from toycomp import parser
from toycomp.codegen import Codegen
from toycomp.compilepass import PassManager
from toycomp.nameres import NameResolver
from toycomp.typechecker import Typechecker
from toycomp.user_op_rewriter import UserOpRewriter


class Driver:
    def __init__(self, triple):
        self._pm = PassManager([
            UserOpRewriter(),
            NameResolver(),
            Typechecker(),
        ])

        self._cg = Codegen()
        self._cg.module.triple = triple

    def run(self, source):
        try:
            exprs = list(parser.parse(source))
        except SyntaxError as exc:
            raise SystemExit(str(exc))

        passes_ok = all([self._pm.visit(expr) for expr in exprs])
        cg_ok = all([self._cg.visit(expr) for expr in exprs])

        if not (passes_ok and cg_ok):
            raise SystemExit('compilation failed')

        print(self._cg.module)


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=argparse.FileType('r'))
    ap.add_argument('--triple')
    args = ap.parse_args(args)

    driver = Driver(args.triple)
    driver.run(args.source.read())


if __name__ == '__main__':
    main()
