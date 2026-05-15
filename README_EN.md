# XMind Backup & Restore Tools

Back up XMind `.xmind` files to a single `.md` and restore them back with **byte-level fidelity**. Split and merge large MD files to work around Git platform character limits (5,000,000 chars).

## Directory Structure

```
xmind-backup-tool/
├── xmind_batch.py       # Batch backup/restore for directories
├── xmind2md.py          # Single XMind -> single MD backup
├── md2xmind.py          # Single MD -> XMind restore
├── split_md.py          # Single large MD -> split into chunks
├── merge_md.py          # Split chunks -> merge back into single MD
├── split_md_batch.py    # Batch: recursively split all .md files
└── merge_md_batch.py    # Batch: recursively merge all split .md files
```

The `AI/` directory is excluded from batch operations to avoid circular processing.

## Scripts

| Script | Purpose |
|---|---|
| `xmind2md.py` | Reads a `.xmind` file (ZIP format), extracts every inner file into code blocks inside a single `.md`. Binary content is base64-encoded. |
| `md2xmind.py` | Reconstructs a `.xmind` file from the `.md` backup. Parses code blocks, decodes base64, rebuilds the ZIP archive. |
| `xmind_batch.py` | Scans a directory tree for `.xmind` (backup) or `.md` (restore) files and runs the single-file script on each. |
| `split_md.py` | Splits a large MD file into `_partNNN.md` chunks at `### 文件` boundaries, preserving `\r\n` line endings. Character-count based (limit: 4,500,000 chars). |
| `merge_md.py` | Merges `_partNNN.md` chunks back into a single MD. Byte-identical to original. |
| `split_md_batch.py` | Recursively finds all `.md` files, splits large ones into chunks. Preserves subdirectory structure. |
| `merge_md_batch.py` | Recursively finds `_partNNN.md` files (and unsplit originals), merges them. Handles both split and unsplit files. |

## Installation

No dependencies beyond the Python 3 standard library. Just make sure `python3` (or `python`) is on your PATH.

## Usage

### XMind Backup / Restore

```bash
# Single-file backup
python xmind2md.py "my-mindmap.xmind" "backup.md"

# Single-file restore
python md2xmind.py "backup.md" "restored.xmind"

# Batch operations
python xmind_batch.py backup <input_dir> <output_dir>
python xmind_batch.py restore <input_dir> <output_dir>
python xmind_batch.py backup . /tmp/xmind_bak -b /custom/xmind2md.py -r /custom/md2xmind.py
```

### Split / Merge MD Files

For Git platforms that limit file sizes to 5,000,000 characters:

```bash
# Single file split (output to directory)
python split_md.py "large_backup.md" ./output_dir

# Batch split (recursively under input directory)
python split_md_batch.py <input_directory> <output_directory>

# Batch merge (recursively merge split files)
python merge_md_batch.py <input_directory> <output_directory>
```

### Roundtrip Fidelity

- Split/merge guarantee **byte-level identical** restoration of original MD files
- Splits at `### 文件 N:` boundaries to keep individual file sections intact
- Uses character count (not bytes) for chunking — Chinese/UTF-8 text handled correctly
- Preserves original `\r\n` line endings via `splitlines(keepends=True)` and `read_bytes`/`write_bytes`
- Files under the size limit keep their original names (no `_partNNN` suffix)

### MD Split / Merge Usage Examples

```bash
# Split all .md files under a directory
python split_md_batch.py D:/Notes/xmind D:/Notes/xmind_split

# Merge back
python merge_md_batch.py D:/Notes/xmind_split D:/Notes/xmind_merge

# Custom max size (in characters)
python split_md_batch.py D:/Notes/xmind D:/Notes/xmind_split --max-size-bytes 4000000
```

## Roundtrip Fidelity (XMind)

These scripts guarantee **byte-level identical** restoration of the original `.xmind` file. Key design constraints:

- **`wb` write mode**: `xmind2md.py` writes the output `.md` via `open(path, 'wb')` using a byte list to avoid any platform-dependent newline translation.
- **`newline='\n'` read mode**: `md2xmind.py` reads the `.md` with `open(path, 'r', newline='\n')` to prevent `\r\n` -> `\n` conversion on Windows.
- **\r\n preservation**: XML content inside `.xmind` uses `\r\n` line endings. These are preserved byte-for-byte inside code blocks and decoded back exactly on restore.
- **ZipInfo for writing**: `md2xmind.py` uses `zipfile.ZipInfo` to write ZIP entries, bypassing `writestr`'s automatic newline conversion.
- **No regex for code blocks**: Block boundaries are found via `str.find('```')` to avoid regex pitfalls with content that contains backticks or special characters.

## Caveats

- Do not manually edit the `.md` file in an editor that silently converts `\r\n` to `\n`, as this will break roundtrip fidelity.
- The batch script excludes the `AI/` subdirectory by default to prevent processing backup/restore scripts as data files.
- Split files use `_partNNN.md` naming. Unsplit files (under size limit) keep their original names.
