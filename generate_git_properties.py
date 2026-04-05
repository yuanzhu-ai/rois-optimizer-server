#!/usr/bin/env python3
"""
生成 git.properties 文件，包含最新的 git 提交信息
"""
import os
import subprocess
import datetime

# 生成 git.properties 文件
def generate_git_properties():
    try:
        # 获取 git 提交信息
        git_commit_id = subprocess.check_output(["git", "rev-parse", "HEAD"], 
                                            cwd=os.path.dirname(os.path.abspath(__file__))).strip().decode('utf-8')
        git_commit_short_id = git_commit_id[:7]
        
        # 获取提交作者
        git_commit_author = subprocess.check_output(["git", "log", "-1", "--format=%an"], 
                                                  cwd=os.path.dirname(os.path.abspath(__file__))).strip().decode('utf-8')
        
        # 获取提交时间
        git_commit_time = subprocess.check_output(["git", "log", "-1", "--format=%ci"], 
                                                cwd=os.path.dirname(os.path.abspath(__file__))).strip().decode('utf-8')
        
        # 生成当前时间戳
        build_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 写入 git.properties 文件
        with open("git.properties", "w", encoding="utf-8") as f:
            f.write(f"# Git 提交信息\n")
            f.write(f"git.commit.id={git_commit_id}\n")
            f.write(f"git.commit.id.abbrev={git_commit_short_id}\n")
            f.write(f"git.commit.author.name={git_commit_author}\n")
            f.write(f"git.commit.time={git_commit_time}\n")
            f.write(f"build.timestamp={build_timestamp}\n")
        
        print("git.properties 文件生成成功！")
        print(f"Git 提交 ID: {git_commit_short_id}")
        print(f"提交作者: {git_commit_author}")
        print(f"构建时间: {build_timestamp}")
        
    except Exception as e:
        print(f"生成 git.properties 文件失败: {str(e)}")
        # 如果生成失败，创建一个默认的 git.properties 文件
        with open("git.properties", "w", encoding="utf-8") as f:
            f.write("# Git 提交信息\n")
            f.write("git.commit.id=unknown\n")
            f.write("git.commit.id.abbrev=unknown\n")
            f.write("git.commit.author.name=unknown\n")
            f.write("git.commit.time=unknown\n")
            f.write(f"build.timestamp={datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        print("已创建默认的 git.properties 文件")

if __name__ == "__main__":
    generate_git_properties()
