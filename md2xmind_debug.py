#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug 版 md_to_xmind：从单个 Markdown 文件还原 XMind，并输出大量调试信息。
额外功能：
1. 保存一份解压后的文件夹（含未压缩的图片等二进制文件）
2. 打印每个文件解码前后的 size/md5
3. 打印代码块提取的详细过程
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

LOG = []

def log(msg, indent=0):
    prefix = "  " * indent
    full = f"{prefix}{msg}"
    LOG.append(full)
    print(full)


def log_hex(name, data, offset=0, length=64):
    """打印数据开头的十六进制，便于比对二进制差异"""
    chunk = data[offset:offset + length]
    hex_str = ' '.join(f'{b:02x}' for b in chunk)
    log(f"  [{name}] hex({offset}:{offset+length}): {hex_str}")


def parse_single_md(md_file: str) -> list:
    """解析单个 Markdown 文件，提取所有文件内容"""
    log(f"=== parse_single_md: {md_file} ===")
    file_size = os.path.getsize(md_file)
    log(f"MD file size: {file_size} bytes")

    with open(md_file, 'r', encoding='utf-8', newline='\n') as f:
        content = f.read()

    log(f"MD content length: {len(content)} chars")

    # Check for BOM
    if content.startswith('﻿'):
        log("WARN: MD file has BOM, stripping", 1)
        content = content[1:]

    files = []
    sections = re.split(r'(?=### 文件 \d+: `)', content)
    log(f"After split: {len(sections)} sections")

    for i in range(1, len(sections), 2):
        header = sections[i]
        body = sections[i + 1] if i + 1 < len(sections) else ''
        rel_path = re.search(r'`([^`]+)`', header)
        if not rel_path:
            log(f"  SKIP: no path in header: {header[:60]}", 1)
            continue
        rel_path = rel_path.group(1)
        log(f"\n--- File {i//2}: {rel_path} ---")
        log(f"  body length: {len(body)} chars")

        first = body.find('```')
        if first < 0:
            log(f"  SKIP: no ``` found in body", 1)
            continue
        log(f"  ``` found at position: {first}")
        log(f"  context before ```: ...{repr(body[max(0,first-10):first])}")

        lang_end = body.find('\n', first)
        if lang_end > 0:
            lang = body[first + 3:lang_end]
            code_start = lang_end + 1
        else:
            lang = ''
            code_start = first + 3 + len(lang) + 1
            log(f"  WARN: no newline after ```, lang='', code_start={code_start}", 1)

        log(f"  lang='{lang}', code_start={code_start}")

        second = body.find('```', code_start)
        if second < 0:
            log(f"  SKIP: no closing ``` after position {code_start}", 1)
            continue
        log(f"  closing ``` found at: {second}")

        code = body[code_start:second]
        log(f"  raw code length (before rstrip): {len(code)} chars")
        log(f"  raw code last 10 chars: {repr(code[-10:])}")

        code = code.rstrip('\r\n')
        log(f"  code length (after rstrip): {len(code)} chars")
        stripped_len = len(code_raw) - len(code)
        log(f"  stripped {stripped_len} trailing \\r\\n chars")

        # Print first 32 hex bytes of raw code
        code_bytes_raw = code_raw.encode('utf-8')
        log_hex("raw_code", code_bytes_raw, 0, 32)
        if len(code_bytes_raw) > 128:
            log_hex("raw_code", code_bytes_raw, len(code_bytes_raw) - 32, 32)

        is_binary = lang == 'base64'
        log(f"  is_binary={is_binary}, lang=='base64' -> {lang == 'base64'}")

        if is_binary:
            # Check base64 validity before decoding
            clean = code.strip()
            log(f"  base64 len: {len(code)}, clean len: {len(clean)}, mod4: {len(clean) % 4}")
            if len(code) > 0:
                log(f"  first 40 base64 chars: {repr(code[:40])}")
                log(f"  last 40 base64 chars: {repr(code[-40:])}")

            try:
                decoded_content = base64.b64decode(code)
            except Exception as e:
                log(f"ERROR: {rel_path} base64 decode failed: {e}", 1)
                # Try with validate=True to be stricter
                try:
                    decoded_content = base64.b64decode(code, validate=True)
                    log(f"  decode succeeded with validate=True", 1)
                except Exception as e2:
                    log(f"  decode also failed with validate=True: {e2}", 2)
                    continue

            log(f"  decoded size: {len(decoded_content)} bytes")
            log(f"  decoded md5: {hashlib.md5(decoded_content).hexdigest()}")
            log_hex("decoded_first", decoded_content, 0, 32)
        else:
            decoded_content = code.encode('utf-8')
            log(f"  text size: {len(decoded_content)} bytes")

        rel_path = rel_path.replace('\\', '/')
        files.append({
            'rel_path': rel_path,
            'content': decoded_content,
            'is_binary': is_binary
        })
        ftype = "binary" if is_binary else "text"
        log(f"  OK parsed: {rel_path} ({ftype}, {len(decoded_content)} bytes)")

    return files


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
    path = item['rel_path']
    for i, std in enumerate(XMIND_ORDER):
        if path == std or path.startswith(std + '/'):
            return (0, i, path)
    return (1, 0, path)


def restore_xmind_from_single_md(md_file: str, xmind_output: str, extract_dir: str):
    """从单个 Markdown 文件还原 XMind，并提取未压缩文件到 extract_dir"""
    log(f"\n=== restore_xmind_from_single_md ===")
    log(f"md_file: {md_file}")
    log(f"xmind_output: {xmind_output}")
    log(f"extract_dir: {extract_dir}")

    files = parse_single_md(md_file)
    if not files:
        log("ERROR: No files found in markdown")
        sys.exit(1)

    log(f"\nTotal parsed files: {len(files)}")

    sorted_files = sorted(files, key=_sort_key)
    log(f"Sorted file order:")
    for idx, fi in enumerate(sorted_files):
        log(f"  [{idx}] {fi['rel_path']} ({len(fi['content'])} bytes, {'bin' if fi['is_binary'] else 'txt'})", 1)

    has_mimetype = any(f['rel_path'] == 'mimetype' for f in files)
    if not has_mimetype:
        log("WARN: mimetype not found, creating default", 1)
        mimetype_content = b'application/vnd.xmind.workbook'
    else:
        mimetype_content = next(f['content'] for f in files if f['rel_path'] == 'mimetype')
    log(f"mimetype: {mimetype_content!r} ({len(mimetype_content)} bytes)")

    # --- Extract all files to folder for inspection ---
    log(f"\n=== Extracting files to {extract_dir} ===")
    extract_path = os.path.abspath(extract_dir)
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    os.makedirs(extract_path, exist_ok=True)

    for file_info in sorted_files:
        rel_path = file_info['rel_path']
        content = file_info['content']
        out_path = os.path.join(extract_path, rel_path)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'wb') as f:
            f.write(content)
        log(f"  extracted: {rel_path} -> {out_path} ({len(content)} bytes, md5={hashlib.md5(content).hexdigest()})")

    log(f"\nExtracted folder: {extract_path}")
    log(f"  You can open this folder and check all files directly")
    log(f"  Images (.png/.jpg etc) can be opened with any image viewer")

    # --- Build ZIP ---
    log(f"\n=== Building ZIP: {xmind_output} ===")
    with zipfile.ZipFile(xmind_output, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_info in sorted_files:
            rel_path = file_info['rel_path']
            content = file_info['content']

            if rel_path == 'mimetype':
                log(f"  writestr mimetype (ZIP_STORED)", 1)
                zf.writestr(zipfile.ZipInfo('mimetype'), mimetype_content, compress_type=zipfile.ZIP_STORED)
            else:
                is_img = rel_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.ico'))
                if is_img:
                    comp_type = zipfile.ZIP_STORED
                    comp_label = "ZIP_STORED"
                else:
                    comp_type = zipfile.ZIP_DEFLATED
                    comp_label = "ZIP_DEFLATED"

                zi = zipfile.ZipInfo(rel_path)
                zi.compress_type = comp_type
                zi.external_attr = 0o644 << 16

                zf.writestr(zi, content)
                log(f"  writestr {rel_path} ({len(content)} bytes) -> {comp_label}, md5={hashlib.md5(content).hexdigest()}", 1)

    log(f"Generated ZIP: {xmind_output} ({os.path.getsize(xmind_output)} bytes)")

    # Verify ZIP
    log(f"\n=== Verifying ZIP ===")
    with zipfile.ZipFile(xmind_output) as zf:
        bad = zf.testzip()
        if bad is None:
            log("ZIP testzip: OK", 1)
        else:
            log(f"ZIP testzip: BAD file - {bad}", 1)

        log(f"ZIP contents:")
        for info in zf.infolist():
            comp_name = {0: "STORED", 8: "DEFLATED"}.get(info.compress_type, str(info.compress_type))
            log(f"  {info.filename:50s} uncomp={info.file_size:10d} comp={info.compress_size:10d} {comp_name}", 1)

    log(f"\n=== Summary ===")
    log(f"ZIP output: {xmind_output}")
    log(f"Extracted folder: {extract_path}")
    log(f"Open the extracted folder to check images directly")
    log(f"Open the .xmind with XMind to verify")
    log(f"Done!")


def main():
    if len(sys.argv) < 2:
        print("Usage: python md2xmind_debug.py <Markdown_file> [output_XMind] [extract_folder]")
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

    if len(sys.argv) >= 4:
        extract_dir = sys.argv[3]
    else:
        md_base = os.path.basename(md_file).replace('.md', '')
        extract_dir = os.path.join(os.path.dirname(md_file), md_base + "_extracted")

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
