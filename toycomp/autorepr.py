import yaml


def autorepr(*fields):
    def acceptor(klass):
        def __repr__(self):
            args = ', '.join('{}={!r}'.format(f, getattr(self, f))
                             for f in fields)
            return '{}({})'.format(type(self).__name__,
                                   args)

        klass.__repr__ = __repr__

        def representer(dumper, data):
            return dumper.represent_mapping('!{}'.format(klass.__name__),
                                            {f: getattr(data, f) for f in fields})

        yaml.add_representer(klass, representer)

        return klass

    return acceptor


class NoAliasDumper(yaml.Dumper):
    """
    Dumps YAML without annoying ``&idXYZ`` and ``*idXYZ``.
    """
    def ignore_aliases(self, data):
        return True


def yaml_dump(*args, **kwargs):
    kwargs.setdefault('Dumper', NoAliasDumper)
    return yaml.dump(*args, **kwargs)


def yaml_dump_all(*args, **kwargs):
    kwargs.setdefault('Dumper', NoAliasDumper)
    return yaml.dump_all(*args, **kwargs)
