# OCR 文档处理工具

## 启动图形界面

在 Windows 或 Linux 上安装 Python 3.13 及项目依赖后运行：

```bash
python -m ocr
```

界面支持选择输入目录、PDF/PNG/JPG 文件类型、文件名关键词和输出目录。关键词为空时会处理所选目录下所有匹配类型的文件；处理结果会生成 `result.csv`，OCR 原始输出也会保存到输出目录。
