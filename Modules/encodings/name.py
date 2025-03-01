import os

def list_c_files():
    # 当前文件夹名字
    folder_name = os.path.basename(os.getcwd())
    
    # 生成当前目录下所有的 .c 文件路径
    c_files = [f for f in os.listdir('.') if f.endswith('.c')]
    
    # 格式化输出
    output = f"{folder_name} " + " ".join([f"{folder_name}/{file}" for file in c_files])
    
    print(output)

if __name__ == "__main__":
    list_c_files()
