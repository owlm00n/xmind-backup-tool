#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug 版 md_to_xmind：从单个 Markdown 文件还原 XMind，逐行加 log。
与 md2xmind.py 逻辑完全一致，只是加了详细日志。
"""

import os
import sys
import zipfile
import base64
import hashlib
import re
import shutil
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_single_md(md_file: str) -> list:
    """解析单个 Markdown 文件，提取所有文件内容"""
    print(f"=== parse_single_md: {md_file} ===")
    print(f"  file size: {os.path.getsize(md_file)} bytes")

    with open(md_file, 'r', encoding='utf-8', newline='\n') as f:
        content = f.read()

    print(f"  content length: {len(content)} chars")

    files = []
    parts = re.split(r'(### 文件 \d+: `[^`]+`)', content)
    print(f"  after split: {len(parts)} parts")

    for i in range(1, len(parts), 2):
        header = parts[i]
        body = parts[i + 1] if i + 1 < len(parts) else ''
        rel_path = re.search(r'`([^`]+)`', header).group(1)
        print(f"\n--- Part {i//2}: {rel_path} ---")
        print(f"  header: {header!r}")
        print(f"  body length: {len(body)} chars")

        first = body.find('```')
        if first < 0:
            print(f"  SKIP: no ``` found")
            continue
        print(f"  first ``` at position: {first}")

        lang_end = body.find('\n', first)
        lang = body[first + 3:lang_end] if lang_end > 0 else ''
        print(f"  lang_end={lang_end}, lang={lang!r}")

        code_start = lang_end + 1 if lang_end > 0 else first + 3 + len(lang) + 1
        print(f"  code_start={code_start}")

        second = body.find('```', code_start)
        if second < 0:
            print(f"  SKIP: no closing ``` after position {code_start}")
            continue
        print(f"  closing ``` at: {second}")

        code_raw = body[code_start:second]
        print(f"  raw code length (before rstrip): {len(code_raw)} chars")
        print(f"  raw code last 20 chars repr: {repr(code_raw[-20:])}")

        code = code_raw.rstrip('\r\n')
        print(f"  code after rstrip: {len(code)} chars, stripped {len(code_raw) - len(code)} chars")

        is_binary = lang == 'base64'
        print(f"  is_binary={is_binary}")

        if is_binary:
            try:
                decoded_content = base64.b64decode(code)
            except Exception as e:
                print(f"WARN: {rel_path} base64 decode failed: {e}")
                continue
            print(f"  decoded size: {len(decoded_content)} bytes, md5={hashlib.md5(decoded_content).hexdigest()}")
        else:
            decoded_content = code.encode('utf-8')
            print(f"  text size: {len(decoded_content)} bytes, md5={hashlib.md5(decoded_content).hexdigest()}")

        rel_path = rel_path.replace('\\', '/')
        print(f"  final rel_path: {rel_path}")

        files.append({
            'rel_path': rel_path,
            'content': decoded_content,
            'is_binary': is_binary
        })
        ftype = "binary" if is_binary else "text"
        print(f"  OK parsed: {rel_path} ({ftype}, {len(decoded_content)} bytes)")

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


def restore_xmind_from_single_md(md_file: str, xmind_output: str, extract_dir: str = None):
    """从单个 Markdown 文件还原 XMind"""
    print(f"\n=== restore_xmind_from_single_md ===")
    print(f"  md_file: {md_file}")
    print(f"  xmind_output: {xmind_output}")
    print(f"  extract_dir: {extract_dir}")

    files = parse_single_md(md_file)
    if not files:
        print("ERROR: No files found in markdown")
        sys.exit(1)

    print(f"\nTotal parsed: {len(files)} files")

    sorted_files = sorted(files, key=_sort_key)
    print(f"\nSorted order:")
    for idx, fi in enumerate(sorted_files):
        print(f"  [{idx}] {fi['rel_path']} ({len(fi['content'])} bytes, {'bin' if fi['is_binary'] else 'txt'})")

    has_mimetype = any(f['rel_path'] == 'mimetype' for f in files)
    if not has_mimetype:
        print("WARN: mimetype not found in backup, creating default")
        mimetype_content = b'application/vnd.xmind.workbook'
    else:
        mimetype_content = next(f['content'] for f in files if f['rel_path'] == 'mimetype')
    print(f"\nmimetype content: {mimetype_content!r} ({len(mimetype_content)} bytes)")

    # --- Extract decoded files to folder for inspection ---
    if extract_dir:
        extract_path = os.path.abspath(extract_dir)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        os.makedirs(extract_path, exist_ok=True)

        print(f"\n=== Extracting decoded files to: {extract_path} ===")
        for file_info in sorted_files:
            rel_path = file_info['rel_path']
            content = file_info['content']
            out_path = os.path.join(extract_path, rel_path)
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, 'wb') as f:
                f.write(content)
            print(f"  extracted: {rel_path} -> {out_path} ({len(content)} bytes, md5={hashlib.md5(content).hexdigest()})")
    else:
        print(f"\n(no extract_dir, skipping file extraction)")

    print(f"\n=== Building ZIP: {xmind_output} ===")
    with zipfile.ZipFile(xmind_output, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_info in sorted_files:
            rel_path = file_info['rel_path']
            content = file_info['content']

            if rel_path == 'mimetype':
                print(f"  writestr mimetype -> ZIP_STORED")
                zf.writestr(zipfile.ZipInfo('mimetype'), mimetype_content, compress_type=zipfile.ZIP_STORED)
            else:
                is_img = rel_path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico'))
                if not is_img:
                    compress_type = zipfile.ZIP_DEFLATED
                    ext_attr = 0o644 << 16
                    comp_label = "ZIP_DEFLATED"
                else:
                    compress_type = zipfile.ZIP_STORED
                    ext_attr = 0o644 << 16
                    comp_label = "ZIP_STORED"

                print(f"  writestr {rel_path} ({len(content)} bytes) -> {comp_label}")
                print(f"    md5={hashlib.md5(content).hexdigest()}")

                zi = zipfile.ZipInfo(rel_path)
                zi.compress_type = compress_type
                zi.external_attr = ext_attr
                zf.writestr(zi, content)

    final_size = os.path.getsize(xmind_output)
    print(f"\nGenerated ZIP: {xmind_output} ({final_size} bytes)")

    # Verify
    print(f"\n=== Verifying ZIP ===")
    with zipfile.ZipFile(xmind_output) as zf:
        bad = zf.testzip()
        print(f"  testzip: {'OK' if bad is None else 'BAD: ' + str(bad)}")
        print(f"  ZIP contents:")
        for info in zf.infolist():
            comp_name = {0: "STORED", 8: "DEFLATED"}.get(info.compress_type, str(info.compress_type))
            print(f"    {info.filename:50s} uncomp={info.file_size:10d} comp={info.compress_size:10d} {comp_name}")

    if extract_dir:
        print(f"\nExtracted folder: {extract_path}")
        print(f"  Check images/files here to verify decoded data before ZIP compression")
    print(f"\nDone! Open with XMind to verify.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python md2xmind_debug.py <Markdown_file_path> [output_XMind_path]")
        sys.exit(1)

    md_file = sys.argv[1]
    if not os.path.isfile(md_file):
        print(f"Error: not a valid file: {md_file}")
        sys.exit(1)

    if not md_file.lower().endswith('.md'):
        print(f"Error: expected .md file, got: {md_file}")
        sys.exit(1)

    if len(sys.argv) >= 3:
        xmind_output = sys.argv[2]
    else:
        md_name = os.path.basename(md_file)
        xmind_name = md_name.replace('.md', '').replace('_完整备份', '_还原') + '.xmind'
        xmind_output = os.path.join(os.path.dirname(md_file), xmind_name)

    if len(sys.argv) >= 4:
        extract_dir = sys.argv[3]
    else:
        extract_dir = None

    print(f"Restore: {md_file}")
    print(f"Output: {xmind_output}")
    print(f"Extract: {extract_dir}\n")

    try:
        restore_xmind_from_single_md(md_file, xmind_output, extract_dir)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
