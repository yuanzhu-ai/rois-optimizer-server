import datetime
import os
import sys

# 版本信息
VERSION = "1.0.0"

# 读取 git.properties 文件
GIT_COMMIT_ID = "unknown"
COMMIT_AUTHOR = "unknown"
BUILD_TIMESTAMP = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def resource_path(relative_path):
    """获取资源的绝对路径，支持 PyInstaller 打包后的路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 打包后，资源文件会被解压到 _MEIPASS 目录
        return os.path.join(sys._MEIPASS, relative_path)
    # 未打包时，使用当前目录
    return os.path.join(os.path.abspath("."), relative_path)

def load_git_properties():
    """加载 git.properties 文件中的信息"""
    global GIT_COMMIT_ID, COMMIT_AUTHOR, BUILD_TIMESTAMP
    
    # 尝试从不同位置读取 git.properties 文件
    possible_paths = [
        resource_path("git.properties"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "git.properties"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "git.properties"),
        os.path.join(os.getcwd(), "git.properties")
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            key, value = line.split("=", 1)
                            key = key.strip()
                            value = value.strip()
                            if key == "git.commit.id.abbrev":
                                GIT_COMMIT_ID = value
                            elif key == "git.commit.author.name":
                                COMMIT_AUTHOR = value
                            elif key == "build.timestamp":
                                BUILD_TIMESTAMP = value
                break
            except Exception as e:
                print(f"读取 git.properties 文件失败: {str(e)}")
                break

# 加载 git.properties 文件
load_git_properties()

# 完整版本信息
def get_version():
    return f"{VERSION}-{GIT_COMMIT_ID}-{BUILD_TIMESTAMP}"

# 获取 Git 提交 ID
def get_git_commit_id():
    return GIT_COMMIT_ID

# 获取提交作者
def get_commit_author():
    return COMMIT_AUTHOR

# 获取构建时间戳
def get_build_timestamp():
    return BUILD_TIMESTAMP

if __name__ == "__main__":
    print(f"版本: {VERSION}")
    print(f"Git 提交 ID: {GIT_COMMIT_ID}")
    print(f"提交作者: {COMMIT_AUTHOR}")
    print(f"构建时间: {BUILD_TIMESTAMP}")
    print(f"完整版本信息: {get_version()}")
