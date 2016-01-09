#include <stdio.h>
#include <stdbool.h>


double putchard(double x)
{
    fputc((char) x, stderr);
    return 0;
}


double putbool(bool x)
{
    fprintf(stderr, x ? "True" : "False");
    return 0;
}
