#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Merge chunked MD files back into a single MD file.
Detects _partN.md files and merges them in order.

Usage:
  python merge_md.py <input_directory> <output.md>
"""

import os
import sys
import pathlib
import re


def merge_md(input_dir: pathlib.Path, output_file: pathlib.Path):
    """
    Merge all *_part*.md files in a directory back into one MD.
    Files are sorted by their _part### number.
    """
    if not input_dir.is_dir():
        print(f"ERROR: Directory not found: {input_dir}")
        sys.exit(1)

    # Find all part files
    part_files = []
    for p in input_dir.iterdir():
        if not p.is_file():
            continue
        m = re.match(r'^(.+)_part(\d{3})\.md$', p.name)
        if m:
            base_name = m.group(1)
            part_num = int(m.group(2))
            part_files.append((base_name, part_num, p))

    if not part_files:
        print(f"ERROR: No _part*.md files found in {input_dir}")
        sys.exit(1)

    # Sort by base name then part number
    part_files.sort(key=lambda x: (x[0], x[1]))

    # Group by base name
    groups = {}
    for base, num, path in part_files:
        groups.setdefault(base, []).append((num, path))

    print(f"Found {len(groups)} original file(s) to merge")

    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    for base, files_in_group in groups.items():
        files_in_group.sort(key=lambda x: x[0])
        out_path = output_dir / f"{base}.md"
        print(f"  Merging {base}: {len(files_in_group)} parts -> {out_path.name}")

        all_content = []
        for num, path in files_in_group:
            all_content.append(path.read_bytes())

        combined = b''.join(all_content)
        out_path.write_bytes(combined)
        print(f"    {len(all_content)} parts, {len(combined)} chars total")

    print(f"Done: {output_file}")


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python merge_md.py <input_directory> <output.md>")
        sys.exit(1)

    input_dir = pathlib.Path(args[0])
    output_file = pathlib.Path(args[1])

    merge_md(input_dir, output_file)


if __name__ == "__main__":
    main()
