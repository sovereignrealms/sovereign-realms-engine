#ifndef PY_COMPAT_H
#define PY_COMPAT_H

#ifndef PY_SSIZE_T_CLEAN
#define PY_SSIZE_T_CLEAN
#endif

#include <Python.h>

#if PY_MAJOR_VERSION >= 3

static inline int PF_PyString_Check(PyObject *obj)
{
    return PyUnicode_Check(obj) || PyBytes_Check(obj);
}

static inline char *PF_PyString_AsString(PyObject *obj)
{
    if(PyUnicode_Check(obj)) {
        return (char*)PyUnicode_AsUTF8(obj);
    }
    if(PyBytes_Check(obj)) {
        return PyBytes_AsString(obj);
    }
    PyErr_SetString(PyExc_TypeError, "Expected str or bytes object.");
    return NULL;
}

static inline Py_ssize_t PF_PyString_Size(PyObject *obj)
{
    if(PyUnicode_Check(obj)) {
        Py_ssize_t size = 0;
        if(!PyUnicode_AsUTF8AndSize(obj, &size))
            return -1;
        return size;
    }
    if(PyBytes_Check(obj))
        return PyBytes_GET_SIZE(obj);

    PyErr_SetString(PyExc_TypeError, "Expected str or bytes object.");
    return -1;
}

static inline PyObject *PF_PyString_FromString(const char *str)
{
    return PyUnicode_FromString(str);
}

static inline PyObject *PF_PyString_FromStringAndSize(const char *str, Py_ssize_t size)
{
    return PyBytes_FromStringAndSize(str, size);
}

#define PyString_Check              PF_PyString_Check
#define PyString_AsString           PF_PyString_AsString
#define PyString_AS_STRING          PF_PyString_AsString
#define PyString_Size               PF_PyString_Size
#define PyString_GET_SIZE           PF_PyString_Size
#define PyString_FromString         PF_PyString_FromString
#define PyString_FromStringAndSize  PF_PyString_FromStringAndSize
#define PyString_FromFormat         PyUnicode_FromFormat
#define PyString_InternFromString   PyUnicode_InternFromString
#define PyString_Type               PyUnicode_Type
#define _PyString_Resize            _PyBytes_Resize

#define PyInt_Check                 PyLong_Check
#define PyInt_FromLong              PyLong_FromLong
#define PyInt_AsLong                PyLong_AsLong
#define PyInt_AS_LONG               PyLong_AsLong
#define PyInt_FromSsize_t           PyLong_FromSsize_t
#define PyInt_AsSsize_t             PyLong_AsSsize_t
#define PyInt_Type                  PyLong_Type

#endif

#endif
