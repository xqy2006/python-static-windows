/* Minimal main program -- everything is loaded from the library */

#include "Python.h"

#ifdef MS_WINDOWS
int
wmain(int argc, wchar_t **argv)
{
    //Py_SetPath(L"D:\Python-3.13\Python-3.13.0\Lib:");
    return Py_Main(argc, argv);
}
#else
int
main(int argc, char **argv)
{
    //Py_SetPath(L"D:\Python-3.13\Python-3.13.0\Lib:");
    return Py_BytesMain(argc, argv);
}
#endif
