#define Py_BUILD_CORE
#include "Python.h"
#include "import.h"

static struct _inittab extensions[] = {
        /* Sentinel */
        {0, 0}
};
PyAPI_FUNC(int) PyImport_ExtendInittab(struct _inittab* newtab);

PyMODINIT_FUNC PyInitFrozenExtensions(void)
{
    return PyImport_ExtendInittab(extensions);
}

