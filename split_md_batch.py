#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch split: recursively find all .md files under input_dir
and split each into _partN.md files under the corresponding
output directory. Preserves subdirectory structure.

Usage:
  python split_md_batch.py <input_directory> <output_directory> [--max-size-bytes 5000000]
"""

import os
import sys
import pathlib
import re


def batch_split(input_root: pathlib.Path, output_root: pathlib.Path,
                max_size: int = 4_500_000):
    md_files = sorted(
        f for f in input_root.rglob('*')
        if f.is_file() and f.name.endswith('.md')
    )

    if not md_files:
        print(f"No .md files found in {input_root}")
        return

    print(f"Found {len(md_files)} .md files (max chars per chunk: {max_size:,})\n")
    total_parts = 0

    for md_file in md_files:
        rel = md_file.relative_to(input_root)
        output_dir = output_root / rel.parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Read raw bytes to preserve original line endings
        raw_content = md_file.read_bytes()
        content = raw_content.decode('utf-8')

        sections = re.split(r'(?=### 文件 \d+: `)', content)
        parts = []
        current_parts = []
        for s in sections:
            stripped = s.strip()
            if stripped and not stripped.startswith('### 文件'):
                current_parts.append(s)
            elif current_parts:
                parts.append(''.join(current_parts))
                current_parts = [s]
            else:
                parts.append(s)
        if current_parts:
            parts.append(''.join(current_parts))
        parts = [p for p in parts if p.strip()]

        if not parts:
            print(f"SKIP (no file sections): {rel}")
            continue

        # Split preserves original line endings by splitting on
        # both \r\n and \n, but we need to rejoin with the original separator
        # Better approach: split content by the part boundaries, keeping \r\n
        # Rebuild chunks preserving original bytes for joined lines
        chunks = []
        current_chunk = []
        current_size = 0
        for part in parts:
            part_size = len(part)
            if part_size > max_size:
                if current_chunk:
                    chunks.append(''.join(current_chunk))
                    current_chunk = []
                    current_size = 0
                # Split by original line endings (\r\n or \n)
                # Use splitlines with keepends to preserve original endings
                lines = part.splitlines(keepends=True)
                temp = []
                temp_size = 0
                for line in lines:
                    ls = len(line)
                    if temp_size + ls > max_size and temp:
                        chunks.append(''.join(temp))
                        temp = []
                        temp_size = 0
                    temp.append(line)
                    temp_size += ls
                if temp:
                    chunks.append(''.join(temp))
                continue
            if current_size + part_size > max_size and current_chunk:
                chunks.append(''.join(current_chunk))
                current_chunk = []
                current_size = 0
            current_chunk.append(part)
            current_size += part_size
        if current_chunk:
            chunks.append(''.join(current_chunk))

        stem = md_file.stem  # use name without .md extension
        for i, chunk in enumerate(chunks, 1):
            if len(chunks) == 1:
                out_name = md_file.name  # not split, keep original name
            else:
                out_name = f"{stem}_part{i:03d}.md"
            # Write raw bytes to preserve original \r\n line endings
            (output_dir / out_name).write_bytes(chunk.encode('utf-8'))

        total_parts += len(chunks)
        print(f"[{md_files.index(md_file) + 1}/{len(md_files)}] {rel} -> {len(chunks)} chunk(s)")

    print(f"\nDone: {len(md_files)} files split into {total_parts} chunks")


def main():
    args = sys.argv[1:]
    max_size = 4_500_000

    files = []
    i = 0
    while i < len(args):
        if args[i] == '--max-size-bytes' and i + 1 < len(args):
            max_size = int(args[i + 1])
            i += 2
        elif args[i].startswith('--'):
            i += 1
        else:
            files.append(args[i])
            i += 1

    if len(files) < 2:
        print("Usage: python split_md_batch.py <input_directory> <output_directory>")
        sys.exit(1)

    input_root = pathlib.Path(files[0])
    output_root = pathlib.Path(files[1])

    if not input_root.is_dir():
        print(f"ERROR: Directory not found: {input_root}")
        sys.exit(1)

    batch_split(input_root, output_root, max_size)


if __name__ == "__main__":
    main()
