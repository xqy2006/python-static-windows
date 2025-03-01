import os
from pathlib import Path

def get_submodule_names(parent_module_dir):
    """遍历父模块目录，找到所有的子模块（.py文件）。"""
    submodule_names = []
    parent_dir = Path(parent_module_dir)

    # 遍历目录下的所有 .py 文件，排除 __init__.py
    for py_file in parent_dir.glob('*.py'):
        if py_file.stem != '__init__':
            submodule_names.append(py_file.stem)  # 获取子模块名称（不含后缀）

    return submodule_names

def generate_init_code(parent_module, submodules):
    """根据父模块和子模块生成 C 代码的初始化函数。"""
    # 生成 C 代码的初始化模板
    init_code = f"""
PyMODINIT_FUNC
PyInit_{parent_module}(void) {{
    PyObject *module = PyModule_Create(&{parent_module}_definition);

    if (module == NULL) {{
        return NULL;
    }}
    """

    # 为每个子模块生成初始化和添加的代码
    for submodule in submodules:
        init_code += f"""
    // Initialize submodule {submodule}
    PyObject *{submodule} = PyInit_{submodule}();
    if (!{submodule}) {{
        Py_DECREF(module);
        return NULL;
    }}
    PyModule_AddObject(module, "{submodule}", {submodule});
        """
    
    # 结束初始化代码
    init_code += """
    return module;
}
    """
    
    return init_code

# 示例用法
if __name__ == "__main__":
    parent_module_dir = "D:\Python-3.13.0\Lib\encodings"  # 父模块的目录路径
    parent_module = os.path.basename(parent_module_dir)  # 父模块名称
    
    # 获取子模块名称列表
    submodules = get_submodule_names(parent_module_dir)

    # 检查是否找到了子模块
    if submodules:
        # 生成并打印 C 代码
        c_code = generate_init_code(parent_module, submodules)
        print(c_code)
        for submodule in submodules:
            print(f"extern PyObject* PyInit_{submodule}(void);")
    else:
        print(f"No submodules found in {parent_module_dir}")
