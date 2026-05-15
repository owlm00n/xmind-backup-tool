#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复版 md_to_xmind：从单个 Markdown 文件还原 XMind。
关键修复：
1. 按文件条目分割 MD，精确提取代码块内容
2. 代码块内保留 \r\n 换行（XML 文件中的 Windows 换行）
3. 使用 ZipInfo 避免 zipfile 自动换行转换
核心约束：以 wb 模式写 MD 文件、使用 newline='\n' 打开、不用正则匹配 code block 边界。
"""

import os
import sys
import zipfile
import base64
import re
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_single_md(md_file: str) -> list:
    """解析单个 Markdown 文件，提取所有文件内容"""
    with open(md_file, 'r', encoding='utf-8', newline='\n') as f:
        content = f.read()

    files = []
    parts = re.split(r'(### 文件 \d+: `[^`]+`)', content)

    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ''
        rel_path = re.search(r'`([^`]+)`', header).group(1)

        first = body.find('```')
        if first < 0:
            continue

        lang_end = body.find('\n', first)
        lang = body[first + 3:lang_end] if lang_end > 0 else ''

        code_start = lang_end + 1 if lang_end > 0 else first + 3 + len(lang) + 1

        second = body.find('```', code_start)
        if second < 0:
            continue

        code = body[code_start:second]
        code = code.rstrip('\r\n')

        is_binary = lang == 'base64'

        if is_binary:
            try:
                decoded_content = base64.b64decode(code)
            except Exception as e:
                print(f"WARN: {rel_path} base64 decode failed: {e}")
                continue
        else:
            decoded_content = code.encode('utf-8')

        rel_path = rel_path.replace('\\', '/')

        files.append({
            'rel_path': rel_path,
            'content': decoded_content,
            'is_binary': is_binary
        })
        ftype = "binary" if is_binary else "text"
        print(f"OK parsed: {rel_path} ({ftype})")

    return files


# XMind 标准文件顺序（优先排前面）
XMIND_ORDER = [
    'mimetype',
    'content.xml',
    'meta.xml',
    'styles.xml',
    'META-INF/manifest.xml',
    'META-INF/',
    'Revisions/',
    'Thumbnails/',
]


def _sort_key(item):
    """按 XMind 标准顺序排序"""
    path = item['rel_path']
    for i, std in enumerate(XMIND_ORDER):
        if path == std or path.startswith(std + '/'):
            return (0, i, path)
    return (1, 0, path)


def restore_xmind_from_single_md(md_file: str, xmind_output: str):
    """从单个 Markdown 文件还原 XMind"""
    print(f"Parsing: {md_file}\n")

    files = parse_single_md(md_file)
    if not files:
        print("ERROR: No files found in markdown")
        sys.exit(1)

    print(f"\nTotal: {len(files)} files\n")

    sorted_files = sorted(files, key=_sort_key)

    has_mimetype = any(f['rel_path'] == 'mimetype' for f in files)
    if not has_mimetype:
        print("WARN: mimetype not found in backup, creating default")
        mimetype_content = b'application/vnd.xmind.workbook'
    else:
        mimetype_content = next(f['content'] for f in files if f['rel_path'] == 'mimetype')

    with zipfile.ZipFile(xmind_output, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_info in sorted_files:
            rel_path = file_info['rel_path']
            content = file_info['content']

            if rel_path == 'mimetype':
                zf.writestr(zipfile.ZipInfo('mimetype'), mimetype_content, compress_type=zipfile.ZIP_STORED)
            else:
                zi = zipfile.ZipInfo(rel_path)
                if not rel_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico')):
                    zi.compress_type = zipfile.ZIP_DEFLATED
                    zi.external_attr = 0o644 << 16
                else:
                    zi.compress_type = zipfile.ZIP_STORED
                zf.writestr(zi, content)

    print(f"Generated: {xmind_output}")
    print("Done! Open with XMind to verify.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python md2xmind.py <Markdown_file_path> [output_XMind_path]")
        sys.exit(1)

    md_file = sys.argv[1]
    if not os.path.isfile(md_file):
        print(f"Error: not a valid file: {md_file}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        xmind_output = sys.argv[2]
    else:
        md_name = os.path.basename(md_file)
        xmind_name = md_name.replace('.md', '').replace('_完整备份', '_还原') + '.xmind'
        xmind_output = os.path.join(os.path.dirname(md_file), xmind_name)

    print(f"Restore: {md_file}")
    print(f"Output: {xmind_output}\n")

    try:
        restore_xmind_from_single_md(md_file, xmind_output)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
