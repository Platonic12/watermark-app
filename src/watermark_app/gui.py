from __future__ import annotations
import os
from pathlib import Path
from typing import List
from PyQt6.QtCore import Qt, QSize, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QColor
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QListWidget, QListWidgetItem,
    QMainWindow, QToolBar, QMessageBox, QWidget, QVBoxLayout, QLabel,
    QPushButton, QColorDialog, QSlider, QLineEdit, QHBoxLayout, QStatusBar
)
from .watermark_core import apply_text_watermark, apply_image_watermark

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def is_image_file(p: Path) -> bool:
    """判断是否为支持的图片文件"""
    return p.is_file() and p.suffix.lower() in SUPPORTED_EXTS


class ThumbList(QListWidget):
    """支持拖拽导入的缩略图列表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(128, 128))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setAcceptDrops(True)
        self.setSpacing(6)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, e):
        paths = [Path(QUrl(u).toLocalFile()) for u in e.mimeData().urls()]
        self.parent().add_images(paths)


class MainWindow(QMainWindow):
    """主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Watermark App — 添加文本/图片水印")
        self.resize(1050, 700)

        # 主界面组件
        self.thumb_list = ThumbList(self)
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        # 文本输入与控制
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("请输入水印文本…")

        self.color_btn = QPushButton("选择颜色")
        self.color = QColor(255, 255, 255)

        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(50)

        self.img_btn = QPushButton("选择图片水印 (PNG)")
        self.apply_text_btn = QPushButton("应用文本水印")
        self.apply_img_btn = QPushButton("应用图片水印")

        # 布局设置
        layout = QVBoxLayout()
        layout.addWidget(self.thumb_list)
        layout.addWidget(self.text_input)

        hl = QHBoxLayout()
        hl.addWidget(self.color_btn)
        hl.addWidget(QLabel("透明度"))
        hl.addWidget(self.alpha_slider)
        layout.addLayout(hl)

        layout.addWidget(self.img_btn)
        layout.addWidget(self.apply_text_btn)
        layout.addWidget(self.apply_img_btn)

        wrapper = QWidget()
        wrapper.setLayout(layout)
        self.setCentralWidget(wrapper)

        # 工具栏
        tb = QToolBar("File", self)
        tb.setIconSize(QSize(18, 18))
        self.addToolBar(tb)
        act_open = tb.addAction("打开文件...")
        act_open.triggered.connect(self.open_files)
        act_open_dir = tb.addAction("打开文件夹...")
        act_open_dir.triggered.connect(self.open_dir)

        # 信号连接
        self.color_btn.clicked.connect(self.choose_color)
        self.img_btn.clicked.connect(self.choose_logo)
        self.apply_text_btn.clicked.connect(self.add_text_watermark)
        self.apply_img_btn.clicked.connect(self.add_image_watermark)

        # 内部状态
        self.watermark_img_path = None
        self.update_status()

    # =================== 文件导入 ===================
    def update_status(self):
        self.status.showMessage(f"当前已导入图片 {self.thumb_list.count()} 张")

    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            "",
            "Images (*.jpg *.png *.jpeg *.bmp *.tif *.tiff)"
        )
        if files:
            self.add_images([Path(f) for f in files])

    def open_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if d:
            for root, _, files in os.walk(d):
                self.add_images([Path(root) / f for f in files])

    def add_images(self, paths: List[Path]):
        for p in paths:
            if not is_image_file(p):
                continue
            icon = QIcon(str(p))
            item = QListWidgetItem(icon, p.name)
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.thumb_list.addItem(item)
        self.update_status()

    # =================== 控制项 ===================
    def choose_color(self):
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")

    def choose_logo(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择PNG水印图片", "", "PNG Images (*.png)"
        )
        if file:
            self.watermark_img_path = file
            self.img_btn.setText(f"已选择: {os.path.basename(file)}")

    # =================== 水印操作 ===================
    def add_text_watermark(self):
        if self.thumb_list.count() == 0:
            QMessageBox.warning(self, "提示", "请先导入图片")
            return

        text = self.text_input.text().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入水印文本")
            return

        alpha = int(self.alpha_slider.value() * 2.55)
        color_rgb = self.color.getRgb()[:3]

        for i in range(self.thumb_list.count()):
            p = self.thumb_list.item(i).data(Qt.ItemDataRole.UserRole)
            img = apply_text_watermark(p, text, color=color_rgb, alpha=alpha)
            save_path = str(Path(p).with_name(f"{Path(p).stem}_wm.jpg"))
            img.save(save_path, quality=95)

        QMessageBox.information(self, "完成", "文本水印已应用并保存。")

    def add_image_watermark(self):
        if not self.watermark_img_path:
            QMessageBox.warning(self, "提示", "请先选择水印图片")
            return

        alpha = int(self.alpha_slider.value() * 2.55)
        for i in range(self.thumb_list.count()):
            p = self.thumb_list.item(i).data(Qt.ItemDataRole.UserRole)
            img = apply_image_watermark(p, self.watermark_img_path, scale=0.3, alpha=alpha)
            save_path = str(Path(p).with_name(f"{Path(p).stem}_imgwm.jpg"))
            img.save(save_path, quality=95)

        QMessageBox.information(self, "完成", "图片水印已应用并保存。")

# =================== 应用入口 ===================
def run_app():
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
