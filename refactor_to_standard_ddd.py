#!/usr/bin/env python3
"""
DDD 标准化改造脚本 - 方案 A
1. services/ → application/
2. models/schemas.py → schemas/
3. 更新所有 import
"""
import os
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).parent

# 文件移动映射
FILE_MOVES = {
    # services → application (整个目录)
    'services': 'application',
}

# models/schemas.py → schemas/
SCHEMA_FILES = [
    'models/schemas.py',
    'models/auth_schemas.py',
]

# Import 替换规则
IMPORT_REPLACEMENTS = {
    # services → application
    'from application.': 'from application.',
    'from application import': 'from application import',
    'import application.': 'import application.',
    
    # schemas.schemas → schemas
    'from schemas.schemas import': 'from schemas.schemas import',
    'from schemas.schemas': 'from schemas.schemas',
    'schemas.schemas': 'schemas.schemas',
    
    'from schemas.auth_schemas import': 'from schemas.auth_schemas import',
    'from schemas.auth_schemas': 'from schemas.auth_schemas',
    'schemas.auth_schemas': 'schemas.auth_schemas',
}


def rename_directory(old_name: str, new_name: str):
    """重命名目录"""
    old_path = ROOT_DIR / old_name
    new_path = ROOT_DIR / new_name
    
    if old_path.exists():
        if new_path.exists():
            print(f"  ⚠️  {new_name}/ 已存在，跳过")
            return False
        shutil.move(str(old_path), str(new_path))
        print(f"  ✅ {old_name}/ → {new_name}/")
        return True
    else:
        print(f"  ⚠️  {old_name}/ 不存在")
        return False


def move_schemas():
    """移动 schemas 文件到独立目录"""
    schemas_dir = ROOT_DIR / 'schemas'
    schemas_dir.mkdir(exist_ok=True)
    
    # 创建 __init__.py
    init_file = schemas_dir / '__init__.py'
    init_file.write_text('"""\nPydantic DTO Schemas\n职责：API 输入输出数据传输对象\n"""\n', encoding='utf-8')
    
    moved_count = 0
    for schema_file in SCHEMA_FILES:
        src = ROOT_DIR / schema_file
        if src.exists():
            dst = schemas_dir / src.name
            shutil.move(str(src), str(dst))
            print(f"  ✅ {schema_file} → schemas/{src.name}")
            moved_count += 1
    
    return moved_count


def update_imports_in_file(file_path: Path):
    """更新文件中的 import 语句"""
    if not file_path.exists() or file_path.suffix != '.py':
        return False
    
    try:
        content = file_path.read_text(encoding='utf-8')
        original_content = content
        
        # 应用所有替换规则
        for old_import, new_import in IMPORT_REPLACEMENTS.items():
            content = content.replace(old_import, new_import)
        
        # 如果有修改，写回文件
        if content != original_content:
            file_path.write_text(content, encoding='utf-8')
            return True
    except Exception as e:
        print(f"  ❌ 处理 {file_path} 失败: {e}")
    
    return False


def update_all_imports():
    """更新所有 Python 文件的 import 语句"""
    print("\n🔄 更新 import 语句...")
    
    updated_files = []
    
    # 遍历所有 Python 文件
    for file_path in ROOT_DIR.rglob('*.py'):
        # 排除虚拟环境和缓存目录
        if any(part in file_path.parts for part in ['.venv', '__pycache__', '.git']):
            continue
        
        if update_imports_in_file(file_path):
            updated_files.append(str(file_path.relative_to(ROOT_DIR)))
    
    if updated_files:
        print(f"\n  ✅ 更新了 {len(updated_files)} 个文件:")
        for f in updated_files[:10]:  # 只显示前 10 个
            print(f"     - {f}")
        if len(updated_files) > 10:
            print(f"     ... 还有 {len(updated_files) - 10} 个文件")
    
    return len(updated_files)


def main():
    print("🏗️  DDD 标准化改造 - 方案 A")
    print("=" * 60)
    
    # 1. 重命名 services → application
    print("\n📦 步骤 1: 重命名目录...")
    rename_directory('services', 'application')
    
    # 2. 移动 schemas 文件
    print("\n📦 步骤 2: 移动 Pydantic Schemas...")
    moved = move_schemas()
    print(f"  ✅ 移动了 {moved} 个 schema 文件")
    
    # 3. 更新 import 语句
    updated = update_all_imports()
    
    print("\n" + "=" * 60)
    print("✅ 改造完成！")
    print(f"\n📊 统计:")
    print(f"  - 重命名目录: services → application")
    print(f"  - 移动文件: {moved} 个")
    print(f"  - 更新 import: {updated} 个文件")
    print("\n📋 后续步骤:")
    print("  1. 测试: uv run app.py")
    print("  2. 验证: python -m py_compile application/*.py schemas/*.py")
    print("  3. 更新 README 文档")


if __name__ == '__main__':
    main()
