#include "Python.h"

static struct _inittab extensions[] = {
        /* Sentinel */
        {0, 0}
};
extern DL_IMPORT(int) PyImport_ExtendInittab(struct _inittab *newtab);

int PyInitFrozenExtensions()
{
        return PyImport_ExtendInittab(extensions);
}

