#include "Python.h"
static PyMethodDef nomethods[] = {  {NULL, NULL}};
extern void inittest_module1();
extern void inittest_package1();
extern void inittest_package1_submodule();
 
PyMODINIT_FUNC
inittest(){
    PyObject* module;
    PyObject* __path__;
 
    // Add a __path__ attribute so Python knows that this is a package
    PyObject* package_gilbert = PyImport_AddModule("test1");
    Py_InitModule("test1", nomethods);
    __path__ = PyList_New(1);
    PyList_SetItem(__path__, 0, PyString_FromString("test1"));
    PyModule_AddObject(package_test, "__path__", __path__);
 
    PyImport_AppendInittab("test1.package1", inittest_package1);
    PyImport_AppendInittab("test1.package1.submodule", inittest_package1_submodule);
    }