#!/usr/bin/env python3
"""
FJNote AstrBot插件打包脚本
自动打包为zip格式供AstrBot后台安装
"""

import os
import zipfile
import shutil
from pathlib import Path

def create_plugin_package():
    """创建插件包"""
    print("📦 开始打包 FJNote 插件...")
    
    # 项目根目录
    root_dir = Path(__file__).parent
    
    # 输出目录和文件
    output_dir = root_dir / "dist"
    zip_file = output_dir / "fjnote-plugin.zip"
    
    # 清理输出目录
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    
    # 从 metadata.yaml 获取插件名称
    plugin_name = "FjNoteBot"  # 使用 metadata.yaml 中的 name
    
    # 需要包含的文件和目录
    include_files = [
        "main.py",
        "metadata.yaml", 
        "requirements.txt",
        "_conf_schema.json",
        "fjnote/",
        "README.md"
    ]
    
    # 排除的文件模式
    exclude_patterns = [
        "__pycache__",
        "*.pyc",
        "*.pyo", 
        ".DS_Store",
        "*.egg-info",
        ".git",
        "venv/",
        "test_*.py",
        "run.py",
        "package.py",
        "dist/",
        "docs/"
    ]
    
    print(f"📁 创建 zip 包: {zip_file}")
    print(f"📂 插件目录: {plugin_name}/")
    
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 首先创建插件目录结构
        zf.writestr(f"{plugin_name}/", "")  # 创建空目录
        
        for item in include_files:
            item_path = root_dir / item
            
            if not item_path.exists():
                print(f"⚠️  跳过不存在的文件: {item}")
                continue
                
            if item_path.is_file():
                # 单个文件 - 添加到插件目录下
                if not should_exclude(item_path, exclude_patterns):
                    arc_path = f"{plugin_name}/{item}"
                    zf.write(item_path, arc_path)
                    print(f"✅ 添加文件: {arc_path}")
                else:
                    print(f"⚠️  排除文件: {item}")
            
            elif item_path.is_dir():
                # 目录递归添加 - 添加到插件目录下
                for file_path in item_path.rglob("*"):
                    if file_path.is_file() and not should_exclude(file_path, exclude_patterns):
                        # 计算相对路径并添加插件目录前缀
                        rel_path = file_path.relative_to(root_dir)
                        arc_path = f"{plugin_name}/{rel_path}"
                        zf.write(file_path, arc_path)
                        print(f"✅ 添加文件: {arc_path}")
                    elif should_exclude(file_path, exclude_patterns):
                        print(f"⚠️  排除文件: {file_path.relative_to(root_dir)}")
    
    # 验证包内容
    print(f"\n📋 包内容验证:")
    with zipfile.ZipFile(zip_file, 'r') as zf:
        file_list = zf.namelist()
        for file_name in sorted(file_list):
            print(f"   {file_name}")
    
    file_size = zip_file.stat().st_size
    print(f"\n🎉 打包完成!")
    print(f"📦 文件路径: {zip_file}")
    print(f"📏 文件大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")
    print(f"📊 包含文件: {len(file_list)} 个")
    
    print(f"\n📋 AstrBot 安装说明:")
    print("1. 登录 AstrBot 管理后台")
    print("2. 进入 插件管理 -> 本地安装")
    print(f"3. 上传 {zip_file.name}")
    print("4. 配置 Blinko API 信息")
    print("5. 启用插件")

def should_exclude(file_path: Path, exclude_patterns: list) -> bool:
    """检查文件是否应该被排除"""
    file_str = str(file_path)
    
    for pattern in exclude_patterns:
        if pattern in file_str:
            return True
        if file_path.name == pattern:
            return True
        if pattern.endswith("/") and pattern[:-1] in file_path.parts:
            return True
    
    return False

if __name__ == "__main__":
    create_plugin_package()