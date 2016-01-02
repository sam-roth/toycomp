import abc


class Pass(metaclass=abc.ABCMeta):
    dependencies = ()

    @abc.abstractmethod
    def visit(self, node):
        pass


def _order_topologically(passes):
    pass_for_class = {klass: pass_
                      for pass_ in passes
                      for klass in type(pass_).mro()
                      if issubclass(klass, Pass)}
    order = []
    visited = set()
    visiting = set()

    def visit(pass_):
        if pass_ in visited:
            return

        if pass_ in visiting:
            raise ValueError('cyclic pass dependency {!r}'.format(type(pass_).__name__))

        visiting.add(pass_)

        for dep in pass_.dependencies:
            if dep not in pass_for_class:
                raise ValueError('pass missing dependency {!r}'.format(dep.__name__))

            visit(pass_for_class[dep])

        visiting.remove(pass_)
        visited.add(pass_)
        order.append(pass_)

    for pass_ in passes:
        if not isinstance(pass_, Pass):
            raise TypeError('expected Pass instance, got {!r}'.format(type(pass_).__name__))
        visit(pass_)

    return order


class PassManager:
    def __init__(self, passes):
        self.passes = _order_topologically(passes)

    def visit(self, node):
        return all([pass_.visit(node) for pass_ in self.passes])
