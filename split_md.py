#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Split a single large Markdown file into chunks.
Each chunk is split at the ### 文件 boundary (file section header)
to keep individual file backups intact.

Usage:
  python split_md.py <input.md> <output_directory> [--max-size-bytes] [--max-chunks]
"""

import os
import sys
import pathlib
import re


def split_md(input_file: pathlib.Path, output_dir: pathlib.Path,
             max_size: int = 4_500_000, max_chunks: int = 500):
    """
    Split a single MD file into chunks.
    Split at '### 文件 N:' headers so individual XMind file sections stay intact.
    """
    content = input_file.read_bytes().decode('utf-8')

    # Find all ### 文件 boundaries
    sections = re.split(r'(?=### 文件 \d+: `)', content)

    # Filter out header lines before the first file section
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

    # Remove empty parts
    parts = [p for p in parts if p.strip()]

    if not parts:
        print(f"ERROR: No file sections found in {input_file}")
        return

    print(f"Found {len(parts)} file sections in {input_file.name}")

    # Build chunks — count by CHARACTERS, not bytes
    chunks = []
    current_chunk_lines = []
    current_chunk_size = 0
    chunk_idx = 0

    for part in parts:
        part_size = len(part)

        # If a single part is larger than max_size, split by newlines
        if part_size > max_size:
            if current_chunk_lines:
                chunks.append(''.join(current_chunk_lines))
                current_chunk_lines = []
                current_chunk_size = 0

            # Split this large part into smaller pieces
            lines = part.splitlines(keepends=True)
            temp_chunk = []
            temp_size = 0
            for line in lines:
                ls = len(line)
                if temp_size + ls > max_size and temp_chunk:
                    chunks.append(''.join(temp_chunk))
                    temp_chunk = []
                    temp_size = 0
                temp_chunk.append(line)
                temp_size += ls
            if temp_chunk:
                chunks.append(''.join(temp_chunk))
            continue

        if current_chunk_size + part_size > max_size and current_chunk_lines:
            chunks.append(''.join(current_chunk_lines))
            current_chunk_lines = []
            current_chunk_size = 0

        current_chunk_lines.append(part)
        current_chunk_size += part_size

    if current_chunk_lines:
        chunks.append(''.join(current_chunk_lines))

    # Limit chunks
    if len(chunks) > max_chunks:
        print(f"WARN: Exceeded max_chunks ({max_chunks}), taking first {max_chunks}")
        chunks = chunks[:max_chunks]

    print(f"Split into {len(chunks)} chunks")

    output_dir.mkdir(parents=True, exist_ok=True)

    stem = input_file.stem
    for i, chunk in enumerate(chunks, 1):
        if len(chunks) == 1:
            out_name = input_file.name
        else:
            out_name = f"{stem}_part{i:03d}.md"
        out_path = output_dir / out_name
        out_path.write_bytes(chunk.encode('utf-8'))
        print(f"  [{i}/{len(chunks)}] {out_name} ({len(chunk)} chars)")

    print(f"Done: {output_dir}")


def main():
    args = sys.argv[1:]
    max_size = 4_500_000  # default 4.5M chars (safe for 5M limit)

    files = []
    i = 0
    while i < len(args):
        if args[i] == '--max-size-bytes' and i + 1 < len(args):
            max_size = int(args[i + 1])
            i += 2
        elif args[i].startswith('--'):
            print(f"WARN: Unknown option '{args[i]}'")
            i += 1
        else:
            files.append(args[i])
            i += 1

    if len(files) < 2:
        print("Usage: python split_md.py <input.md> <output_directory>")
        sys.exit(1)

    input_file = pathlib.Path(files[0])
    output_dir = pathlib.Path(files[1])

    if not input_file.is_file():
        print(f"ERROR: File not found: {input_file}")
        sys.exit(1)

    split_md(input_file, output_dir, max_size=max_size)


if __name__ == "__main__":
    main()
