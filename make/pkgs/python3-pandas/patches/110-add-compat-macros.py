#!/usr/bin/env python3
"""Insert NumPy compatibility macros into pandas meson.build.

Usage: 110-add-compat-macros.py <path/to/meson.build>

Inserts an add_project_arguments() block with -D macros for NumPy C API
functions that are missing in NumPy < 2.5.0 (PyDataType_TYPEOBJ, KIND, TYPE,
BYTEORDER, TYPENUM, _PyUFuncObject_GET_ITEM_DATA,
_PyDatetimeScalarObject_GetMetadata).
"""

import sys
import os

if len(sys.argv) != 2:
    print(f"Usage: {sys.argv[0]} <path/to/meson.build>", file=sys.stderr)
    sys.exit(1)

path = sys.argv[1]

if not os.path.exists(path):
    print(f"File not found: {path}", file=sys.stderr)
    sys.exit(1)

with open(path, 'r') as f:
    content = f.read()

# Pattern to find: the closing of the NPY_TARGET_VERSION C++ block
old = """    language: 'cpp',
)"""

compat_block = """    language: 'cpp',
)

# Compatibility macros for NumPy C API functions not available in NumPy < 2.5.0
# pandas 3.x Cython-generated code uses these functions; provide them as simple
# struct field accessors for older numpy versions.
add_project_arguments(
    '-DPyDataType_TYPEOBJ(descr)=((descr)->typeobj)',
    '-DPyDataType_KIND(descr)=((descr)->kind)',
    '-DPyDataType_TYPE(descr)=((descr)->type)',
    '-DPyDataType_BYTEORDER(descr)=((descr)->byteorder)',
    '-DPyDataType_TYPENUM(descr)=((descr)->type_num)',
    '-D_PyUFuncObject_GET_ITEM_DATA(ufunc)=(ufunc)',
    '-D_PyDatetimeScalarObject_GetMetadata(obj)=(((PyDatetimeScalarObject *)(obj))->obmeta)',
    language: 'c',
)"""

if old not in content:
    print("WARNING: pattern 'language: 'cpp',' not found in meson.build", file=sys.stderr)
    sys.exit(0)

content = content.replace(old, compat_block, 1)

with open(path, 'w') as f:
    f.write(content)

print(f"OK: compat macros inserted into {path}")
