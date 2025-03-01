#!/usr/bin/env python
'''Add a set of modules to the list of static Python builtins.

Usage: python add_builtins.py [-s /path/to/script] [module_name] ...
'''
from modulefinder import ModuleFinder
import sys
import os
import os.path as op
import re
import shutil
import types
import importlib
from Cython.Build import cythonize
import Cython


# module definition lines in Modules/Setup look like this
module_def = re.compile('^[A-Za-z_\.]+ .+\.c')
# put extra builtins in here
extra_module_dir = op.join('Modules', 'extras')
if not op.exists(extra_module_dir):
    os.makedirs(extra_module_dir)
# file endings that can be compiled by cython
compileable_exts = ('.c', '.cpp', 'module.c', 'module.cpp')

# 使用 importlib.util.find_spec 替换 imp.find_module
def find_module(name, paths):
    spec = importlib.util.find_spec(name, paths)
    if spec is None or spec.origin is None:
        return None
    return spec.origin  # 返回模块路径

def add_builtins(names, script=None, exclude=None, path=None, auto_add_deps=False, src_dirs=None):
    if path is None:
        paths = ['lib'] + sys.path
    elif isinstance(path, str):
        paths = [path, 'lib'] + sys.path
    else:
        paths = path

    if src_dirs is None: src_dirs = {}

    # if called with a script, find their dependencies and re-run
    to_add = set(names)
    if script:
        module_dir = op.split(script)[0]
        paths = [module_dir] + paths
        finder = ModuleFinder(path=paths)
        finder.run_script(script)
        to_add.update(finder.modules.keys())
        return add_builtins(list(to_add), script=None, exclude=exclude, 
                             path=paths, auto_add_deps=False, src_dirs=None)
        
    if auto_add_deps:
        for name in names:
            try:
                module_path = find_module(name, paths)
            except KeyboardInterrupt: raise
            except: continue
            
            if module_path and module_path.endswith(('.py', '.pyc')):
                finder = ModuleFinder(path=paths)
                finder.run_script(module_path)
                to_add.update(finder.modules.keys())
                
        
    with open('Modules/Setup', 'r') as setup_file:
        lines = [str(x).rstrip('\n') for x in setup_file.readlines()]
    
    # don't add sys (it's already builtin) or anything explicitly excluded
    added = {'sys'}
    if exclude:
        added.update(exclude)
        
    
    # check each module to see if a commented line is present in Modules/Setup,
    # and uncomment
    for n, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        
        for name in to_add:
            if line.startswith('#%s ' % name):
                lines[n] = line.lstrip('#')
                to_add.remove(name)
                added.add(name)
                print('** Added %s' % name)
                break
                
        # keep track of uncommented module names in Modules/Setup
        if module_def.match(line):
            module_name = line.split()[0]
            pkg = False
            try: 
                module_path = find_module(module_name, paths)
                if module_path is None: pkg = True
            except: pkg = False
            
            if not pkg:
                added.add(module_name)
                print('** Found existing builtin %s' % module_name)
    
    # don't try to re-add existing builtins
    to_add = set.difference(to_add, added)
    
    for name in list(to_add):
        if name in added: continue
        
        new_lines = []
        
        try:
            module_path = find_module(name, paths)
        except ImportError:
            if '.' in name:
                module_path = None
            else: 
                raise Exception("** Couldn't find module %s" % name)
                continue
        
        # see if the target file already exists in Modules
        search_paths = [op.join(*(search_dir + (name+x,)))
                        for x in compileable_exts
                        for search_dir in (
                            (),
                            (name,),
                            ('extras', name),
                        )
                        if op.exists(op.join(*(('Modules',) + search_dir + (name+x,))))]
        
        if search_paths:
            module_file = search_paths[0]
            print('** Added %s' % module_file)
        else:
            # import the target module using this python installation,
            # and check the corresponding file
            
            if module_path is None:
                # add package
                pkg = name
                print("*** Scanning package %s..." % pkg)
                
                try:
                    p = importlib.import_module(pkg)
                except:
                    continue
                
                def get_submodules(x, yielded=None):
                    if not yielded: yielded = set()
                    yield x
                    yielded.add(x)
                    for member in dir(x):
                        member = getattr(x, member)
                        if isinstance(member, types.ModuleType) and member not in yielded:
                            for y in get_submodules(member, yielded):
                                yield y
                                yielded.add(y)
                
                submodules = get_submodules(p)
                
                for submodule in submodules:
                    name = submodule.__name__
                    
                    sys.stdout.write("** Adding module %s in package %s..." % (name, pkg))
                    sys.stdout.flush()
                    
                    try:
                        add = add_module(name, added, paths, src_dirs)
                        if add: new_lines += add
                    except Exception as e:
                        print(e)
                    
                    print('done.')
                
            else:
                # add standalone module
                sys.stdout.write('** Adding %s...' % name)
                sys.stdout.flush()
                
                try:
                    add = add_module(name, added, paths, src_dirs, module_path=module_path)
                    if add: new_lines += add
                except Exception as e:
                    print(e)
                
                print('done.')
        
        if new_lines: lines += new_lines
    
    with open('Modules/Setup', 'w') as setup_file:
        setup_file.write('\n'.join(lines))
        
        
def add_module(name, added, paths, src_dirs, module_path=None):
    if name in added: 
        return
    
    added.add(name)
    pkg = '.' in name
    opts = ''
    
    if not module_path: 
        try: 
            module_path = importlib.import_module(name).__file__
        except: 
            return
        
    # if it's a .pyc file, hope the original python source is right next to it!
    if module_path.endswith('.pyc'):
        if op.exists(module_path[:-1]):
            module_path = module_path[:-1]
        else:
            raise Exception('Lone .pyc file %s' % module_path)
        
    module_dir, module_file = op.split(module_path)
    
    # copy the file to the Modules/extras directory
    dest_dir = extra_module_dir
    if pkg:
        dest_dir = op.join(dest_dir, name.split('.')[0])
        if not op.exists(dest_dir): os.makedirs(dest_dir)
    
    # if it's a shared library, try to find the original C or C++ 
    # source file to compile into a static library; otherwise, 
    # there's nothing we can do here
    if module_file.endswith('.dll'):
        done = False
        module_dirs = []
        for k, v in src_dirs.items():
            # if user specified a src directory for this package,
            # include it in the module search path
            if name.startswith(k):
                module = name[len(k):].lstrip('.')
                if '.' in module:
                    v = op.join(v, *module.split('.'))
                module_dirs += [v]
        module_dirs += [module_dir]
        for search_dir in module_dirs + paths:
            for compiled_module in ('.'.join(module_file.split('.')[:-1]) + ext
                                     for ext in compileable_exts):
                if op.exists(op.join(search_dir, compiled_module)):
                    dest_file = compiled_module
                    if pkg:
                        dest_file = '__'.join(name.split('.')) + '.' + dest_file.split('.')[-1]
                    
                    dest_path = op.join(dest_dir, dest_file)
                    
                    if not op.exists(dest_path):
                        shutil.copy(op.join(search_dir, compiled_module), dest_path)
                    
                    module_dir = search_dir
                    module_file = dest_file
                    opts += ' -I%s' % op.abspath(search_dir)
                    done = True
                    break
            
            if done: break
        
        if not any([module_file.endswith(ext) for ext in compileable_exts]):
            return
            
        module_path = op.join(module_dir, module_file)
        
    else:
        # copy the file to the Modules/extras directory
        dest_file = module_file
        if pkg:
            dest_file = '__'.join(name.split('.')) + '.' + dest_file.split('.')[-1]
            
        dest_path = op.join(dest_dir, dest_file)
        opts = ''
        
        if not op.exists(dest_path) or op.getmtime(dest_path) < op.getmtime(module_path):
            print("** Copying %s to %s" % (module_path, dest_path))
            shutil.copy(module_path, dest_path)
        
        if not module_file.endswith('.py'):
            return
        
        # cythonize the target module to compile it
        dest_path = cythonize(dest_path, quiet=True)[0]
        dest_file = '.'.join(dest_file.split('.')[:-1]) + '.c'
        opts = ' -I%s' % Cython.__path__[0].split('Cython')[0]
        
    print("** Wrote %s" % dest_path)
    
    return ['%s %s' % (name, op.join(extra_module_dir, dest_file) + opts)]


if __name__ == '__main__':
    if '-s' in sys.argv:
        script = sys.argv[sys.argv.index('-s') + 1]
    else:
        script = None
    
    modules = [x for x in sys.argv[1:] if not x.startswith('-')]
    add_builtins(modules, script)
