#!/usr/bin/env python3
"""
图书库浏览器 - 基于 PyQt6
现代扁平化设计 + 封面图展示
性能优化版：低分辨率封面提取 + 缓存分离 + 批量UI更新
"""

import sys
import os
import subprocess
import json
import csv
import time
import zipfile
import threading
from pathlib import Path
from collections import Counter, OrderedDict

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem, QFileDialog,
    QLabel, QLineEdit, QMessageBox, QMenu, QSplitter,
    QListWidget, QListWidgetItem, QStatusBar,
    QTreeWidgetItemIterator, QStyledItemDelegate, QStyleOptionViewItem,
    QAbstractItemView
)
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QObject, QPoint, QModelIndex
from PyQt6.QtGui import (
    QFont, QColor, QAction, QKeySequence, QShortcut,
    QPixmap, QImage, QPainter, QPen, QPainterPath, QIcon, QBrush
)

# ==================== 主题 ====================

THEME = {
    "bg":           "#0d0d0d",
    "bg_sidebar":   "#111111",
    "surface":      "#161616",
    "hover":        "#252525",
    "hover_border": "#3a3a3a",
    "selected":     "#2d2d2d",
    "text":         "#e8e8e8",
    "text_dim":     "#a0a0a0",
    "text_faint":   "#707070",
    "accent":       "#ffffff",
    "danger":       "#ff4444",
    "border":       "#2e2e2e",
    "border_light": "#3a3a3a",
    "radius":       "8px",
    "row_height":   72,
    "cover_size":   64,
}

FONT_FAMILY = "PingFang SC"

BOOK_EXTS = {".pdf", ".epub", ".djvu", ".mobi", ".azw", ".azw3"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

ROLE_PATH    = Qt.ItemDataRole.UserRole + 1
ROLE_LOADED  = Qt.ItemDataRole.UserRole + 2
ROLE_ISDIR   = Qt.ItemDataRole.UserRole + 3
ROLE_NAME    = Qt.ItemDataRole.UserRole + 4
ROLE_COUNT   = Qt.ItemDataRole.UserRole + 5

CONFIG_FILE = Path.home() / ".library_browser_config.json"
SKIP_DIRS = {"code", ".git", "__pycache__", ".Trash"}


# ==================== 工具函数 ====================

def format_size(size):
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    elif size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    else:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"


def make_font(size, bold=False):
    return QFont(FONT_FAMILY, size, QFont.Weight.Bold if bold else QFont.Weight.Normal)


# ==================== 封面管理器 ====================

class CoverManager:
    """封面提取与缓存，分离原始图和缩略图缓存"""

    MAX_CACHE = 500

    def __init__(self):
        self.cache = OrderedDict()           # path -> QImage (原始)
        self.thumb_cache = OrderedDict()      # path -> QImage (64x64圆角缩略图)
        self.default_covers = {}
        self._lock = threading.Lock()
        self._generate_default_covers()

    def get_cover(self, file_path):
        with self._lock:
            if file_path in self.cache:
                self.cache.move_to_end(file_path)
                return self.cache[file_path]

        cover = self._extract_cover(file_path)

        with self._lock:
            if cover is not None and not cover.isNull():
                self.cache[file_path] = cover
                if len(self.cache) > self.MAX_CACHE:
                    self.cache.popitem(last=False)
            else:
                ext = Path(file_path).suffix.lower().lstrip(".")
                cover = self.default_covers.get(ext, self.default_covers.get("default"))
        return cover

    def get_thumbnail(self, file_path, size):
        """获取已处理的圆角缩略图，避免重复处理"""
        with self._lock:
            if file_path in self.thumb_cache:
                self.thumb_cache.move_to_end(file_path)
                return self.thumb_cache[file_path]

        cover = self.get_cover(file_path)
        thumb = make_rounded_thumbnail_image(cover, size)

        with self._lock:
            if thumb and not thumb.isNull():
                self.thumb_cache[file_path] = thumb
                if len(self.thumb_cache) > self.MAX_CACHE:
                    self.thumb_cache.popitem(last=False)
            else:
                ext = Path(file_path).suffix.lower().lstrip(".")
                thumb = self.default_covers.get(ext, self.default_covers.get("default"))
        return thumb

    def _extract_cover(self, file_path):
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return self._extract_pdf_cover(file_path)
        elif ext == ".epub":
            return self._extract_epub_cover(file_path)
        elif ext in IMAGE_EXTS:
            return self._load_image(file_path)
        return None

    def _extract_pdf_cover(self, path):
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                import pymupdf
                doc = pymupdf.open(path)
                if len(doc) > 0:
                    page = doc[0]
                    # 用0.75倍分辨率，64x64缩略图足够
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(0.75, 0.75))
                    img_data = pix.tobytes("png")
                    img = QImage.fromData(img_data, "PNG")
                    if not img.isNull():
                        doc.close()
                        return img
                doc.close()
            except Exception:
                pass
        return None

    def _extract_epub_cover(self, path):
        try:
            with zipfile.ZipFile(path, "r") as zf:
                candidates = []
                for name in zf.namelist():
                    lower = name.lower()
                    if lower.endswith((".jpg", ".jpeg", ".png")):
                        if "cover" in lower or "title" in lower:
                            candidates.insert(0, name)
                        else:
                            candidates.append(name)
                for name in candidates[:5]:
                    data = zf.read(name)
                    img = QImage.fromData(data)
                    if not img.isNull():
                        return img
        except Exception:
            pass
        return None

    def _load_image(self, path):
        try:
            img = QImage(path)
            if not img.isNull():
                return img
        except Exception:
            pass
        return None

    def _generate_default_covers(self):
        for ext in ["pdf", "epub", "djvu", "mobi", "azw", "azw3", "default"]:
            self.default_covers[ext] = self._draw_default_cover(ext.upper())

    def _draw_default_cover(self, label):
        w, h = 64, 64
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(QColor(THEME["surface"]))

        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(THEME["border_light"]))
        pen.setWidth(2)
        p.setPen(pen)
        p.setBrush(QBrush(QColor(THEME["surface"])))
        p.drawRoundedRect(2, 2, w - 4, h - 4, 6, 6)

        p.setPen(QColor(THEME["text_dim"]))
        p.setFont(QFont(FONT_FAMILY, 10, QFont.Weight.Bold))
        p.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, label)

        p.end()
        return img


# ==================== 后台封面提取 ====================

class CoverExtractor(QObject):
    """后台提取封面，批量回主线程更新"""
    cover_ready = pyqtSignal(str, object, object)

    def __init__(self, cover_manager):
        super().__init__()
        self.cover_manager = cover_manager
        self._queue = []
        self._lock = threading.Lock()
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

        self._result_timer = QTimer()
        self._result_timer.setInterval(30)   # ~33fps
        self._result_timer.timeout.connect(self._drain_results)
        self._result_timer.setSingleShot(False)
        self._results = []
        self._results_lock = threading.Lock()

    def enqueue_file(self, file_path, tree_item):
        with self._lock:
            self._queue.append(("file", file_path, tree_item))

    def clear(self):
        with self._lock:
            self._queue.clear()
        with self._results_lock:
            self._results.clear()

    def start(self):
        if not self._result_timer.isActive():
            self._result_timer.start()

    def _run(self):
        while self._running:
            with self._lock:
                if not self._queue:
                    task = None
                else:
                    task = self._queue.pop(0)

            if task is None:
                time.sleep(0.01)
                continue

            try:
                if task[0] == "file":
                    _, file_path, item = task
                    # 直接获取缩略图（有独立缓存）
                    thumb = self.cover_manager.get_thumbnail(file_path, THEME["cover_size"])
                    if thumb and not thumb.isNull():
                        with self._results_lock:
                            self._results.append((file_path, thumb, item))
            except Exception:
                pass

            time.sleep(0.001)

    def _drain_results(self):
        with self._results_lock:
            # 每帧最多取10个，大幅提升吞吐
            results = self._results[:10]
            self._results = self._results[10:]

        for path, img, item in results:
            if item and item.treeWidget() is not None:
                self.cover_ready.emit(path, img, item)

        if not self._results:
            self._result_timer.stop()


# ==================== 图标绘制 ====================

def make_rounded_thumbnail_image(image, size=64):
    """圆角正方形封面缩略图"""
    if image is None or image.isNull():
        return QImage()

    result = QImage(size, size, QImage.Format.Format_ARGB32)
    result.fill(Qt.GlobalColor.transparent)

    p = QPainter(result)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, 8, 8)
    p.setClipPath(path)

    src = image.scaled(
        size, size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation
    )
    x = (size - src.width()) // 2
    y = (size - src.height()) // 2
    p.drawImage(x, y, src)

    p.setClipping(False)
    pen = QPen(QColor(0, 0, 0, 60))
    pen.setWidth(1)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRoundedRect(0, 0, size, size, 8, 8)

    p.end()
    return result


# ==================== 样式表 ====================

def build_stylesheet():
    t = THEME
    return f"""
    QMainWindow {{
        background-color: {t["bg"]};
    }}

    QPushButton#primary {{
        background-color: {t["accent"]};
        color: {t["bg"]};
        border: none;
        border-radius: {t["radius"]};
        padding: 10px 24px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton#primary:hover {{ background-color: #d0d0d0; }}
    QPushButton#primary:pressed {{ background-color: #b0b0b0; }}
    QPushButton#primary:disabled {{
        background-color: #2a2a2a;
        color: {t["text_faint"]};
    }}

    QPushButton#ghost {{
        background-color: transparent;
        color: {t["text_dim"]};
        border: none;
        border-radius: {t["radius"]};
        padding: 8px 16px;
        font-size: 12px;
    }}
    QPushButton#ghost:hover {{
        background-color: {t["hover"]};
        color: {t["text"]};
    }}
    QPushButton#ghost:disabled {{
        color: {t["text_faint"]};
    }}

    QLineEdit {{
        background-color: {t["surface"]};
        border: none;
        border-radius: {t["radius"]};
        padding: 10px 18px;
        color: {t["text"]};
        font-size: 14px;
        selection-background-color: #444;
    }}
    QLineEdit:focus {{ background-color: #1f1f1f; }}
    QLineEdit::placeholder {{ color: {t["text_faint"]}; }}

    QTreeWidget {{
        background-color: {t["bg"]};
        border: none;
        color: {t["text"]};
        outline: none;
    }}
    QTreeWidget::item {{
        padding: 2px 4px;
        min-height: {t["row_height"]}px;
        max-height: {t["row_height"]}px;
        border: none;
        border-left: 3px solid transparent;
    }}
    QTreeWidget::item:hover {{
        background-color: {t["hover"]};
        border-left: 3px solid {t["hover_border"]};
    }}
    QTreeWidget::item:selected {{
        background-color: {t["selected"]};
        color: {t["accent"]};
        border-left: 3px solid {t["accent"]};
    }}
    QTreeWidget::branch:has-children:closed {{ background-color: {t["bg"]}; }}
    QTreeWidget::branch:has-children:open {{ background-color: {t["bg"]}; }}
    QTreeWidget::branch:!has-children {{ background-color: {t["bg"]}; }}
    QHeaderView::section {{
        background-color: {t["bg"]};
        color: {t["text_faint"]};
        padding: 0px 0px 6px 12px;
        border: none;
        font-size: 10px;
        font-weight: 600;
    }}

    QListWidget {{
        background-color: {t["bg_sidebar"]};
        border: none;
        color: {t["text"]};
        outline: none;
    }}
    QListWidget::item {{
        padding: 8px 8px;
        border-bottom: none;
        border-left: 3px solid transparent;
    }}
    QListWidget::item:hover {{
        background-color: {t["hover"]};
        border-left: 3px solid {t["hover_border"]};
    }}
    QListWidget::item:selected {{
        background-color: {t["selected"]};
        color: {t["accent"]};
        border-left: 3px solid {t["accent"]};
    }}

    QSplitter::handle {{ background-color: #1a1a1a; width: 1px; }}

    QLabel#title {{ color: {t["accent"]}; font-size: 20px; font-weight: 700; }}
    QLabel#section {{
        color: {t["text_dim"]};
        font-size: 10px;
        font-weight: 700;
        padding: 12px 0px 4px 0px;
    }}
    QLabel#stats {{ color: {t["text_dim"]}; font-size: 11px; }}
    QLabel#card {{ color: {t["text_dim"]}; font-size: 11px; padding: 10px 14px; }}
    QLabel#hint {{ color: {t["text_faint"]}; font-size: 10px; }}

    QStatusBar {{
        background-color: transparent;
        color: {t["text_faint"]};
        border: none;
        font-size: 10px;
    }}

    QScrollBar:vertical {{ background: transparent; width: 6px; margin: 4px 0; }}
    QScrollBar::handle:vertical {{ background: #2a2a2a; min-height: 40px; border-radius: 3px; }}
    QScrollBar::handle:vertical:hover {{ background: #3a3a3a; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 6px; margin: 0 4px; }}
    QScrollBar::handle:horizontal {{ background: #2a2a2a; min-width: 40px; border-radius: 3px; }}
    QScrollBar::handle:horizontal:hover {{ background: #3a3a3a; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

    QMenu {{
        background-color: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: {t["radius"]};
        padding: 6px;
    }}
    QMenu::item {{ padding: 8px 28px 8px 16px; border-radius: 4px; color: {t["text"]}; font-size: 13px; }}
    QMenu::item:selected {{ background-color: {t["hover"]}; color: {t["accent"]}; }}
    QMenu::separator {{ height: 1px; background: #222; margin: 4px 8px; }}

    QMessageBox {{ background-color: {t["bg"]}; }}
    QMessageBox QLabel {{ color: {t["text"]}; font-size: 14px; }}
    QMessageBox QPushButton {{
        background-color: #1a1a1a;
        color: {t["text"]};
        border: none;
        border-radius: 6px;
        padding: 8px 20px;
        min-width: 64px;
        font-size: 13px;
    }}
    QMessageBox QPushButton:hover {{ background-color: #2a2a2a; }}
    QFileDialog {{ background-color: {t["bg"]}; color: {t["text"]}; }}
    """


# ==================== 主窗口 ====================

FOLDER_ICON = "\u25B8"
FILE_ICON = "\u00B7"
BOOK_ICON = "\u25AB"
RECENT_ICON = "\u25CB"


class LibraryBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_folder = None
        self.total_files = 0
        self.total_folders = 0
        self.format_stats = Counter()
        self.recent_books = []
        self.expanded_paths = set()
        self.search_active = False
        self._searching = False
        self.all_file_items = []
        self._path_cache = {}

        # 封面懒加载定时器
        self._visible_cover_timer = QTimer()
        self._visible_cover_timer.setInterval(150)
        self._visible_cover_timer.setSingleShot(True)
        self._visible_cover_timer.timeout.connect(self._load_visible_covers)
        self._cover_pending = set()

        # 搜索防抖定时器（复用，不每次新建）
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(300)
        self._search_timer.timeout.connect(self._do_search)

        self.cover_manager = CoverManager()
        self._cover_extractor = CoverExtractor(self.cover_manager)
        self._cover_extractor.cover_ready.connect(self._on_cover_ready)

        self.init_ui()
        self.load_config()

    # ==================== UI 初始化 ====================

    def init_ui(self):
        self.setWindowTitle("图书库")
        self.setMinimumSize(960, 600)
        self.resize(1240, 780)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ---------- 顶栏 ----------
        topbar = QWidget()
        topbar.setMinimumHeight(56)
        topbar_layout = QHBoxLayout(topbar)
        topbar_layout.setContentsMargins(20, 12, 20, 12)
        topbar_layout.setSpacing(10)

        title = QLabel("图书库")
        title.setObjectName("title")
        title.setFont(make_font(20, bold=True))
        topbar_layout.addWidget(title)

        self.path_label = QLineEdit()
        self.path_label.setReadOnly(True)
        self.path_label.setPlaceholderText("未选择文件夹")
        self.path_label.setFont(make_font(11))
        topbar_layout.addWidget(self.path_label, stretch=1)

        self.btn_refresh = QPushButton("刷新")
        self.btn_refresh.setObjectName("ghost")
        self.btn_refresh.setFont(make_font(12))
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.clicked.connect(self.refresh)
        topbar_layout.addWidget(self.btn_refresh)

        self.btn_collapse = QPushButton("全部收起")
        self.btn_collapse.setObjectName("ghost")
        self.btn_collapse.setFont(make_font(12))
        self.btn_collapse.setEnabled(False)
        self.btn_collapse.clicked.connect(self.collapse_all)
        topbar_layout.addWidget(self.btn_collapse)

        self.btn_export = QPushButton("导出")
        self.btn_export.setObjectName("ghost")
        self.btn_export.setFont(make_font(12))
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self.export_list)
        topbar_layout.addWidget(self.btn_export)

        self.btn_select = QPushButton("选择文件夹")
        self.btn_select.setObjectName("primary")
        self.btn_select.setFont(make_font(13, bold=True))
        self.btn_select.clicked.connect(self.select_folder)
        topbar_layout.addWidget(self.btn_select)

        root.addWidget(topbar)

        # ---------- 搜索栏 ----------
        search_area = QWidget()
        search_layout = QHBoxLayout(search_area)
        search_layout.setContentsMargins(20, 0, 20, 8)
        search_layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("  搜索图书...")
        self.search_input.setFont(make_font(14))
        self.search_input.setMinimumHeight(42)
        self.search_input.textChanged.connect(self._on_search_input_changed)
        search_layout.addWidget(self.search_input, stretch=1)

        self.btn_clear_search = QPushButton("清除")
        self.btn_clear_search.setObjectName("ghost")
        self.btn_clear_search.setFont(make_font(12))
        self.btn_clear_search.setMinimumHeight(42)
        self.btn_clear_search.clicked.connect(self.clear_search)
        search_layout.addWidget(self.btn_clear_search)

        root.addWidget(search_area)

        # ---------- 统计行 ----------
        stats_area = QWidget()
        stats_layout = QHBoxLayout(stats_area)
        stats_layout.setContentsMargins(20, 0, 20, 4)

        self.stats_label = QLabel("")
        self.stats_label.setObjectName("stats")
        self.stats_label.setFont(make_font(11))
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        root.addWidget(stats_area)

        # ---------- 主区域 ----------
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # 左侧：文件树
        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(12, 0, 0, 0)
        tree_layout.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["名称", "格式", "大小", ""])
        self.tree.setFont(make_font(13))
        self.tree.setIndentation(24)
        self.tree.setAlternatingRowColors(False)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_context_menu)
        self.tree.setRootIsDecorated(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setExpandsOnDoubleClick(False)
        self.tree.setIconSize(QSize(THEME["cover_size"], THEME["cover_size"]))
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.setAnimated(False)

        header = self.tree.header()
        header.resizeSection(0, 560)
        header.resizeSection(1, 50)
        header.resizeSection(2, 80)
        header.resizeSection(3, 50)

        self.tree.itemExpanded.connect(self.on_item_expanded)
        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.itemCollapsed.connect(self.on_item_collapsed)
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.verticalScrollBar().valueChanged.connect(
            lambda: self._visible_cover_timer.start()
        )
        tree_layout.addWidget(self.tree)
        splitter.addWidget(tree_container)

        # 右侧面板
        sidebar = QWidget()
        sidebar.setStyleSheet(f"background-color: {THEME['bg_sidebar']};")
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 8, 12, 12)
        side_layout.setSpacing(2)

        recent_section = QLabel("最近打开")
        recent_section.setObjectName("section")
        recent_section.setFont(make_font(10, bold=True))
        side_layout.addWidget(recent_section)

        self.recent_list = QListWidget()
        self.recent_list.setFont(make_font(12))
        self.recent_list.itemDoubleClicked.connect(self.on_recent_item_clicked)
        side_layout.addWidget(self.recent_list, stretch=1)

        self.btn_clear_recent = QPushButton("清除记录")
        self.btn_clear_recent.setObjectName("ghost")
        self.btn_clear_recent.setFont(make_font(10))
        self.btn_clear_recent.clicked.connect(self.clear_recent)
        side_layout.addWidget(self.btn_clear_recent)

        stats_section = QLabel("格式统计")
        stats_section.setObjectName("section")
        stats_section.setFont(make_font(10, bold=True))
        side_layout.addWidget(stats_section)

        self.format_stats_label = QLabel("暂无数据")
        self.format_stats_label.setObjectName("card")
        self.format_stats_label.setFont(make_font(11))
        self.format_stats_label.setWordWrap(True)
        side_layout.addWidget(self.format_stats_label)

        side_layout.addStretch()

        splitter.addWidget(sidebar)
        splitter.setSizes([900, 280])
        splitter.setStretchFactor(0, 1)
        root.addWidget(splitter, stretch=1)

        # ---------- 底部提示 ----------
        hint = QLabel("  双击打开  /  Ctrl+F 搜索  /  Ctrl+E 导出  /  右键更多操作")
        hint.setObjectName("hint")
        hint.setFont(make_font(10))
        hint.setStyleSheet(f"padding: 6px 20px;")
        root.addWidget(hint)

        self.setStyleSheet(build_stylesheet())
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(
            lambda: self.search_input.setFocus())
        QShortcut(QKeySequence("Return"), self).activated.connect(self.open_selected)
        QShortcut(QKeySequence("Ctrl+E"), self).activated.connect(self.export_list)
        QShortcut(QKeySequence("Escape"), self).activated.connect(self.clear_search)
        QShortcut(QKeySequence("Ctrl+R"), self).activated.connect(self.refresh)
        QShortcut(QKeySequence("Ctrl+Shift+C"), self).activated.connect(self.copy_selected_path)

    # ==================== 配置持久化 ====================

    def load_config(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.recent_books = cfg.get("recent_books", [])
                last_folder = cfg.get("last_folder")
                self.expanded_paths = set(cfg.get("expanded_paths", []))
                self.update_recent_list()
                if last_folder and os.path.isdir(last_folder):
                    self.current_folder = last_folder
                    self.path_label.setText(last_folder)
                    self.btn_refresh.setEnabled(True)
                    self.btn_collapse.setEnabled(True)
                    self.btn_export.setEnabled(True)
                    self.load_folder(last_folder, restore_expanded=True)
        except Exception as e:
            print(f"配置加载失败: {e}")

    def _load_config_no_folder(self):
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.recent_books = cfg.get("recent_books", [])
                self.expanded_paths = set(cfg.get("expanded_paths", []))
                self.update_recent_list()
        except Exception as e:
            print(f"配置加载失败: {e}")

    def save_config(self):
        try:
            cfg = {
                "recent_books": self.recent_books,
                "last_folder": self.current_folder,
                "expanded_paths": list(self.expanded_paths),
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"配置保存失败: {e}")

    # ==================== 文件夹选择与加载 ====================

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择文件夹", str(Path.home()),
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks
        )
        if folder:
            self.expanded_paths.clear()
            self.current_folder = folder
            self.path_label.setText(folder)
            self.btn_refresh.setEnabled(True)
            self.btn_collapse.setEnabled(True)
            self.btn_export.setEnabled(True)
            self.load_folder(folder)
            self.save_config()

    def refresh(self):
        if self.current_folder:
            self.load_folder(self.current_folder, restore_expanded=True)

    def collapse_all(self):
        self.tree.collapseAll()
        self.expanded_paths.clear()

    def load_folder(self, folder_path, restore_expanded=False):
        self.tree.clear()
        self.total_files = 0
        self.total_folders = 0
        self.all_file_items = []
        self._path_cache.clear()
        self._cover_pending.clear()
        self._cover_extractor.clear()
        self.stats_label.setText("正在扫描...")

        self._refresh_format_stats_async(folder_path)

        folder_path = Path(folder_path)
        try:
            entries = self._scan_dir(folder_path)
            for entry in entries:
                if entry.is_dir():
                    self._create_folder_item(self.tree, entry)
                    self.total_folders += 1
                elif entry.is_file():
                    self._create_file_item(self.tree, entry)
                    self.total_files += 1
        except Exception as e:
            QMessageBox.warning(self, "错误", f"扫描文件夹失败：\n{e}")

        self._update_stats()

        if restore_expanded and self.expanded_paths:
            QTimer.singleShot(100, self._restore_expanded_state)

    def _refresh_format_stats_async(self, folder_path):
        """在后台线程计算格式统计，不阻塞 UI"""
        def worker():
            stats = Counter()
            try:
                for dirpath, dirnames, filenames in os.walk(folder_path):
                    dirnames[:] = [d for d in dirnames
                                   if d not in SKIP_DIRS and not d.startswith("._")]
                    for f in filenames:
                        if f.startswith("._"):
                            continue
                        ext = os.path.splitext(f)[1].lower().lstrip(".")
                        stats[ext.upper() if ext else "无扩展名"] += 1
            except Exception:
                pass
            QTimer.singleShot(0, lambda: self._on_stats_ready(stats))

        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def _on_stats_ready(self, stats):
        self.format_stats = stats
        self._update_stats()

    def _scan_dir(self, dir_path):
        entries = []
        for entry in dir_path.iterdir():
            if entry.name.startswith("._") or entry.name == ".DS_Store":
                continue
            if entry.name in SKIP_DIRS and entry.is_dir():
                continue
            entries.append(entry)
        entries.sort(key=lambda x: (not x.is_dir(), x.name.lower()))
        return entries

    def _create_folder_item(self, parent, dir_path):
        item = QTreeWidgetItem(parent)
        item.setText(0, f"  {FOLDER_ICON}  {dir_path.name}")
        item.setText(1, "")
        item.setText(2, "")
        item.setText(3, "")
        item.setData(0, ROLE_PATH, str(dir_path))
        item.setData(0, ROLE_LOADED, False)
        item.setData(0, ROLE_ISDIR, True)
        item.setData(0, ROLE_NAME, dir_path.name)
        item.setData(0, ROLE_COUNT, 0)
        self._path_cache[str(dir_path)] = item
        item.setFont(0, make_font(13, bold=True))
        item.setForeground(0, QColor(THEME["text"]))
        item.setForeground(1, QColor(THEME["text_faint"]))
        item.setForeground(2, QColor(THEME["text_faint"]))
        item.setForeground(3, QColor(THEME["text_faint"]))

        dummy = QTreeWidgetItem(item)
        dummy.setText(0, "      \u2022 \u2022 \u2022")
        dummy.setForeground(0, QColor(THEME["text_faint"]))
        dummy.setData(0, ROLE_PATH, "__dummy__")

        return item

    def _create_file_item(self, parent, file_path):
        item = QTreeWidgetItem(parent)
        ext = file_path.suffix.lower()
        icon = BOOK_ICON if ext in BOOK_EXTS else FILE_ICON
        item.setText(0, f"  {icon}  {file_path.name}")
        item.setText(1, ext.lstrip(".").upper() if ext else "-")
        try:
            size = file_path.stat().st_size
            item.setText(2, format_size(size))
        except Exception:
            item.setText(2, "-")
        item.setData(0, ROLE_PATH, str(file_path))
        item.setData(0, ROLE_LOADED, True)
        item.setData(0, ROLE_ISDIR, False)
        self._path_cache[str(file_path)] = item
        item.setForeground(0, QColor(THEME["text_dim"]))
        item.setForeground(1, QColor(THEME["text_faint"]))
        item.setForeground(2, QColor(THEME["text_faint"]))
        item.setFont(0, make_font(12))
        item.setFont(1, make_font(10))
        item.setFont(2, make_font(10))
        self.all_file_items.append(item)

        self._cover_pending.add(id(item))
        self._schedule_visible_covers()
        return item

    # ==================== 封面队列处理 ====================

    def _on_cover_ready(self, path, image, item):
        """封面提取完成回调，在主线程执行"""
        if item and item.treeWidget() is self.tree:
            if image and not image.isNull():
                pixmap = QPixmap.fromImage(image)
                item.setIcon(0, QIcon(pixmap))

    def _schedule_visible_covers(self):
        """延迟后只提取可见行的封面"""
        self._visible_cover_timer.start()

    def _load_visible_covers(self):
        """只提取可见区域的封面，用固定行高性能计算"""
        if not self._cover_pending:
            return

        viewport = self.tree.viewport()
        top_index = self.tree.indexAt(QPoint(0, 0))
        if not top_index.isValid():
            return

        row_height = THEME["row_height"]
        visible_rows = viewport.height() // row_height + 3  # 多加载3行缓冲

        idx = top_index
        for _ in range(visible_rows):
            if not idx.isValid():
                break
            item = self.tree.itemFromIndex(idx)
            if item and id(item) in self._cover_pending:
                self._cover_pending.discard(id(item))
                if not item.data(0, ROLE_ISDIR):
                    path = item.data(0, ROLE_PATH)
                    if path and path != "__dummy__":
                        self._cover_extractor.enqueue_file(path, item)
            idx = self.tree.indexBelow(idx)

        self._cover_extractor.start()

    # ==================== 懒加载与展开状态 ====================

    def on_item_expanded(self, item):
        if self._searching:
            return
        self._load_folder_content(item)

    def on_item_collapsed(self, item):
        path = item.data(0, ROLE_PATH)
        if path and path in self.expanded_paths:
            self.expanded_paths.discard(path)

    def _load_folder_content(self, item):
        loaded = item.data(0, ROLE_LOADED)
        if loaded:
            path = item.data(0, ROLE_PATH)
            if path:
                self.expanded_paths.add(path)
            return

        dir_path = item.data(0, ROLE_PATH)
        if not dir_path or not os.path.isdir(dir_path):
            return

        item.setData(0, ROLE_LOADED, True)
        self.expanded_paths.add(dir_path)

        # 批量移除占位子项
        if item.childCount() > 0:
            item.takeChildren()

        try:
            entries = self._scan_dir(Path(dir_path))
            file_count = 0
            folder_count = 0
            for entry in entries:
                if entry.is_dir():
                    self._create_folder_item(item, entry)
                    folder_count += 1
                    self.total_folders += 1
                elif entry.is_file():
                    self._create_file_item(item, entry)
                    file_count += 1
                    self.total_files += 1
            total = file_count + folder_count
            item.setData(0, ROLE_COUNT, total)
            name = item.data(0, ROLE_NAME)
            if total:
                item.setText(0, f"  {FOLDER_ICON}  {name}  \u00b7 {total}")
            else:
                item.setText(0, f"  {FOLDER_ICON}  {name}")
        except PermissionError:
            err = QTreeWidgetItem(item)
            err.setText(0, "      [权限不足]")
            err.setForeground(0, QColor(THEME["danger"]))
        except Exception as e:
            err = QTreeWidgetItem(item)
            err.setText(0, f"      [错误: {e}]")
            err.setForeground(0, QColor(THEME["danger"]))

        self._update_stats()
        self._trim_path_cache()

        if self.search_active and not self._searching:
            self._apply_search_filter()

    def _trim_path_cache(self):
        """清理已折叠分支的路径缓存，限制缓存大小"""
        if len(self._path_cache) < 500:
            return
        keep = set()
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            p = item.data(0, ROLE_PATH)
            if p and p != "__dummy__":
                keep.add(os.path.normpath(p))
            iterator += 1
        to_del = [k for k in self._path_cache if k not in keep]
        for k in to_del:
            del self._path_cache[k]

    def on_item_clicked(self, item, column):
        is_dir = item.data(0, ROLE_ISDIR)
        if is_dir:
            item.setExpanded(not item.isExpanded())

    def _restore_expanded_state(self):
        if not self.expanded_paths:
            return
        sorted_paths = sorted(self.expanded_paths, key=lambda p: p.count(os.sep))
        for path in list(sorted_paths):
            if not os.path.isdir(path):
                self.expanded_paths.discard(path)
                continue
            item = self._find_item_by_path(path)
            if item:
                item.setExpanded(True)

    def _find_item_by_path(self, target_path):
        target_path = os.path.normpath(target_path)
        item = self._path_cache.get(target_path)
        if item and item.treeWidget() is self.tree:
            return item
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            p = item.data(0, ROLE_PATH)
            if p and p != "__dummy__" and os.path.normpath(p) == target_path:
                self._path_cache[target_path] = item
                return item
            iterator += 1
        return None

    def expand_recursive(self, item):
        item.setExpanded(True)
        self._load_folder_content(item)
        for i in range(item.childCount()):
            child = item.child(i)
            if child.data(0, ROLE_ISDIR):
                self.expand_recursive(child)

    # ==================== 搜索过滤 ====================

    def _on_search_input_changed(self, text):
        """防抖：复用定时器，不每次新建"""
        self._search_timer.stop()
        self._search_timer.start()

    def _do_search(self):
        text = self.search_input.text().strip().lower()
        if not text:
            self.search_active = False
            self._clear_filter()
            return
        self.search_active = True
        self._apply_search_filter()

    def _apply_search_filter(self):
        keyword = self.search_input.text().strip().lower()
        if not keyword:
            self._clear_filter()
            return

        self._searching = True

        matches = []
        for dirpath, dirnames, filenames in os.walk(self.current_folder):
            dirnames[:] = [d for d in dirnames
                           if d not in SKIP_DIRS and not d.startswith("._")]
            for f in filenames:
                if f.startswith("._"):
                    continue
                if keyword in f.lower():
                    matches.append(os.path.join(dirpath, f))

        self.tree.collapseAll()
        for item in self.all_file_items:
            item.setHidden(True)

        for file_path in matches:
            parent_chain = self._get_parent_chain(file_path)
            for parent_path in parent_chain:
                item = self._find_item_by_path(parent_path)
                if item:
                    if not item.data(0, ROLE_LOADED):
                        self._load_folder_content(item)
                    item.setExpanded(True)
                    item.setHidden(False)
            file_item = self._find_item_by_path(file_path)
            if file_item:
                file_item.setHidden(False)

        self._searching = False
        self.stats_label.setText(
            f'  搜索"{self.search_input.text()}"  共 {len(matches)} 条结果'
        )

    def _get_parent_chain(self, file_path):
        root = self.current_folder
        chain = []
        p = os.path.dirname(file_path)
        while p and os.path.normpath(p) != os.path.normpath(root) and len(p) >= len(root):
            chain.insert(0, p)
            new_p = os.path.dirname(p)
            if new_p == p:
                break
            p = new_p
        return chain

    def _clear_filter(self):
        for item in self.all_file_items:
            item.setHidden(False)
        self._update_stats()

    def clear_search(self):
        self.search_input.clear()
        self.search_active = False
        self._clear_filter()

    # ==================== 点击与打开 ====================

    def on_item_double_clicked(self, item, column):
        file_path = item.data(0, ROLE_PATH)
        is_dir = item.data(0, ROLE_ISDIR)
        if is_dir:
            item.setExpanded(not item.isExpanded())
            return
        if file_path and file_path != "__dummy__" and os.path.isfile(file_path):
            self.open_file(file_path)

    def open_selected(self):
        if self.search_input.hasFocus():
            return
        item = self.tree.currentItem()
        if item:
            self.on_item_double_clicked(item, 0)

    def open_file(self, file_path):
        try:
            if sys.platform == "darwin":
                result = subprocess.run(
                    ["open", file_path],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode != 0:
                    self._show_open_with_dialog(file_path)
                else:
                    self.add_recent(file_path)
            elif sys.platform.startswith("linux"):
                result = subprocess.run(
                    ["xdg-open", file_path],
                    capture_output=True, text=True, timeout=15
                )
                if result.returncode != 0:
                    self._show_open_with_dialog(file_path)
                else:
                    self.add_recent(file_path)
            elif sys.platform == "win32":
                os.startfile(file_path)
                self.add_recent(file_path)
            else:
                self._show_open_with_dialog(file_path)
        except subprocess.TimeoutExpired:
            self._show_open_with_dialog(file_path)
        except Exception:
            self._show_open_with_dialog(file_path)

    def _show_open_with_dialog(self, file_path):
        msg = QMessageBox(self)
        msg.setWindowTitle("打开方式")
        msg.setText(f"无法直接打开：\n{os.path.basename(file_path)}")
        msg.setInformativeText("请选择打开方式：")
        open_btn = msg.addButton("选择应用...", QMessageBox.ButtonRole.AcceptRole)
        reveal_btn = msg.addButton("在访达中显示", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("取消", QMessageBox.ButtonRole.RejectRole)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.exec()

        clicked = msg.clickedButton()
        if clicked == open_btn:
            if sys.platform == "darwin":
                app_path = QFileDialog.getOpenFileName(
                    self, "选择应用", "/Applications",
                    "应用 (*.app);;所有文件 (*)"
                )[0]
            else:
                app_path = QFileDialog.getOpenFileName(
                    self, "选择应用", "", "所有文件 (*)"
                )[0]
            if app_path:
                try:
                    if sys.platform == "darwin":
                        subprocess.run(["open", "-a", app_path, file_path], timeout=15)
                    else:
                        subprocess.run([app_path, file_path], timeout=15)
                    self.add_recent(file_path)
                except Exception as e:
                    QMessageBox.warning(self, "失败", f"无法使用所选应用打开：\n{e}")
        elif clicked == reveal_btn:
            self.reveal_in_finder(file_path)

    def reveal_in_finder(self, file_path):
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", file_path], timeout=10)
            elif sys.platform.startswith("linux"):
                subprocess.run(["xdg-open", os.path.dirname(file_path)], timeout=10)
            else:
                subprocess.run(["explorer", "/select,", file_path], timeout=10)
        except Exception:
            pass

    # ==================== 最近打开记录 ====================

    def add_recent(self, file_path):
        entry = {
            "path": file_path,
            "name": os.path.basename(file_path),
            "time": time.strftime("%Y-%m-%d %H:%M"),
        }
        self.recent_books = [b for b in self.recent_books if b["path"] != file_path]
        self.recent_books.insert(0, entry)
        self.recent_books = self.recent_books[:10]
        self.update_recent_list()
        self.save_config()

    def update_recent_list(self):
        self.recent_list.clear()
        for book in self.recent_books:
            display = f"  {RECENT_ICON}  {book['name']}\n        {book['time']}"
            item = QListWidgetItem(display)
            item.setToolTip(book["path"])
            self.recent_list.addItem(item)

    def on_recent_item_clicked(self, item):
        path = item.toolTip()
        if path and os.path.isfile(path):
            self.open_file(path)
        elif path and not os.path.isfile(path):
            QMessageBox.information(self, "提示", "文件已不存在")

    def clear_recent(self):
        self.recent_books.clear()
        self.update_recent_list()
        self.save_config()

    # ==================== 右键菜单 ====================

    def on_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        file_path = item.data(0, ROLE_PATH)
        if not file_path or file_path == "__dummy__":
            return

        menu = QMenu(self)
        is_dir = item.data(0, ROLE_ISDIR)

        if not is_dir and os.path.isfile(file_path):
            act_open = QAction("打开", self)
            act_open.triggered.connect(lambda: self.open_file(file_path))
            menu.addAction(act_open)

            act_reveal = QAction("在访达中显示", self)
            act_reveal.triggered.connect(lambda: self.reveal_in_finder(file_path))
            menu.addAction(act_reveal)

            menu.addSeparator()

            act_copy = QAction("复制路径", self)
            act_copy.triggered.connect(lambda: self._copy_path(file_path))
            menu.addAction(act_copy)

            act_copy_name = QAction("复制文件名", self)
            act_copy_name.triggered.connect(
                lambda: self._copy_text(os.path.basename(file_path))
            )
            menu.addAction(act_copy_name)
        elif os.path.isdir(file_path):
            act_reveal = QAction("在访达中显示", self)
            act_reveal.triggered.connect(lambda: self.reveal_in_finder(file_path))
            menu.addAction(act_reveal)

            act_expand = QAction("展开全部子文件夹", self)
            act_expand.triggered.connect(lambda: self.expand_recursive(item))
            menu.addAction(act_expand)

            menu.addSeparator()

            act_copy = QAction("复制文件夹路径", self)
            act_copy.triggered.connect(lambda: self._copy_path(file_path))
            menu.addAction(act_copy)

            act_export_dir = QAction("导出此文件夹书目", self)
            act_export_dir.triggered.connect(lambda: self.export_list(file_path))
            menu.addAction(act_export_dir)

        if menu.actions():
            menu.exec(self.tree.viewport().mapToGlobal(pos))

    def _copy_path(self, path):
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
        self.statusBar().showMessage(f"已复制：{path}", 3000)

    def _copy_text(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.statusBar().showMessage(f"已复制：{text}", 3000)

    def copy_selected_path(self):
        item = self.tree.currentItem()
        if item:
            path = item.data(0, ROLE_PATH)
            if path and path != "__dummy__":
                self._copy_path(path)

    # ==================== 导出书目清单 ====================

    def export_list(self, specific_dir=None):
        if not self.current_folder and not specific_dir:
            return

        export_root = specific_dir if specific_dir else self.current_folder

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出书目清单",
            os.path.join(os.path.dirname(export_root),
                         f"booklist_{Path(export_root).name}.csv"),
            "CSV (*.csv);;TXT (*.txt)"
        )
        if not file_path:
            return

        books = []
        for root, dirs, files in os.walk(export_root):
            dirs[:] = [d for d in dirs
                       if d not in SKIP_DIRS and not d.startswith("._")]
            for f in files:
                if f.startswith("._") or f == ".DS_Store":
                    continue
                fp = os.path.join(root, f)
                ext = os.path.splitext(f)[1].lower().lstrip(".")
                try:
                    size = os.path.getsize(fp)
                except Exception:
                    size = 0
                rel_path = os.path.relpath(fp, export_root)
                books.append({
                    "name": f,
                    "format": ext.upper() if ext else "-",
                    "size": format_size(size),
                    "path": rel_path,
                })

        books.sort(key=lambda x: x["path"].lower())

        try:
            if file_path.endswith(".csv"):
                with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    writer.writerow(["序号", "书名", "格式", "大小", "路径"])
                    for i, book in enumerate(books, 1):
                        writer.writerow([
                            i, book["name"], book["format"],
                            book["size"], book["path"]
                        ])
                    writer.writerow([])
                    writer.writerow([f"共 {len(books)} 本"])
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"书目清单 - {Path(export_root).name}\n")
                    f.write(f"导出时间：{time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"共 {len(books)} 本\n")
                    f.write("=" * 60 + "\n\n")
                    for i, book in enumerate(books, 1):
                        f.write(f"{i:4d}. [{book['format']:>5}] {book['name']}\n")
                        f.write(f"      大小: {book['size']}  路径: {book['path']}\n")
                    f.write("\n" + "=" * 60 + "\n")
                    f.write(f"共 {len(books)} 本\n")

            QMessageBox.information(
                self, "导出成功",
                f"已导出 {len(books)} 本书目至：\n{file_path}"
            )
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"导出失败：\n{e}")

    # ==================== 统计更新 ====================

    def _update_stats(self):
        self.stats_label.setText(
            f"  {self.total_folders} 个文件夹  /  {self.total_files} 个文件"
        )
        if self.format_stats:
            parts = []
            for fmt, count in self.format_stats.most_common():
                parts.append(f"{fmt} {count}")
            self.format_stats_label.setText("  ".join(parts))
        else:
            self.format_stats_label.setText("暂无数据")

    # ==================== 关闭事件 ====================

    def closeEvent(self, event):
        self._cover_extractor._running = False
        self._cover_extractor._result_timer.stop()
        self._visible_cover_timer.stop()
        self._search_timer.stop()
        self.save_config()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("图书库浏览器")

    cli_folder = sys.argv[1] if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]) else None

    if cli_folder:
        window = LibraryBrowser.__new__(LibraryBrowser)
        QMainWindow.__init__(window)
        window.current_folder = cli_folder
        window.total_files = 0
        window.total_folders = 0
        window.format_stats = Counter()
        window.recent_books = []
        window.expanded_paths = set()
        window.search_active = False
        window._searching = False
        window.all_file_items = []
        window._path_cache = {}
        window._cover_pending = set()

        window._visible_cover_timer = QTimer()
        window._visible_cover_timer.setInterval(150)
        window._visible_cover_timer.setSingleShot(True)
        window._visible_cover_timer.timeout.connect(window._load_visible_covers)

        window._search_timer = QTimer()
        window._search_timer.setSingleShot(True)
        window._search_timer.setInterval(300)
        window._search_timer.timeout.connect(window._do_search)

        window.cover_manager = CoverManager()
        window._cover_extractor = CoverExtractor(window.cover_manager)
        window._cover_extractor.cover_ready.connect(window._on_cover_ready)

        window.init_ui()
        window._load_config_no_folder()
        window.path_label.setText(cli_folder)
        window.btn_refresh.setEnabled(True)
        window.btn_collapse.setEnabled(True)
        window.btn_export.setEnabled(True)
        window.load_folder(cli_folder)
        window.save_config()
    else:
        window = LibraryBrowser()

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
