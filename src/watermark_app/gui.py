from __future__ import annotations
import os
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import Qt, QSize, QRectF, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap, QColor, QImage
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QListWidget, QListWidgetItem,
    QMainWindow, QToolBar, QMessageBox, QWidget, QVBoxLayout, QLabel,
    QPushButton, QColorDialog, QSlider, QLineEdit, QHBoxLayout, QStatusBar,
    QGraphicsScene, QGraphicsView, QGraphicsPixmapItem, QSpinBox
)
from PIL import Image, ImageQt, ImageDraw, ImageFont


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def is_image_file(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() in SUPPORTED_EXTS


class ThumbList(QListWidget):
    imageSelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(100, 100))
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSpacing(6)
        self.itemClicked.connect(self._on_item_clicked)

    def _on_item_clicked(self, item):
        self.imageSelected.emit(item.data(Qt.ItemDataRole.UserRole))


class PreviewArea(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.image_item: Optional[QGraphicsPixmapItem] = None

    def load_image(self, img_path: str):
        self._scene.clear()
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            return
        self.image_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def show_composite(self, pil_image: Image.Image):
        qimage = ImageQt.ImageQt(pil_image.convert("RGBA"))
        pixmap = QPixmap.fromImage(QImage(qimage))
        self._scene.clear()
        self.image_item = self._scene.addPixmap(pixmap)
        self._scene.setSceneRect(QRectF(pixmap.rect()))
        self.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Watermark App — 文本字号调节版")
        self.resize(1250, 800)

        self.thumb_list = ThumbList(self)
        self.preview = PreviewArea(self)
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        # 文本水印设置
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("输入水印文本…")

        self.color_btn = QPushButton("颜色")
        self.color = QColor(255, 255, 255)
        self.alpha_slider = QSlider(Qt.Orientation.Horizontal)
        self.alpha_slider.setRange(0, 100)
        self.alpha_slider.setValue(70)

        # 字号调节
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 128)
        self.font_size_spin.setValue(36)

        # 图片水印
        self.img_btn = QPushButton("选择PNG水印")
        self.apply_text_btn = QPushButton("应用文本水印")
        self.apply_img_btn = QPushButton("应用图片水印")

        # 布局
        control_layout = QVBoxLayout()
        control_layout.addWidget(QLabel("预览窗口"))
        control_layout.addWidget(self.preview)
        control_layout.addWidget(QLabel("水印文字"))
        control_layout.addWidget(self.text_input)

        hl1 = QHBoxLayout()
        hl1.addWidget(self.color_btn)
        hl1.addWidget(QLabel("透明度"))
        hl1.addWidget(self.alpha_slider)
        control_layout.addLayout(hl1)

        hl2 = QHBoxLayout()
        hl2.addWidget(QLabel("字号"))
        hl2.addWidget(self.font_size_spin)
        control_layout.addLayout(hl2)

        control_layout.addWidget(self.img_btn)
        control_layout.addWidget(self.apply_text_btn)
        control_layout.addWidget(self.apply_img_btn)

        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.addWidget(self.thumb_list, 2)
        layout.addLayout(control_layout, 5)
        self.setCentralWidget(wrapper)

        tb = QToolBar("File", self)
        self.addToolBar(tb)
        act_open = tb.addAction("打开文件...")
        act_open.triggered.connect(self.open_files)
        act_open_dir = tb.addAction("打开文件夹...")
        act_open_dir.triggered.connect(self.open_dir)

        # 信号绑定
        self.color_btn.clicked.connect(self.choose_color)
        self.img_btn.clicked.connect(self.choose_logo)
        self.apply_text_btn.clicked.connect(self.apply_text)
        self.apply_img_btn.clicked.connect(self.apply_image)
        self.thumb_list.imageSelected.connect(self.show_preview)

        self.watermark_img_path = None
        self.current_img_path = None
        self.update_status()

    # === 文件导入 ===
    def open_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择图片", "", "Images (*.jpg *.png *.jpeg *.bmp *.tif *.tiff)")
        if files:
            self.add_images([Path(f) for f in files])
            self.show_preview(files[0])

    def open_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择文件夹", "")
        if d:
            imgs = []
            for root, _, files in os.walk(d):
                for f in files:
                    p = Path(root) / f
                    if is_image_file(p):
                        imgs.append(str(p))
                        icon = QIcon(str(p))
                        item = QListWidgetItem(icon, p.name)
                        item.setData(Qt.ItemDataRole.UserRole, str(p))
                        self.thumb_list.addItem(item)
            if imgs:
                self.show_preview(imgs[0])
        self.update_status()

    def add_images(self, paths: List[Path]):
        for p in paths:
            if not is_image_file(p):
                continue
            icon = QIcon(str(p))
            item = QListWidgetItem(icon, p.name)
            item.setData(Qt.ItemDataRole.UserRole, str(p))
            self.thumb_list.addItem(item)
        self.update_status()

    # === 预览 ===
    def show_preview(self, path: str):
        self.current_img_path = path
        self.preview.load_image(path)

    # === 控件操作 ===
    def choose_color(self):
        color = QColorDialog.getColor(self.color, self)
        if color.isValid():
            self.color = color
            self.color_btn.setStyleSheet(f"background-color: {color.name()};")

    def choose_logo(self):
        file, _ = QFileDialog.getOpenFileName(self, "选择PNG水印", "", "PNG Images (*.png)")
        if file:
            self.watermark_img_path = file
            self.img_btn.setText(f"已选择: {os.path.basename(file)}")

    # === 应用文本水印 ===
    def apply_text(self):
        if not self.current_img_path:
            QMessageBox.warning(self, "提示", "请先选择图片")
            return

        text = self.text_input.text().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入水印文本")
            return

        font_size = self.font_size_spin.value()
        # 尝试使用一个通用字体
        try:
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        base = Image.open(self.current_img_path).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        alpha = int(self.alpha_slider.value() * 2.55)
        draw.text((40, 40), text, fill=self.color.getRgb()[:3] + (alpha,), font=font)
        combined = Image.alpha_composite(base, overlay)
        self.preview.show_composite(combined)

    # === 应用图片水印 ===
    def apply_image(self):
        if not self.current_img_path or not self.watermark_img_path:
            QMessageBox.warning(self, "提示", "请先选择图片和水印文件")
            return

        base = Image.open(self.current_img_path).convert("RGBA")
        watermark = Image.open(self.watermark_img_path).convert("RGBA")
        scale = 0.3
        w = int(base.width * scale)
        h = int(watermark.height * (w / watermark.width))
        watermark = watermark.resize((w, h))
        alpha_val = int(self.alpha_slider.value() * 2.55)
        watermark.putalpha(alpha_val)
        pos = (base.width - watermark.width - 20, base.height - watermark.height - 20)
        base.paste(watermark, pos, watermark)
        self.preview.show_composite(base)

    def update_status(self):
        self.status.showMessage(f"已导入图片数：{self.thumb_list.count()}")


def run_app():
    import sys
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
