colors = dict(
        black=0,
        red=1,
        green=2,
        yellow=3,
        blue=4,
        magenta=5,
        cyan=6,
        white=7
)


def color(c, s):
    return '\033[{}m{}\033[0m'.format(30 + colors[c], s)

