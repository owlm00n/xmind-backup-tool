#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版 xmind_to_1_md：直接读取 .xmind 文件（ZIP格式），无需手动解压。
关键修复：在写入 MD 代码块时保留 \r\n 换行，确保 roundtrip 完全一致。
核心约束：以 wb 模式写文件、不使用正则匹配 code block 边界。
"""

import os
import sys
import zipfile
import base64
import datetime
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def backup_xmind_to_single_md(xmind_file: str, output_md: str):
    """将 .xmind 文件的所有内容备份到单个 Markdown 文件"""
    if not os.path.isfile(xmind_file):
        print(f"错误: 不是有效的文件: {xmind_file}")
        sys.exit(1)

    standard_files = [
        'mimetype',
        'content.xml',
        'meta.xml',
        'styles.xml',
        'META-INF/manifest.xml',
    ]

    seen = set()
    all_files = []

    with zipfile.ZipFile(xmind_file, 'r') as zf:
        for std_file in standard_files:
            if std_file in zf.namelist():
                if std_file not in seen:
                    seen.add(std_file)
                    all_files.append((std_file, zf.read(std_file)))

        for name in zf.namelist():
            if name not in seen:
                seen.add(name)
                all_files.append((name, zf.read(name)))

    print(f"Backup: {xmind_file}")
    print(f"Output: {output_md}\n")
    print(f"Total: {len(all_files)} files\n")

    # 使用字节列表来构建 MD，完全控制换行
    md_bytes = []

    # Header
    def add(s):
        md_bytes.append(s.encode('utf-8'))

    def add_line(s=''):
        add(s)
        add('\n')

    add_line(f"# XMind 完整备份 - {os.path.basename(xmind_file)}")
    add_line()
    add_line(f"**原始文件**: `{xmind_file}`")
    add_line(f"**备份时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    add_line(f"**文件总数**: {len(all_files)}")
    add_line()
    add_line("---")
    add_line()
    add_line("## 使用说明")
    add_line()
    add_line("1. **复制**: 复制整个文件内容到任何地方保存")
    add_line("2. **编辑**: 可以直接修改代码块中的内容（XML、文本等）")
    add_line("3. **还原**: 使用 `md_to_xmind_single_fixed.py` 脚本还原为 XMind 文件")
    add_line()
    add_line("---")
    add_line()

    for i, (rel_path, raw_bytes) in enumerate(all_files, 1):
        add_line(f"### 文件 {i}: `{rel_path}`")

        is_binary_img = rel_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico'))

        if is_binary_img:
            b64_content = base64.b64encode(raw_bytes).decode('utf-8')
            add_line("**类型**: 二进制图片 (base64)")
            add_line(f"**原始大小**: {len(raw_bytes)} 字节")
            add_line()
            add("```base64\n")
            add(b64_content + '\n')
            add("```\n")
        else:
            try:
                text_content = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                b64_content = base64.b64encode(raw_bytes).decode('utf-8')
                add_line("**类型**: 二进制 (base64)")
                add_line(f"**原始大小**: {len(raw_bytes)} 字节")
                add_line()
                add("```base64\n")
                add(b64_content + '\n')
                add("```\n")
            else:
                lang = 'xml' if rel_path.endswith('.xml') else 'text'
                add_line("**类型**: 文本")
                add_line(f"**大小**: {len(text_content)} 字符")
                add_line()
                add(f"```{lang}\n")
                # 关键：XML 原始内容中的 \r\n 保留为 \r\n，然后代码块末尾加 \n
                add(text_content)
                add("```\n")

        add_line()
        add_line("---")
        add_line()
        print(f"OK {rel_path} ({len(raw_bytes)} bytes)")

    with open(output_md, 'wb') as f:
        f.write(b''.join(md_bytes))

    print(f"\nDone! {len(all_files)} files -> {output_md}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python xmind2md.py <XMind_file_path> [output_Markdown_path]")
        print("Example: python xmind2md.py \"AI.xmind\"")
        print("         python xmind2md.py \"AI.xmind\" \"backup.md\"")
        sys.exit(1)

    xmind_file = sys.argv[1]
    if not os.path.isfile(xmind_file):
        print(f"错误: 不是有效的文件: {xmind_file}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_md = sys.argv[2]
    else:
        base_name = os.path.splitext(os.path.basename(xmind_file))[0]
        output_md = os.path.join(os.path.dirname(xmind_file), f"{base_name}_完整备份.md")

    try:
        backup_xmind_to_single_md(xmind_file, output_md)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
