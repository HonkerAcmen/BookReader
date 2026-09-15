# 图书库浏览器

> 一款现代化的本地图书库管理工具，基于 PyQt6 开发，支持封面预览、搜索、分类浏览等功能。

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-yellow.svg)

---

## ✨ 功能特性

- **📁 树形浏览** — 以文件夹为分类，层级展示你的图书库
- **🖼️ 封面预览** — 自动提取 PDF、EPUB 及图片文件的封面，64x64 圆角缩略图
- **🔍 全文搜索** — 支持按文件名快速搜索，带防抖优化
- **📊 格式统计** — 实时统计各格式图书数量
- **📜 最近打开** — 记录最近打开的图书，一键回顾
- **📤 导出清单** — 支持导出 CSV / TXT 格式的书目清单
- **🎨 现代UI** — 黑白扁平化设计，圆角风格，深色主题
- **⚡ 性能优化** — 懒加载封面、后台线程提取、缓存机制，滚动流畅

## 📦 下载

从 [Releases](https://github.com/yourname/library-browser/releases) 页面下载最新版本的 `.dmg` 安装包。

> 首次打开时若提示「无法打开」，请右键 → 打开，或在「系统设置 → 隐私与安全性」中点击「仍要打开」。

## 🚀 快速开始

### 从源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/yourname/library-browser.git
cd library-browser

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python library_browser.py
```

### 打包为 macOS 应用

```bash
python build.py --clean
```

构建完成后，应用位于 `dist/图书库浏览器.app`。

## 🛠️ 开发

### 项目结构

```
library-browser/
├── library_browser.py       # 主程序
├── build.py                 # 打包脚本
├── requirements.txt         # 依赖列表
├── 图书库浏览器.spec         # PyInstaller 配置
├── setup.py                 # py2app 配置
├── .github/
│   └── workflows/
│       └── build.yml        # GitHub Actions CI
├── .gitignore
├── LICENSE
└── README.md
```

### 核心技术

| 技术 | 用途 |
|------|------|
| PyQt6 | GUI 框架 |
| PyMuPDF | PDF 封面提取 |
| Pillow | 图像处理 |
| PyInstaller | 应用打包 |
| GitHub Actions | CI/CD 自动构建 |

### 性能优化点

- **封面懒加载**：只提取可视区域内的封面，滚动停止后延迟加载
- **双层缓存**：原始封面 + 圆角缩略图分离缓存，LRU 淘汰策略
- **后台线程**：封面提取、格式统计均在后台线程执行，不阻塞 UI
- **批量更新**：封面结果每帧批量回传，减少 UI 刷新次数
- **搜索防抖**：输入停止 300ms 后才执行搜索

## ⌨️ 快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+F` | 聚焦搜索框 |
| `Ctrl+E` | 导出书目清单 |
| `Ctrl+R` | 刷新 |
| `Ctrl+Shift+C` | 复制当前选中路径 |
| `Enter` | 打开选中项 |
| `Esc` | 清除搜索 |

## 📋 支持格式

- **图书格式**：PDF、EPUB、DJVU、MOBI、AZW、AZW3
- **图片格式**：PNG、JPG、JPEG、WEBP、BMP、GIF

## 🤝 贡献

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建你的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 — 详见 [LICENSE](LICENSE) 文件。

## 🙏 致谢

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — GUI 框架
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) — PDF 处理
- [Pillow](https://python-pillow.org/) — 图像处理
- [PyInstaller](https://www.pyinstaller.org/) — 应用打包

---

如果这个项目对你有帮助，欢迎给个 ⭐️ Star 支持一下！
