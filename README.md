# 图书库浏览器（BookReader）

> 一款 macOS 上的本地图书库管理工具，基于 PyQt6 开发。以树形目录展示图书分类，自动提取封面，支持文件名搜索、书目导出等功能。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow.svg)
[![Build](https://github.com/HonkerAcmen/BookReader/actions/workflows/build.yml/badge.svg)](https://github.com/HonkerAcmen/BookReader/actions/workflows/build.yml)

---

## ✨ 功能特性

- **📁 树形浏览** — 以文件夹为分类，层级展示图书库结构，支持懒加载与展开状态记忆
- **🖼️ 封面预览** — 自动提取 PDF、EPUB 及图片文件的封面，64×64 圆角缩略图，滚动时按需加载
- **🔍 文件名搜索** — 实时过滤当前目录树，带 300ms 防抖优化
- **📊 格式统计** — 后台线程统计各格式图书数量与总大小
- **📜 最近打开** — 记录最近打开的图书，一键回顾
- **📤 导出清单** — 导出 CSV / TXT 格式的书目清单（支持整个目录树或当前文件夹）
- **🎨 现代 UI** — 黑白扁平化设计、圆角风格、深色主题，悬浮高亮反馈
- **⚡ 性能优化** — 封面懒加载、双层缓存、后台线程提取，滚动流畅不卡顿

## 📦 下载

从 [Releases](https://github.com/HonkerAcmen/BookReader/releases) 页面下载最新版本的 `.dmg` 安装包。

> 首次打开若提示「无法打开」，右键点击应用 → 打开，或在「系统设置 → 隐私与安全性」中点击「仍要打开」。

## 🚀 快速开始

### 从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/HonkerAcmen/BookReader.git
cd BookReader

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行（可选：直接传入图书库文件夹路径）
python library_browser.py
python library_browser.py /Volumes/文件小助手/图书集成库   # 启动后直接打开指定目录
```

### 打包为 macOS 应用

```bash
# 安装 PyInstaller（requirements.txt 不含打包依赖）
pip install pyinstaller

# 构建
python build.py --clean
```

构建完成后，应用位于 `dist/图书库浏览器.app`。

> 也可直接运行 `python build.py`（跳过清理）。打 `v*` 标签推送后，GitHub Actions 会自动构建 arm64 / x86_64 双架构并发布到 Releases。

## 🛠️ 开发

### 项目结构

```
BookReader/
├── library_browser.py       # 主程序（约 1500 行，单文件应用）
├── build.py                 # PyInstaller 打包脚本
├── requirements.txt         # 运行依赖
├── 图书库浏览器.spec         # PyInstaller 配置（构建时生成）
├── setup.py                 # py2app 配置（备用打包方案）
├── .github/
│   └── workflows/
│       └── build.yml        # GitHub Actions CI：双架构构建 + 自动发布
├── .gitignore
├── LICENSE
└── README.md
```

### 核心技术

| 技术 | 用途 |
|------|------|
| PyQt6 | GUI 框架（QtWidgets / QtGui / QtCore） |
| PyMuPDF (fitz) | PDF 封面提取 |
| Pillow | 图像缩放与圆角处理 |
| PyInstaller | macOS 应用打包 |
| GitHub Actions | CI/CD 自动构建与发布 |

### 性能优化点

- **封面懒加载**：仅提取可视区域内的封面，滚动停止后延迟加载
- **双层缓存**：原始封面 + 圆角缩略图分离缓存，LRU 淘汰策略（上限 500 条）
- **后台线程**：封面提取、格式统计均在后台线程执行，不阻塞 UI
- **批量更新**：封面结果每帧批量回传（10 个/帧），减少 UI 刷新次数
- **搜索防抖**：输入停止 300ms 后才执行搜索，避免高频过滤

## ⌨️ 交互方式

### 双击与右键

| 操作 | 功能 |
|------|------|
| 双击文件 | 用系统默认应用打开图书 |
| 右键文件 | 打开 / 在访达中显示 / 复制路径 / 复制文件名 |
| 右键文件夹 | 在访达中显示 / 复制路径 / 展开全部子文件夹 / 导出此文件夹书目 |

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+F` | 聚焦搜索框 |
| `Ctrl+E` | 导出书目清单（CSV / TXT） |
| `Ctrl+R` | 刷新当前目录 |
| `Ctrl+Shift+C` | 复制当前选中路径 |
| `Enter` | 打开选中项 |
| `Esc` | 清除搜索 |

## 📋 支持格式

- **图书格式**：PDF、EPUB、DJVU、MOBI、AZW、AZW3
- **图片格式**：PNG、JPG、JPEG、WEBP、BMP、GIF

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建功能分支（`git checkout -b feature/AmazingFeature`）
3. 提交更改（`git commit -m 'Add some AmazingFeature'`）
4. 推送到分支（`git push origin feature/AmazingFeature`）
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 — 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI 框架
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF 处理
- [Pillow](https://python-pillow.org/) — 图像处理
- [PyInstaller](https://www.pyinstaller.org/) — 应用打包

---

如果这个项目对你有帮助，欢迎给个 ⭐️ Star 支持一下！
