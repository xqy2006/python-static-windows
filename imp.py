"""This module provides the components needed to build your own __import__
function.  Undocumented functions are obsolete.

In most cases it is preferred you consider using the importlib module's
functionality over this module.

"""
# (Probably) need to stay in _imp
from _imp import (lock_held, acquire_lock, release_lock,
                  get_frozen_object, is_frozen_package,
                  init_builtin, init_frozen, is_builtin, is_frozen,
                  _fix_co_filename)
try:
    from _imp import load_dynamic
except ImportError:
    # Platform doesn't support dynamic loading.
    load_dynamic = None

from importlib._bootstrap import SourcelessFileLoader, _ERR_MSG

from importlib import machinery
from importlib import util
import importlib
import os
import sys
import tokenize
import types
import warnings

warnings.warn("the imp module is deprecated in favour of importlib; "
              "see the module's documentation for alternative uses",
              PendingDeprecationWarning)

# DEPRECATED
SEARCH_ERROR = 0
PY_SOURCE = 1
PY_COMPILED = 2
C_EXTENSION = 3
PY_RESOURCE = 4
PKG_DIRECTORY = 5
C_BUILTIN = 6
PY_FROZEN = 7
PY_CODERESOURCE = 8
IMP_HOOK = 9


def new_module(name):
    """**DEPRECATED**

    Create a new module.

    The module is not entered into sys.modules.

    """
    return types.ModuleType(name)


def get_magic():
    """**DEPRECATED**

    Return the magic number for .pyc or .pyo files.
    """
    return util.MAGIC_NUMBER


def get_tag():
    """Return the magic tag for .pyc or .pyo files."""
    return sys.implementation.cache_tag


def cache_from_source(path, debug_override=None):
    """**DEPRECATED**

    Given the path to a .py file, return the path to its .pyc/.pyo file.

    The .py file does not need to exist; this simply returns the path to the
    .pyc/.pyo file calculated as if the .py file were imported.  The extension
    will be .pyc unless sys.flags.optimize is non-zero, then it will be .pyo.

    If debug_override is not None, then it must be a boolean and is used in
    place of sys.flags.optimize.

    If sys.implementation.cache_tag is None then NotImplementedError is raised.

    """
    return util.cache_from_source(path, debug_override)


def source_from_cache(path):
    """**DEPRECATED**

    Given the path to a .pyc./.pyo file, return the path to its .py file.

    The .pyc/.pyo file does not need to exist; this simply returns the path to
    the .py file calculated to correspond to the .pyc/.pyo file.  If path does
    not conform to PEP 3147 format, ValueError will be raised. If
    sys.implementation.cache_tag is None then NotImplementedError is raised.

    """
    return util.source_from_cache(path)


def get_suffixes():
    """**DEPRECATED**"""
    extensions = [(s, 'rb', C_EXTENSION) for s in machinery.EXTENSION_SUFFIXES]
    source = [(s, 'U', PY_SOURCE) for s in machinery.SOURCE_SUFFIXES]
    bytecode = [(s, 'rb', PY_COMPILED) for s in machinery.BYTECODE_SUFFIXES]

    return extensions + source + bytecode


class NullImporter:

    """**DEPRECATED**

    Null import object.

    """

    def __init__(self, path):
        if path == '':
            raise ImportError('empty pathname', path='')
        elif os.path.isdir(path):
            raise ImportError('existing directory', path=path)

    def find_module(self, fullname):
        """Always returns None."""
        return None


class _HackedGetData:

    """Compatibiilty support for 'file' arguments of various load_*()
    functions."""

    def __init__(self, fullname, path, file=None):
        super().__init__(fullname, path)
        self.file = file

    def get_data(self, path):
        """Gross hack to contort loader to deal w/ load_*()'s bad API."""
        if self.file and path == self.path:
            if not self.file.closed:
                file = self.file
            else:
                self.file = file = open(self.path, 'r')

            with file:
                # Technically should be returning bytes, but
                # SourceLoader.get_code() just passed what is returned to
                # compile() which can handle str. And converting to bytes would
                # require figuring out the encoding to decode to and
                # tokenize.detect_encoding() only accepts bytes.
                return file.read()
        else:
            return super().get_data(path)


class _LoadSourceCompatibility(_HackedGetData, machinery.SourceFileLoader):

    """Compatibility support for implementing load_source()."""


def load_source(name, pathname, file=None):
    _LoadSourceCompatibility(name, pathname, file).load_module(name)
    module = sys.modules[name]
    # To allow reloading to potentially work, use a non-hacked loader which
    # won't rely on a now-closed file object.
    module.__loader__ = machinery.SourceFileLoader(name, pathname)
    return module


class _LoadCompiledCompatibility(_HackedGetData, SourcelessFileLoader):

    """Compatibility support for implementing load_compiled()."""


def load_compiled(name, pathname, file=None):
    """**DEPRECATED**"""
    _LoadCompiledCompatibility(name, pathname, file).load_module(name)
    module = sys.modules[name]
    # To allow reloading to potentially work, use a non-hacked loader which
    # won't rely on a now-closed file object.
    module.__loader__ = SourcelessFileLoader(name, pathname)
    return module


def load_package(name, path):
    """**DEPRECATED**"""
    if os.path.isdir(path):
        extensions = (machinery.SOURCE_SUFFIXES[:] +
                      machinery.BYTECODE_SUFFIXES[:])
        for extension in extensions:
            path = os.path.join(path, '__init__'+extension)
            if os.path.exists(path):
                break
        else:
            raise ValueError('{!r} is not a package'.format(path))
    return machinery.SourceFileLoader(name, path).load_module(name)


def load_module(name, file, filename, details):
    """**DEPRECATED**

    Load a module, given information returned by find_module().

    The module name must include the full package name, if any.

    """
    suffix, mode, type_ = details
    if mode and (not mode.startswith(('r', 'U')) or '+' in mode):
        raise ValueError('invalid file open mode {!r}'.format(mode))
    elif file is None and type_ in {PY_SOURCE, PY_COMPILED}:
        msg = 'file object required for import (type code {})'.format(type_)
        raise ValueError(msg)
    elif type_ == PY_SOURCE:
        return load_source(name, filename, file)
    elif type_ == PY_COMPILED:
        return load_compiled(name, filename, file)
    elif type_ == C_EXTENSION and load_dynamic is not None:
        if file is None:
            with open(filename, 'rb') as opened_file:
                return load_dynamic(name, filename, opened_file)
        else:
            return load_dynamic(name, filename, file)
    elif type_ == PKG_DIRECTORY:
        return load_package(name, filename)
    elif type_ == C_BUILTIN:
        return init_builtin(name)
    elif type_ == PY_FROZEN:
        return init_frozen(name)
    else:
        msg =  "Don't know how to import {} (type code {})".format(name, type_)
        raise ImportError(msg, name=name)


def find_module(name, path=None):
    """**DEPRECATED**

    Search for a module.

    If path is omitted or None, search for a built-in, frozen or special
    module and continue search in sys.path. The module name cannot
    contain '.'; to search for a submodule of a package, pass the
    submodule name and the package's __path__.

    """
    if not isinstance(name, str):
        raise TypeError("'name' must be a str, not {}".format(type(name)))
    elif not isinstance(path, (type(None), list)):
        # Backwards-compatibility
        raise RuntimeError("'list' must be None or a list, "
                           "not {}".format(type(name)))

    if path is None:
        if is_builtin(name):
            return None, None, ('', '', C_BUILTIN)
        elif is_frozen(name):
            return None, None, ('', '', PY_FROZEN)
        else:
            path = sys.path

    for entry in path:
        package_directory = os.path.join(entry, name)
        for suffix in ['.py', machinery.BYTECODE_SUFFIXES[0]]:
            package_file_name = '__init__' + suffix
            file_path = os.path.join(package_directory, package_file_name)
            if os.path.isfile(file_path):
                return None, package_directory, ('', '', PKG_DIRECTORY)
        for suffix, mode, type_ in get_suffixes():
            file_name = name + suffix
            file_path = os.path.join(entry, file_name)
            if os.path.isfile(file_path):
                break
        else:
            continue
        break  # Break out of outer loop when breaking out of inner loop.
    else:
        raise ImportError(_ERR_MSG.format(name), name=name)

    encoding = None
    if mode == 'U':
        with open(file_path, 'rb') as file:
            encoding = tokenize.detect_encoding(file.readline)[0]
    file = open(file_path, mode, encoding=encoding)
    return file, file_path, (suffix, mode, type_)


def reload(module):
    """**DEPRECATED**

    Reload the module and return it.

    The module must have been successfully imported before.

    """
    return importlib.reload(module)