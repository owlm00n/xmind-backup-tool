# XMind 备份与还原工具

将 XMind `.xmind` 文件备份为单个 `.md` 文件，并可还原回原始 `.xmind` 格式，**字节级精确复原**。同时提供大文件拆分/合并功能，用于绕过 Git 平台 5,000,000 字符限制。

## 目录结构

```
xmind-backup-tool/
├── xmind_batch.py       # 批量目录备份/还原
├── xmind2md.py          # 单个 XMind → 单个 MD 备份
├── md2xmind.py          # 单个 MD → XMind 还原
├── split_md.py          # 单个大 MD → 拆分为多个 chunk
├── merge_md.py          # 拆分后的 chunk → 合并为单个 MD
├── split_md_batch.py    # 批量：递归拆分所有 .md 文件
└── merge_md_batch.py    # 批量：递归合并所有拆分后的 .md 文件
```

批量操作默认排除 `AI/` 目录，避免循环处理。

## 脚本说明

| 脚本 | 功能 |
|---|---|
| `xmind2md.py` | 读取 `.xmind` 文件（ZIP 格式），将内部所有文件提取为代码块，合并到单个 `.md` 中。二进制内容使用 base64 编码。 |
| `md2xmind.py` | 从 `.md` 备份重建 `.xmind` 文件。解析代码块，解码 base64，重建 ZIP 归档。 |
| `xmind_batch.py` | 递归扫描目录中的 `.xmind`（备份）或 `.md`（还原）文件，逐个调用单文件脚本处理。 |
| `split_md.py` | 将单个大 MD 文件拆分为 `_partNNN.md` 块，在 `### 文件` 边界处分割，保留 `\r\n` 行尾。按字符数计算（上限：4,500,000 字符）。 |
| `merge_md.py` | 将 `_partNNN.md` 合并回单个 MD，与原始文件字节级一致。 |
| `split_md_batch.py` | 递归查找所有 `.md` 文件，拆分大文件。保留子目录结构。 |
| `merge_md_batch.py` | 递归查找 `_partNNN.md` 文件（和未拆分的原始文件），合并还原。同时处理拆分和未拆分文件。 |

## 安装

无需额外依赖，仅使用 Python 3 标准库。确保 `python3`（或 `python`）在 PATH 中即可。

## 使用方法

### XMind 备份 / 还原

```bash
# 单文件备份
python xmind2md.py "my-mindmap.xmind" "backup.md"

# 单文件还原
python md2xmind.py "backup.md" "restored.xmind"

# 批量操作
python xmind_batch.py backup <输入目录> <输出目录>
python xmind_batch.py restore <输入目录> <输出目录>
python xmind_batch.py backup . /tmp/xmind_bak -b /自定义路径/xmind2md.py -r /自定义路径/md2xmind.py
```

### MD 文件拆分 / 合并

用于 Git 平台限制 5,000,000 字符的场景：

```bash
# 单个文件拆分（输出到目录）
python split_md.py "large_backup.md" ./output_dir

# 批量拆分（递归处理输入目录下的所有 .md 文件）
python split_md_batch.py <输入目录> <输出目录>

# 批量合并（递归合并拆分后的文件）
python merge_md_batch.py <输入目录> <输出目录>
```

### 字节级精确复原

- 拆分/合并保证与原始 MD 文件**字节级完全一致**
- 在 `### 文件 N:` 边界处分割，保持单个文件区块完整
- 使用字符数（非字节数）进行分块 — 正确处理中文/UTF-8 文本
- 通过 `splitlines(keepends=True)` 和 `read_bytes`/`write_bytes` 保留原始 `\r\n` 行尾
- 未超过限制的原始文件名保持不变（不带 `_partNNN` 后缀）

### 拆分 / 合并使用示例

```bash
# 拆分目录下所有 .md 文件
python split_md_batch.py D:/Notes/xmind D:/Notes/xmind_split

# 合并还原
python merge_md_batch.py D:/Notes/xmind_split D:/Notes/xmind_merge

# 自定义大小限制（字符数）
python split_md_batch.py D:/Notes/xmind D:/Notes/xmind_split --max-size-bytes 4000000
```

### XMind 还原的字节级精确保证

这些脚本保证 `.xmind` 文件的**字节级完全一致**还原。关键设计：

- **`wb` 写入模式**：`xmind2md.py` 使用 `open(path, 'wb')` + 字节列表写入 `.md`，避免平台相关的换行符转换
- **`newline='\n'` 读取模式**：`md2xmind.py` 使用 `open(path, 'r', newline='\n')` 读取 `.md`，防止 Windows 上 `\r\n` → `\n` 转换
- **`\r\n` 保留**：`.xmind` 内部的 XML 内容使用 `\r\n` 行尾，在代码块中逐字节保留，还原时精确恢复
- **ZipInfo 写入**：`md2xmind.py` 使用 `zipfile.ZipInfo` 写入 ZIP 条目，绕过 `writestr` 的自动换行转换
- **不使用正则匹配代码块**：通过 `str.find('```')` 查找块边界，避免内容中包含反引号或特殊字符时的正则陷阱

## 注意事项

- 不要用会静默将 `\r\n` 转换为 `\n` 的编辑器手动修改 `.md` 文件，否则会破坏还原的精确性
- 批量脚本默认排除 `AI/` 子目录，防止将备份/还原脚本本身当作数据处理
- 拆分后的文件使用 `_partNNN.md` 命名。未拆分文件（未超限）保留原始文件名
