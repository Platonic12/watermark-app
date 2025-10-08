from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable, List, Set

from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QListWidget, QListWidgetItem,
    QMainWindow, QToolBar, QMessageBox, QWidget, QVBoxLayout, QLabel, QStatusBar
)


SUPPORTED_EXTS: Set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def is_image_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in SUPPORTED_EXTS


def iter_images_from_paths(paths: Iterable[Path]) -> Iterable[Path]:
    """
    将传入的文件或文件夹路径展开为图片文件列表（递归扫描文件夹）。
    """
    for p in paths:
        if p.is_dir():
            for root, _, files in os.walk(p):
                for f in files:
                    fp = Path(root) / f
                    if is_image_file(fp):
                        yield fp
        elif is_image_file(p):
            yield p


class ThumbList(QListWidget):
    """
    支持拖拽导入（文件/文件夹）的缩略图列表。
    """
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(128, 128))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setUniformItemSizes(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.DragDropMode.NoDragDrop)
        self.setSpacing(8)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [Path(QUrl(u).toLocalFile()) for u in urls]
        self.parent().add_images(paths)  # 交给 MainWindow 统一处理
        event.acceptProposedAction()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Watermark App — 导入图片预览")
        self.resize(1000, 650)

        self.thumb_list = ThumbList(self)

        tip = QLabel("拖拽图片或文件夹到此处，或使用上方“打开文件/打开文件夹”。")
        tip.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip.setStyleSheet("color: #666;")

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.addWidget(self.thumb_list)
        layout.addWidget(tip)
        self.setCentralWidget(wrapper)

        # 工具栏
        tb = QToolBar("File", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)

        act_open_files = QAction(QIcon(), "打开文件...", self)
        act_open_files.triggered.connect(self.open_files)
        tb.addAction(act_open_files)

        act_open_dir = QAction(QIcon(), "打开文件夹...", self)
        act_open_dir.triggered.connect(self.open_dir)
        tb.addAction(act_open_dir)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.update_status()

    def update_status(self):
        self.status.showMessage(f"已导入图片：{self.thumb_list.count()} 张")

    # —— 打开对话框：多文件 ——
    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片（可多选）",
            "",
            "Images (*.jpg *.jpeg *.png *.bmp *.tif *.tiff)"
        )
        if files:
            self.add_images([Path(f) for f in files])

    # —— 打开对话框：文件夹 ——
    def open_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择图片所在文件夹", "")
        if d:
            self.add_images([Path(d)])

    # —— 统一添加图片 ——（去重、生成缩略图+文件名）
    def add_images(self, inputs: Iterable[Path]):
        new_files: List[Path] = list(iter_images_from_paths(inputs))
        if not new_files:
            QMessageBox.information(self, "提示", "未发现可导入的图片。")
            return

        # 已有项的路径集合，用于去重
        existing: Set[str] = set()
        for i in range(self.thumb_list.count()):
            it = self.thumb_list.item(i)
            existing.add(it.data(Qt.ItemDataRole.UserRole))

        added = 0
        for p in new_files:
            sp = str(p.resolve())
            if sp in existing:
                continue

            pix = QPixmap(sp)
            if pix.isNull():
                # 读不到就跳过
                continue
            icon = QIcon(pix.scaled(256, 256, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

            item = QListWidgetItem(icon, p.name)
            item.setData(Qt.ItemDataRole.UserRole, sp)
            item.setToolTip(sp)
            item.setSizeHint(QSize(150, 160))
            self.thumb_list.addItem(item)
            added += 1

        if added > 0:
            self.update_status()
        else:
            QMessageBox.information(self, "提示", "没有新增图片（可能都已导入或格式不支持）。")


def run_app():
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
