#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Batch merge: recursively find all split MD files in input_dir
and merge them back into complete .md files under output_dir.

Handles both:
- Split files: *_partNNN.md
- Unsplit files (original names kept): *.md (not _part*)

Preserves subdirectory structure.

Usage:
  python merge_md_batch.py <input_directory> <output_directory>
"""

import os
import sys
import pathlib
import re


def batch_merge(input_root: pathlib.Path, output_root: pathlib.Path):
    all_md = []
    for p in input_root.rglob('*'):
        if not p.is_file():
            continue
        if not p.name.endswith('.md'):
            continue

        # Check if it's a split part file
        m = re.match(r'^(.+)_part(\d{3})\.md$', p.name)
        if m:
            all_md.append(('part', p, m.group(1), int(m.group(2))))
        else:
            # Unsplit file — keep original name
            all_md.append(('orig', p, p.stem, 0))

    if not all_md:
        print(f"No .md files found in {input_root}")
        return

    # Group by (parent, base_name)
    groups = {}
    for kind, path, name, num in all_md:
        rel = path.relative_to(input_root)
        parent = rel.parent
        groups.setdefault((parent, name), []).append((num, path))

    print(f"Found {len(groups)} original file(s) to merge\n")

    total_merged = 0
    for (parent, name), files_in_group in sorted(groups.items()):
        files_in_group.sort(key=lambda x: x[0])
        out_path = output_root / parent / f"{name}.md"
        out_path.parent.mkdir(parents=True, exist_ok=True)

        all_content = []
        for num, fp in files_in_group:
            all_content.append(fp.read_bytes())

        combined = b''.join(all_content)
        out_path.write_bytes(combined)
        total_merged += 1
        path_str = str(parent)
        if path_str == '.':
            path_str = ''
        print(f"[{total_merged}/{len(groups)}] {path_str}/{name} -> {out_path.name} ({len(combined)} bytes)")

    print(f"\nDone: {len(groups)} files merged")


def main():
    if len(sys.argv) < 3:
        print("Usage: python merge_md_batch.py <input_directory> <output_directory>")
        sys.exit(1)

    input_root = pathlib.Path(sys.argv[1])
    output_root = pathlib.Path(sys.argv[2])

    if not input_root.is_dir():
        print(f"ERROR: Directory not found: {input_root}")
        sys.exit(1)

    batch_merge(input_root, output_root)


if __name__ == "__main__":
    main()
