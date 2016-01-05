#include <stdio.h>


double putchard(double x)
{
    fputc((char) x, stderr);
    return 0;
}
