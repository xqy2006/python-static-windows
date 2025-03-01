import os
import re

def scan_frozen_modules(frozen_dir):
    modules = []
    pattern = re.compile(r'^M_([a-zA-Z_][\w_]*)\.c$')
    
    for filename in os.listdir(frozen_dir):
        match = pattern.match(filename)
        if not match:
            continue
        
        # 转换文件名到模块名（处理嵌套模块）
        modname = match.group(1).replace('__', '.').replace('_', '.')
        
        # 特殊处理_pyrepl等双下划线开头的模块
        if modname.startswith('_'):
            modname = modname.replace('._', '__', 1)
        
        modules.append(modname)
    
    return sorted(modules, key=lambda x: (x.count('.'), x))

if __name__ == '__main__':
    frozen_dir = os.path.join("D:\\Python-3.13.0", 'frozen_modules')
    modules = scan_frozen_modules(frozen_dir)
    
    with open('frozen_auto.cfg', 'w') as f:
        for mod in modules:
            f.write(f"{mod}\n")