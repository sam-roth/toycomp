import argparse

import sys

from toycomp import parser
from toycomp.codegen import Codegen
from toycomp.compilepass import PassManager
from toycomp.diagnostics import DiagnosticsEngine, DiagnosticPrinter
from toycomp.nameres import NameResolver
from toycomp.typechecker import Typechecker
from toycomp.user_op_rewriter import UserOpRewriter


class Driver:
    def __init__(self, triple):
        self._diags = DiagnosticsEngine(DiagnosticPrinter(sys.stderr))
        self._pm = PassManager([
            UserOpRewriter(),
            NameResolver(),
            Typechecker(self._diags),
        ])

        self._cg = Codegen()
        self._cg.module.triple = triple

    def run(self, source, *, name=None):
        try:
            exprs = list(parser.parse(source, name=name))
        except SyntaxError as exc:
            raise SystemExit(str(exc))

        ok = all([self._pm.visit(expr) for expr in exprs])
        if ok:
            ok = all([self._cg.visit(expr) for expr in exprs])

        if not ok:
            self._diags.consumer.finish()
            raise SystemExit(1)

        print(self._cg.module)


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('source', type=argparse.FileType('r'))
    ap.add_argument('--triple')

    args = ap.parse_args(args)

    driver = Driver(args.triple)
    driver.run(args.source.read(), name=args.source.name)


if __name__ == '__main__':
    main()
