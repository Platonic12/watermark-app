import sys
import datetime
import os
import json
import math
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QSlider,
    QComboBox,
    QLineEdit,
    QColorDialog,
    QGroupBox,
    QFormLayout,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QRadioButton,
    QButtonGroup,
    QMessageBox,
    QSplitter,
    QInputDialog,
    QSizePolicy,  # 新增导入
)
from PyQt6.QtGui import (
    QPixmap,
    QImage,
    QFontDatabase,
    QFont,
    QColor,
    QIcon,
    QDragEnterEvent,
    QDropEvent,
)
from PyQt6.QtCore import Qt, QPoint, QRect, QSize, QUrl
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageQt
import numpy as np


class WatermarkApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_data(load_templates=False)  # 先初始化数据，暂不加载模板
        self.init_ui()  # 初始化UI，创建template_list
        self.load_templates()  # 此时template_list已存在，可安全加载模板
        self.load_last_settings()

    def init_ui(self):
        self.setWindowTitle("图片水印处理工具")
        self.setGeometry(100, 100, 1200, 800)

        # 主部件和布局
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # 左侧面板 - 图片列表
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_panel.setMinimumWidth(200)

        # 导入按钮
        import_layout = QHBoxLayout()
        self.btn_import_single = QPushButton("导入图片")
        self.btn_import_batch = QPushButton("批量导入")
        self.btn_import_folder = QPushButton("导入文件夹")

        self.btn_import_single.clicked.connect(self.import_single_image)
        self.btn_import_batch.clicked.connect(self.import_batch_images)
        self.btn_import_folder.clicked.connect(self.import_folder)

        import_layout.addWidget(self.btn_import_single)
        import_layout.addWidget(self.btn_import_batch)
        import_layout.addWidget(self.btn_import_folder)

        # 图片列表
        self.image_list = QListWidget()
        self.image_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.image_list.setIconSize(QSize(128, 128))
        self.image_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.image_list.itemClicked.connect(self.on_image_selected)

        # 移除图片按钮
        self.btn_remove_image = QPushButton("移除选中图片")
        self.btn_remove_image.clicked.connect(self.remove_selected_image)

        left_layout.addLayout(import_layout)
        left_layout.addWidget(QLabel("已导入图片:"))
        left_layout.addWidget(self.image_list)
        left_layout.addWidget(self.btn_remove_image)

        # 中间面板 - 预览（优化部分）
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)
        # 设置布局边距为0，消除不必要的空白
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(5)

        # 优化预览标题显示
        preview_label = QLabel("图片预览")
        preview_label.setStyleSheet("font-weight: bold; padding: 5px 0;")
        center_layout.addWidget(preview_label)

        # 水印预览区域（核心优化）
        self.watermark_preview = QLabel()
        self.watermark_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.watermark_preview.setStyleSheet("border: 1px solid #cccccc;")
        # 设置大小策略为可扩展，使其能随窗口大小变化
        self.watermark_preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Expanding
        )
        self.watermark_preview.setMinimumSize(400, 400)  # 保持最小尺寸
        self.watermark_preview.setMouseTracking(True)
        self.watermark_preview.mousePressEvent = self.start_drag_watermark
        self.watermark_preview.mouseMoveEvent = self.drag_watermark
        self.watermark_preview.mouseReleaseEvent = self.stop_drag_watermark

        # 添加预览区域并设置为可扩展
        center_layout.addWidget(self.watermark_preview, 1)  # 1表示权重，会占据所有可用空间

        # 右侧面板 - 设置
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_panel.setMinimumWidth(300)

        # 选项卡
        self.tabs = QTabWidget()

        # 水印类型选项卡
        self.tab_watermark_type = QWidget()
        self.init_watermark_type_tab()
        self.tabs.addTab(self.tab_watermark_type, "水印类型")

        # 水印设置选项卡
        self.tab_watermark_settings = QWidget()
        self.init_watermark_settings_tab()
        self.tabs.addTab(self.tab_watermark_settings, "水印设置")

        # 位置和旋转选项卡
        self.tab_position = QWidget()
        self.init_position_tab()
        self.tabs.addTab(self.tab_position, "位置和旋转")

        # 导出选项卡
        self.tab_export = QWidget()
        self.init_export_tab()
        self.tabs.addTab(self.tab_export, "导出设置")

        # 模板管理选项卡
        self.tab_templates = QWidget()
        self.init_templates_tab()
        self.tabs.addTab(self.tab_templates, "模板管理")

        right_layout.addWidget(self.tabs)

        # 导出按钮
        self.btn_export = QPushButton("导出图片")
        self.btn_export.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 10px;"
        )
        self.btn_export.clicked.connect(self.export_images)
        right_layout.addWidget(self.btn_export)

        # 添加到主布局
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)
        # 调整初始大小比例，给预览区域更多空间
        splitter.setSizes([200, 800, 300])

        main_layout.addWidget(splitter)

        # 启用拖放功能
        self.setAcceptDrops(True)
        self.image_list.setAcceptDrops(True)
        self.watermark_preview.setAcceptDrops(True)

    def init_data(self, load_templates=True):  # 增加参数，默认True保持兼容性
        # 存储导入的图片
        self.images = []  # 格式: {"path": 路径, "image": PIL图像对象}
        self.current_image_index = -1

        # 水印设置（保持不变）
        self.watermark_settings = {
            "type": "text",  # "text" 或 "image"
            "text": "水印",
            "font_family": "SimHei",
            "font_size": 36,
            "font_bold": False,
            "font_italic": False,
            "color": (255, 255, 255, 128),  # RGBA
            "transparency": 50,  # 0-100
            "shadow": False,
            "stroke": False,
            "image_path": "",
            "image_scale": 100,  # 百分比
            "position": (0.5, 0.5),  # 相对位置 (x, y) 0-1范围
            "rotation": 0,  # 角度
        }

        # 导出设置（保持不变）
        self.export_settings = {
            "folder": os.path.expanduser("~") + "/watermarked_images",
            "format": "png",
            "naming": "suffix",  # "original", "prefix", "suffix"
            "prefix": "wm_",
            "suffix": "_watermarked",
            "quality": 90,
            "resize_method": "none",  # "none", "width", "height", "percentage"
            "resize_value": 100,
        }

        # 水印模板
        self.templates = []
        if load_templates:  # 根据参数决定是否加载模板
            self.load_templates()

        # 拖拽状态
        self.dragging = False
        self.drag_start_pos = QPoint()

    def export_images(self):
        """导出所有处理好的图片"""
        if not self.images:
            QMessageBox.warning(self, "警告", "没有可导出的图片")
            return

        # 确保导出目录存在
        export_dir = self.export_settings["folder"]
        os.makedirs(export_dir, exist_ok=True)

        # 处理每张图片
        success_count = 0
        error_count = 0
        error_files = []

        for img_data in self.images:
            try:
                # 获取原图并应用水印
                original_image = img_data["image"].copy()
                watermarked_image = self.apply_watermark(original_image)

                # 处理缩放
                resized_image = self.resize_image(watermarked_image)

                # 获取输出文件名
                output_path = self.get_output_file_path(img_data["path"], export_dir)

                # 保存图片
                self.save_image(resized_image, output_path)

                success_count += 1
            except Exception as e:
                error_count += 1
                error_files.append(f"{img_data['path']}: {str(e)}")
                print(f"导出失败: {img_data['path']} - {str(e)}")

        # 显示导出结果
        result_msg = f"成功导出 {success_count} 张图片\n"
        if error_count > 0:
            result_msg += f"导出失败 {error_count} 张图片\n"
            # 详细错误信息
            details = "\n".join(error_files)
            QMessageBox.warning(self, "导出完成", f"{result_msg}\n详细错误:\n{details}")
        else:
            QMessageBox.information(self, "导出完成", result_msg)

    def resize_image(self, image):
        """根据导出设置调整图片大小"""
        method = self.export_settings["resize_method"]
        value = self.export_settings["resize_value"]

        if method == "none" or value <= 0:
            return image.copy()

        width, height = image.size

        if method == "percentage":
            # 按百分比缩放
            new_width = int(width * value / 100)
            new_height = int(height * value / 100)
        elif method == "width":
            # 按指定宽度缩放（保持比例）
            ratio = value / width
            new_width = value
            new_height = int(height * ratio)
        elif method == "height":
            # 按指定高度缩放（保持比例）
            ratio = value / height
            new_width = int(width * ratio)
            new_height = value
        else:
            return image.copy()

        # 确保尺寸有效
        new_width = max(10, new_width)
        new_height = max(10, new_height)

        # 高质量缩放
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def get_output_file_path(self, original_path, export_dir):
        """生成输出文件路径"""
        original_name = os.path.basename(original_path)
        name, ext = os.path.splitext(original_name)

        # 根据命名规则处理文件名
        naming = self.export_settings["naming"]
        if naming == "prefix":
            new_name = f"{self.export_settings['prefix']}{name}{ext}"
        elif naming == "suffix":
            new_name = f"{name}{self.export_settings['suffix']}{ext}"
        else:  # original
            new_name = original_name

        # 处理文件格式
        output_format = self.export_settings["format"].lower()
        if output_format == "jpg" and ext.lower() != ".jpg" and ext.lower() != ".jpeg":
            new_name = os.path.splitext(new_name)[0] + ".jpg"
        elif output_format == "png" and ext.lower() != ".png":
            new_name = os.path.splitext(new_name)[0] + ".png"

        return os.path.join(export_dir, new_name)

    def save_image(self, image, output_path):
        """保存图片到指定路径"""
        # 处理不同格式的保存参数
        format = self.export_settings["format"].upper()

        # 如果是JPG，需要转换为RGB模式（去除Alpha通道）
        if format == "JPG" and image.mode in ("RGBA", "LA"):
            background = Image.new(image.mode[:-1], image.size, (255, 255, 255))
            background.paste(image, image.split()[-1])
            image = background

        # 保存图片
        image.save(
            output_path,
            format=format,
            quality=self.export_settings["quality"],
            optimize=True,
        )

    def init_watermark_type_tab(self):
        # 修复：将self.tab_position改为self.tab_watermark_type
        layout = QVBoxLayout(self.tab_watermark_type)

        # 水印类型选择
        type_group = QGroupBox("水印类型")
        type_layout = QVBoxLayout()

        self.radio_text = QRadioButton("文本水印")
        self.radio_image = QRadioButton("图片水印")
        self.radio_text.setChecked(True)

        self.radio_text.toggled.connect(self.on_watermark_type_changed)

        type_layout.addWidget(self.radio_text)
        type_layout.addWidget(self.radio_image)
        type_group.setLayout(type_layout)

        # 文本水印设置
        self.text_settings_group = QGroupBox("文本设置")
        text_layout = QFormLayout()

        self.txt_watermark_text = QLineEdit("水印")
        self.txt_watermark_text.textChanged.connect(self.on_text_changed)

        # 字体选择 - 修复：使用过滤后的可用字体列表
        self.font_families = self.get_available_fonts()  # 调用新增函数获取可用字体
        self.cmb_font = QComboBox()
        self.cmb_font.addItems(self.font_families)

        # 优先选择系统自带的中文字体（确保默认字体可用）
        default_fonts = ["SimHei", "Microsoft YaHei", "SimSun", "KaiTi", "Arial"]
        for df in default_fonts:
            if df in self.font_families:
                self.cmb_font.setCurrentText(df)
                # 更新水印设置中的默认字体（避免初始字体不匹配）
                self.watermark_settings["font_family"] = df
                break

        self.cmb_font.currentTextChanged.connect(self.on_font_changed)

        # 字号
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(8, 128)
        self.spin_font_size.setValue(36)
        self.spin_font_size.valueChanged.connect(self.on_font_size_changed)

        # 粗体和斜体
        self.chk_bold = QCheckBox("粗体")
        self.chk_bold.stateChanged.connect(self.on_font_style_changed)

        self.chk_italic = QCheckBox("斜体")
        self.chk_italic.stateChanged.connect(self.on_font_style_changed)

        # 颜色选择
        self.btn_color = QPushButton("选择颜色")
        self.btn_color.setStyleSheet("background-color: white;")
        self.btn_color.clicked.connect(self.choose_color)

        text_layout.addRow("水印文本:", self.txt_watermark_text)
        text_layout.addRow("字体:", self.cmb_font)
        text_layout.addRow("字号:", self.spin_font_size)
        text_layout.addRow(self.chk_bold, self.chk_italic)
        text_layout.addRow("颜色:", self.btn_color)

        self.text_settings_group.setLayout(text_layout)

        # 图片水印设置
        self.image_settings_group = QGroupBox("图片设置")
        image_layout = QVBoxLayout()

        self.btn_select_watermark_image = QPushButton("选择水印图片")
        self.btn_select_watermark_image.clicked.connect(self.select_watermark_image)

        self.lbl_watermark_image = QLabel("未选择图片")
        self.lbl_watermark_image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_watermark_image.setStyleSheet(
            "border: 1px solid #cccccc; min-height: 60px;"
        )

        image_layout.addWidget(self.btn_select_watermark_image)
        image_layout.addWidget(self.lbl_watermark_image)

        self.image_settings_group.setLayout(image_layout)
        self.image_settings_group.setEnabled(False)

        layout.addWidget(type_group)
        layout.addWidget(self.text_settings_group)
        layout.addWidget(self.image_settings_group)
        layout.addStretch()

        self.tab_watermark_type.setLayout(layout)

    def init_watermark_settings_tab(self):
        layout = QVBoxLayout()

        # 透明度设置
        trans_group = QGroupBox("透明度")
        trans_layout = QVBoxLayout()

        self.slider_transparency = QSlider(Qt.Orientation.Horizontal)
        self.slider_transparency.setRange(0, 100)
        self.slider_transparency.setValue(50)
        self.slider_transparency.valueChanged.connect(self.on_transparency_changed)

        self.lbl_transparency = QLabel("50%")

        trans_hbox = QHBoxLayout()
        trans_hbox.addWidget(self.slider_transparency)
        trans_hbox.addWidget(self.lbl_transparency)

        trans_layout.addLayout(trans_hbox)
        trans_group.setLayout(trans_layout)

        # 文本水印特效
        self.effects_group = QGroupBox("文本特效")
        effects_layout = QVBoxLayout()

        self.chk_shadow = QCheckBox("添加阴影")
        self.chk_shadow.stateChanged.connect(self.on_effects_changed)

        self.chk_stroke = QCheckBox("添加描边")
        self.chk_stroke.stateChanged.connect(self.on_effects_changed)

        effects_layout.addWidget(self.chk_shadow)
        effects_layout.addWidget(self.chk_stroke)
        self.effects_group.setLayout(effects_layout)

        # 图片水印缩放
        self.image_scale_group = QGroupBox("图片缩放")
        scale_layout = QVBoxLayout()

        self.slider_image_scale = QSlider(Qt.Orientation.Horizontal)
        self.slider_image_scale.setRange(10, 200)
        self.slider_image_scale.setValue(100)
        self.slider_image_scale.valueChanged.connect(self.on_image_scale_changed)

        self.lbl_image_scale = QLabel("100%")

        scale_hbox = QHBoxLayout()
        scale_hbox.addWidget(self.slider_image_scale)
        scale_hbox.addWidget(self.lbl_image_scale)

        scale_layout.addLayout(scale_hbox)
        self.image_scale_group.setLayout(scale_layout)
        self.image_scale_group.setEnabled(False)

        layout.addWidget(trans_group)
        layout.addWidget(self.effects_group)
        layout.addWidget(self.image_scale_group)
        layout.addStretch()

        self.tab_watermark_settings.setLayout(layout)

    def init_position_tab(self):
        layout = QVBoxLayout()

        # 预设位置
        position_group = QGroupBox("预设位置")
        position_layout = QGridLayout()

        positions = [
            ("左上", 0, 0),
            ("中上", 0, 1),
            ("右上", 0, 2),
            ("左中", 1, 0),
            ("中心", 1, 1),
            ("右中", 1, 2),
            ("左下", 2, 0),
            ("中下", 2, 1),
            ("右下", 2, 2),
        ]

        self.position_buttons = []
        for name, row, col in positions:
            btn = QPushButton(name)
            btn.setMinimumSize(50, 50)
            btn.clicked.connect(
                lambda checked, p=(col / 2, row / 2): self.set_watermark_position(p)
            )
            position_layout.addWidget(btn, row, col)
            self.position_buttons.append(btn)

        position_group.setLayout(position_layout)

        # 旋转设置
        rotation_group = QGroupBox("旋转角度")
        rotation_layout = QVBoxLayout()

        self.slider_rotation = QSlider(Qt.Orientation.Horizontal)
        self.slider_rotation.setRange(0, 359)
        self.slider_rotation.setValue(0)
        self.slider_rotation.valueChanged.connect(self.on_rotation_changed)

        self.lbl_rotation = QLabel("0°")

        rotation_hbox = QHBoxLayout()
        rotation_hbox.addWidget(self.slider_rotation)
        rotation_hbox.addWidget(self.lbl_rotation)

        rotation_layout.addLayout(rotation_hbox)
        rotation_group.setLayout(rotation_layout)

        layout.addWidget(position_group)
        layout.addWidget(rotation_group)
        layout.addStretch()

        self.tab_position.setLayout(layout)

    def init_export_tab(self):
        layout = QVBoxLayout()

        # 导出文件夹
        folder_group = QHBoxLayout()
        self.txt_export_folder = QLineEdit(self.export_settings["folder"])
        self.btn_select_export_folder = QPushButton("浏览...")
        self.btn_select_export_folder.clicked.connect(self.select_export_folder)

        folder_group.addWidget(self.txt_export_folder)
        folder_group.addWidget(self.btn_select_export_folder)

        # 输出格式
        format_group = QGroupBox("输出格式")
        format_layout = QVBoxLayout()

        self.radio_png = QRadioButton("PNG")
        self.radio_jpg = QRadioButton("JPEG")
        self.radio_png.setChecked(True)

        self.radio_png.toggled.connect(self.on_format_changed)

        format_layout.addWidget(self.radio_png)
        format_layout.addWidget(self.radio_jpg)
        format_group.setLayout(format_layout)

        # JPEG质量
        self.quality_group = QGroupBox("JPEG 质量")
        quality_layout = QVBoxLayout()

        self.slider_quality = QSlider(Qt.Orientation.Horizontal)
        self.slider_quality.setRange(0, 100)
        self.slider_quality.setValue(90)
        self.slider_quality.valueChanged.connect(self.on_quality_changed)

        self.lbl_quality = QLabel("90%")

        quality_hbox = QHBoxLayout()
        quality_hbox.addWidget(self.slider_quality)
        quality_hbox.addWidget(self.lbl_quality)

        quality_layout.addLayout(quality_hbox)
        self.quality_group.setLayout(quality_layout)
        self.quality_group.setEnabled(False)

        # 命名规则
        naming_group = QGroupBox("命名规则")
        naming_layout = QVBoxLayout()

        self.radio_original = QRadioButton("保留原文件名")
        self.radio_prefix = QRadioButton("添加前缀")
        self.radio_suffix = QRadioButton("添加后缀")
        self.radio_suffix.setChecked(True)

        self.txt_prefix = QLineEdit("wm_")
        self.txt_prefix.textChanged.connect(self.on_prefix_changed)

        self.txt_suffix = QLineEdit("_watermarked")
        self.txt_suffix.textChanged.connect(self.on_suffix_changed)

        naming_layout.addWidget(self.radio_original)
        naming_layout.addWidget(self.radio_prefix)
        naming_layout.addWidget(self.txt_prefix)
        naming_layout.addWidget(self.radio_suffix)
        naming_layout.addWidget(self.txt_suffix)

        naming_group.setLayout(naming_layout)

        # 缩放设置
        resize_group = QGroupBox("图片缩放")
        resize_layout = QVBoxLayout()

        self.radio_no_resize = QRadioButton("不缩放")
        self.radio_width = QRadioButton("按宽度")
        self.radio_height = QRadioButton("按高度")
        self.radio_percent = QRadioButton("按百分比")
        self.radio_no_resize.setChecked(True)

        self.spin_resize = QSpinBox()
        self.spin_resize.setRange(10, 200)
        self.spin_resize.setValue(100)
        self.spin_resize.valueChanged.connect(self.on_resize_changed)

        resize_layout.addWidget(self.radio_no_resize)
        resize_layout.addWidget(self.radio_width)
        resize_layout.addWidget(self.radio_height)
        resize_layout.addWidget(self.radio_percent)
        resize_layout.addWidget(self.spin_resize)

        resize_group.setLayout(resize_layout)

        # 连接信号
        self.radio_original.toggled.connect(self.on_naming_changed)
        self.radio_prefix.toggled.connect(self.on_naming_changed)
        self.radio_suffix.toggled.connect(self.on_naming_changed)

        self.radio_no_resize.toggled.connect(self.on_resize_method_changed)
        self.radio_width.toggled.connect(self.on_resize_method_changed)
        self.radio_height.toggled.connect(self.on_resize_method_changed)
        self.radio_percent.toggled.connect(self.on_resize_method_changed)

        layout.addLayout(folder_group)
        layout.addWidget(format_group)
        layout.addWidget(self.quality_group)
        layout.addWidget(naming_group)
        layout.addWidget(resize_group)
        layout.addStretch()

        self.tab_export.setLayout(layout)

    def save_template(self):
        """保存当前水印设置为新模板"""
        if not self.watermark_settings:
            QMessageBox.warning(self, "警告", "没有可保存的水印设置")
            return

        # 请求用户输入模板名称
        name, ok = QInputDialog.getText(self, "保存模板", "请输入模板名称:")
        if not ok or not name.strip():
            return

        # 检查模板名称是否已存在
        for template in self.templates:
            if template["name"] == name:
                QMessageBox.warning(self, "警告", f"模板 '{name}' 已存在")
                return

        # 创建模板（深拷贝设置以避免后续修改影响模板）
        import copy

        new_template = {
            "name": name,
            "watermark_settings": copy.deepcopy(self.watermark_settings),
            "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        # 添加到模板列表并刷新UI
        self.templates.append(new_template)
        self.template_list.addItem(name)

        # 保存模板到文件
        self.save_templates_to_file()
        QMessageBox.information(self, "成功", f"模板 '{name}' 已保存")

    def delete_template(self):
        """删除选中的模板"""
        current_item = self.template_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择要删除的模板")
            return

        name = current_item.text()

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除模板 '{name}' 吗?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # 从数据和列表中移除
            self.templates = [t for t in self.templates if t["name"] != name]
            self.template_list.takeItem(self.template_list.row(current_item))

            # 保存修改到文件
            self.save_templates_to_file()
            QMessageBox.information(self, "成功", f"模板 '{name}' 已删除")

    def load_templates(self):
        """从文件加载模板"""
        try:
            # 确保模板目录存在
            template_dir = os.path.expanduser("~/.watermark_app")
            os.makedirs(template_dir, exist_ok=True)
            template_file = os.path.join(template_dir, "templates.json")

            if os.path.exists(template_file):
                with open(template_file, "r", encoding="utf-8") as f:
                    self.templates = json.load(f)

                # 更新模板列表UI
                self.template_list.clear()
                for template in self.templates:
                    self.template_list.addItem(template["name"])
        except Exception as e:
            print(f"加载模板失败: {str(e)}")
            # 初始化空模板列表
            self.templates = []

    def save_templates_to_file(self):
        """将模板保存到文件"""
        try:
            template_dir = os.path.expanduser("~/.watermark_app")
            os.makedirs(template_dir, exist_ok=True)
            template_file = os.path.join(template_dir, "templates.json")

            with open(template_file, "w", encoding="utf-8") as f:
                json.dump(self.templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存模板失败: {str(e)}")

    def init_templates_tab(self):
        layout = QVBoxLayout()

        # 模板列表
        self.template_list = QListWidget()
        self.template_list.itemClicked.connect(self.on_template_selected)

        # 按钮
        btn_layout = QHBoxLayout()

        self.btn_save_template = QPushButton("保存当前设置为模板")
        self.btn_save_template.clicked.connect(self.save_template)

        self.btn_delete_template = QPushButton("删除选中模板")
        self.btn_delete_template.clicked.connect(self.delete_template)

        btn_layout.addWidget(self.btn_save_template)
        btn_layout.addWidget(self.btn_delete_template)

        layout.addWidget(QLabel("水印模板:"))
        layout.addWidget(self.template_list)
        layout.addLayout(btn_layout)
        layout.addStretch()

        self.tab_templates.setLayout(layout)

    # 事件处理函数
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        self.import_files(files)

    def import_single_image(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.gif);;所有文件 (*)",
        )
        if files:
            self.import_files(files)

    def import_batch_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择多张图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff *.gif);;所有文件 (*)",
        )
        if files:
            self.import_files(files)

    def import_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if folder:
            image_extensions = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".gif"]
            files = []
            for file in os.listdir(folder):
                if os.path.splitext(file)[1].lower() in image_extensions:
                    files.append(os.path.join(folder, file))
            self.import_files(files)

    def import_files(self, files):
        for file in files:
            if not os.path.isfile(file):
                continue

            # 检查文件是否已导入
            exists = any(img["path"] == file for img in self.images)
            if exists:
                continue

            try:
                with Image.open(file) as img:
                    # 转换为RGBA以支持透明
                    if img.mode not in ("RGBA", "LA"):
                        img = img.convert("RGBA")
                    self.images.append({"path": file, "image": img.copy()})

                # 添加到列表
                item = QListWidgetItem(os.path.basename(file))
                pixmap = QPixmap(file)
                item.setIcon(
                    QIcon(
                        pixmap.scaled(
                            128,
                            128,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )
                )
                self.image_list.addItem(item)

            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法导入文件 {file}: {str(e)}")

        # 如果是首次导入，自动选择第一张图片
        if len(self.images) > 0 and self.current_image_index == -1:
            self.current_image_index = 0
            self.image_list.setCurrentRow(0)
            self.update_preview()

    def on_image_selected(self, item):
        index = self.image_list.row(item)
        if 0 <= index < len(self.images):
            self.current_image_index = index
            self.update_preview()

    def remove_selected_image(self):
        if self.current_image_index == -1:
            return

        # 从数据和列表中移除
        del self.images[self.current_image_index]
        self.image_list.takeItem(self.current_image_index)

        # 更新当前索引
        if len(self.images) == 0:
            self.current_image_index = -1
            self.watermark_preview.setText("预览区域")
        else:
            self.current_image_index = min(
                self.current_image_index, len(self.images) - 1
            )
            self.image_list.setCurrentRow(self.current_image_index)
            self.update_preview()

    def on_watermark_type_changed(self):
        is_text = self.radio_text.isChecked()
        self.watermark_settings["type"] = "text" if is_text else "image"

        self.text_settings_group.setEnabled(is_text)
        self.effects_group.setEnabled(is_text)
        self.image_settings_group.setEnabled(not is_text)
        # 确保图片选择按钮可用
        self.btn_select_watermark_image.setEnabled(not is_text)

        self.update_preview()

    def on_text_changed(self, text):
        self.watermark_settings["text"] = text
        self.update_preview()

    def on_font_changed(self, font_family):
        self.watermark_settings["font_family"] = font_family
        self.update_preview()

    def on_font_size_changed(self, size):
        self.watermark_settings["font_size"] = size
        self.update_preview()

    def on_font_style_changed(self):
        self.watermark_settings["font_bold"] = self.chk_bold.isChecked()
        self.watermark_settings["font_italic"] = self.chk_italic.isChecked()
        self.update_preview()

    def choose_color(self):
        current_color = self.watermark_settings["color"]
        initial_color = QColor(
            current_color[0], current_color[1], current_color[2], current_color[3]
        )

        color = QColorDialog.getColor(initial_color, self, "选择颜色")
        if color.isValid():
            self.watermark_settings["color"] = (
                color.red(),
                color.green(),
                color.blue(),
                color.alpha(),
            )
            self.btn_color.setStyleSheet(
                f"background-color: rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()});"
            )
            self.update_preview()

    def select_watermark_image(self):
        file, _ = QFileDialog.getOpenFileName(
            self,
            "选择水印图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.tiff);;所有文件 (*)",
        )
        if file:
            self.watermark_settings["image_path"] = file
            pixmap = QPixmap(file)
            self.lbl_watermark_image.setPixmap(
                pixmap.scaled(
                    100,
                    100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.update_preview()

    def on_transparency_changed(self, value):
        self.watermark_settings["transparency"] = value
        self.lbl_transparency.setText(f"{value}%")

        # 更新颜色的透明度
        r, g, b, _ = self.watermark_settings["color"]
        self.watermark_settings["color"] = (r, g, b, int(value / 100 * 255))

        self.update_preview()

    def on_effects_changed(self):
        self.watermark_settings["shadow"] = self.chk_shadow.isChecked()
        self.watermark_settings["stroke"] = self.chk_stroke.isChecked()
        self.update_preview()

    def on_image_scale_changed(self, value):
        self.watermark_settings["image_scale"] = value
        self.lbl_image_scale.setText(f"{value}%")
        self.update_preview()

    def set_watermark_position(self, position):
        self.watermark_settings["position"] = position
        self.update_preview()

    def on_rotation_changed(self, value):
        self.watermark_settings["rotation"] = value
        self.lbl_rotation.setText(f"{value}°")
        self.update_preview()

    def select_export_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "选择导出文件夹", self.export_settings["folder"]
        )
        if folder:
            self.txt_export_folder.setText(folder)
            self.export_settings["folder"] = folder

    def on_format_changed(self):
        is_png = self.radio_png.isChecked()
        self.export_settings["format"] = "png" if is_png else "jpg"
        self.quality_group.setEnabled(not is_png)
        self.update_preview()

    def on_quality_changed(self, value):
        self.export_settings["quality"] = value
        self.lbl_quality.setText(f"{value}%")

    def on_naming_changed(self):
        if self.radio_original.isChecked():
            self.export_settings["naming"] = "original"
        elif self.radio_prefix.isChecked():
            self.export_settings["naming"] = "prefix"
        elif self.radio_suffix.isChecked():
            self.export_settings["naming"] = "suffix"

    def on_prefix_changed(self, text):
        self.export_settings["prefix"] = text

    def on_suffix_changed(self, text):
        self.export_settings["suffix"] = text

    def on_resize_method_changed(self):
        if self.radio_no_resize.isChecked():
            self.export_settings["resize_method"] = "none"
        elif self.radio_width.isChecked():
            self.export_settings["resize_method"] = "width"
        elif self.radio_height.isChecked():
            self.export_settings["resize_method"] = "height"
        elif self.radio_percent.isChecked():
            self.export_settings["resize_method"] = "percentage"

    def on_resize_changed(self, value):
        self.export_settings["resize_value"] = value

    def start_drag_watermark(self, event):
        if self.current_image_index == -1:
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.pos()

    def drag_watermark(self, event):
        if not self.dragging:
            return

        # 计算相对位置
        preview_rect = self.watermark_preview.rect()
        x = event.pos().x() / preview_rect.width()
        y = event.pos().y() / preview_rect.height()

        # 限制在0-1范围内
        x = max(0, min(1, x))
        y = max(0, min(1, y))

        self.watermark_settings["position"] = (x, y)
        self.update_preview()

    def stop_drag_watermark(self, event):
        self.dragging = False

    def on_template_selected(self, item):
        """模板选中时，应用模板的水印设置"""
        name = item.text()
        for template in self.templates:
            if template["name"] == name:
                # 复制模板的水印设置（避免直接引用导致原模板被修改）
                self.watermark_settings = template["watermark_settings"].copy()
                # 更新UI显示，让设置面板与模板设置同步
                self.update_ui_from_settings()
                # 刷新预览，显示模板效果
                self.update_preview()
                break

    def update_ui_from_settings(self):
        """根据当前水印设置，更新UI控件状态（确保UI与数据同步）"""
        # 1. 更新水印类型（文本/图片）
        if self.watermark_settings["type"] == "text":
            self.radio_text.setChecked(True)
        else:
            self.radio_image.setChecked(True)

        # 2. 更新文本水印设置
        self.txt_watermark_text.setText(self.watermark_settings["text"])
        # 确保字体下拉框显示正确的字体（若字体不存在，显示默认值）
        if self.watermark_settings["font_family"] in self.font_families:
            self.cmb_font.setCurrentText(self.watermark_settings["font_family"])
        else:
            self.cmb_font.setCurrentText("SimHei")  #  fallback到黑体
        self.spin_font_size.setValue(self.watermark_settings["font_size"])
        self.chk_bold.setChecked(self.watermark_settings["font_bold"])
        self.chk_italic.setChecked(self.watermark_settings["font_italic"])

        # 3. 更新颜色选择按钮的显示
        color = self.watermark_settings["color"]  # (r, g, b, a)
        self.btn_color.setStyleSheet(
            f"background-color: rgba({color[0]}, {color[1]}, {color[2]}, {color[3]});"
        )

        # 4. 更新透明度设置
        self.slider_transparency.setValue(self.watermark_settings["transparency"])
        self.lbl_transparency.setText(f"{self.watermark_settings['transparency']}%")

        # 5. 更新文本特效（阴影/描边）
        self.chk_shadow.setChecked(self.watermark_settings["shadow"])
        self.chk_stroke.setChecked(self.watermark_settings["stroke"])

        # 6. 更新图片水印设置
        img_path = self.watermark_settings.get("image_path", "")
        self.lbl_watermark_image.setText(
            "已选择图片" if img_path and os.path.exists(img_path) else "未选择图片"
        )
        # 显示图片水印的缩略图（若有）
        if img_path and os.path.exists(img_path):
            pixmap = QPixmap(img_path)
            self.lbl_watermark_image.setPixmap(
                pixmap.scaled(
                    100,
                    100,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.lbl_watermark_image.setPixmap(QPixmap())  # 清空缩略图
        self.slider_image_scale.setValue(self.watermark_settings["image_scale"])
        self.lbl_image_scale.setText(f"{self.watermark_settings['image_scale']}%")

        # 7. 更新旋转角度
        self.slider_rotation.setValue(self.watermark_settings["rotation"])
        self.lbl_rotation.setText(f"{self.watermark_settings['rotation']}°")

        # 8. 更新UI控件的启用状态（文本/图片模式切换）
        is_text_mode = self.watermark_settings["type"] == "text"
        self.text_settings_group.setEnabled(is_text_mode)
        self.effects_group.setEnabled(is_text_mode)
        self.image_settings_group.setEnabled(not is_text_mode)
        self.btn_select_watermark_image.setEnabled(not is_text_mode)

    def load_last_settings(self):
        """加载用户上次使用的设置"""
        try:
            # 设置文件存储位置
            settings_dir = os.path.expanduser("~/.watermark_app")
            os.makedirs(settings_dir, exist_ok=True)
            settings_file = os.path.join(settings_dir, "last_settings.json")

            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as f:
                    saved_settings = json.load(f)

                    # 恢复水印设置
                    if "watermark_settings" in saved_settings:
                        self.watermark_settings.update(
                            saved_settings["watermark_settings"]
                        )

                    # 恢复导出设置
                    if "export_settings" in saved_settings:
                        self.export_settings.update(saved_settings["export_settings"])
                        # 更新导出设置UI
                        self.txt_export_folder.setText(self.export_settings["folder"])
                        self.txt_prefix.setText(self.export_settings["prefix"])
                        self.txt_suffix.setText(self.export_settings["suffix"])
                        self.slider_quality.setValue(self.export_settings["quality"])
                        self.lbl_quality.setText(f"{self.export_settings['quality']}%")
                        self.spin_resize.setValue(self.export_settings["resize_value"])

                        # 恢复格式选择
                        if self.export_settings["format"] == "jpg":
                            self.radio_jpg.setChecked(True)
                            self.quality_group.setEnabled(True)
                        else:
                            self.radio_png.setChecked(True)
                            self.quality_group.setEnabled(False)

                        # 恢复命名规则
                        if self.export_settings["naming"] == "original":
                            self.radio_original.setChecked(True)
                        elif self.export_settings["naming"] == "prefix":
                            self.radio_prefix.setChecked(True)
                        else:
                            self.radio_suffix.setChecked(True)

                        # 恢复缩放方式
                        if self.export_settings["resize_method"] == "width":
                            self.radio_width.setChecked(True)
                        elif self.export_settings["resize_method"] == "height":
                            self.radio_height.setChecked(True)
                        elif self.export_settings["resize_method"] == "percentage":
                            self.radio_percent.setChecked(True)
                        else:
                            self.radio_no_resize.setChecked(True)

                # 同步UI与恢复的设置
                self.update_ui_from_settings()

        except Exception as e:
            print(f"加载上次设置失败: {str(e)}")
            # 失败时不影响程序运行，使用默认设置

    def save_last_settings(self):
        """退出时保存当前设置，供下次使用"""
        try:
            settings_dir = os.path.expanduser("~/.watermark_app")
            os.makedirs(settings_dir, exist_ok=True)
            settings_file = os.path.join(settings_dir, "last_settings.json")

            # 需要保存的设置
            settings_to_save = {
                "watermark_settings": self.watermark_settings,
                "export_settings": self.export_settings,
            }

            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump(settings_to_save, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"保存设置失败: {str(e)}")

    # 重写关闭事件，确保退出时保存设置
    def closeEvent(self, event):
        self.save_last_settings()
        event.accept()

    def update_preview(self):
        if self.current_image_index == -1:
            return

        # 获取当前图片
        current_image = self.images[self.current_image_index]["image"].copy()

        # 应用水印
        watermarked_image = self.apply_watermark(current_image)

        # 转换为QPixmap并显示
        q_image = ImageQt.ImageQt(watermarked_image)
        pixmap = QPixmap.fromImage(q_image)

        # 缩放以适应预览窗口，但保持原始比例和预览框大小
        scaled_pixmap = pixmap.scaled(
            self.watermark_preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.watermark_preview.setPixmap(scaled_pixmap)
        # 固定预览框大小
        self.watermark_preview.setFixedSize(self.watermark_preview.size())

    def apply_watermark(self, image):
        # 创建一个副本以避免修改原图
        img = image.copy()

        # 根据水印类型应用不同的处理
        if self.watermark_settings["type"] == "text":
            return self.apply_text_watermark(img)
        else:
            return self.apply_image_watermark(img)

    def get_available_fonts(self):
        """获取系统中Pillow可实际加载的字体列表（过滤无效字体）"""
        from PIL import ImageFont

        available_fonts = []
        # 先获取Qt识别的所有字体名
        qt_fonts = QFontDatabase.families()

        # 逐个验证字体是否能被Pillow加载（避免“Qt显示但Pillow无法使用”问题）
        for font_name in qt_fonts:
            try:
                # 尝试加载12号字体（仅验证可用性，不占用资源）
                temp_font = ImageFont.truetype(font_name, 12, encoding="utf-8")
                available_fonts.append(font_name)
                # 释放临时字体资源（可选）
                del temp_font
            except Exception:
                # 跳过无法加载的字体（如字体文件损坏、路径不存在等）
                continue

        # 兜底：若可用字体为空，添加常用默认字体
        if not available_fonts:
            available_fonts = [
                "SimHei",
                "Microsoft YaHei",
                "SimSun",
                "KaiTi",
                "Arial",
                "Times New Roman",
            ]

        return available_fonts

    def apply_text_watermark(self, image):
        # 导入必要模块
        from PIL import ImageDraw, ImageFont
        import glob

        # 1. 创建水印绘制图层
        watermark_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark_layer)

        # 2. 获取当前水印配置参数
        text = self.watermark_settings["text"]
        font_family = self.watermark_settings["font_family"]
        font_size = self.watermark_settings["font_size"]
        is_bold = self.watermark_settings["font_bold"]
        is_italic = self.watermark_settings["font_italic"]
        color = self.watermark_settings["color"]
        rotation = self.watermark_settings["rotation"]
        shadow_enabled = self.watermark_settings["shadow"]
        stroke_enabled = self.watermark_settings["stroke"]

        # 修复：确保文本是Unicode字符串
        if isinstance(text, str):
            # 对于包含非ASCII字符（如中文）的文本，确保正确处理
            pass
        else:
            # 转换为Unicode字符串
            text = str(text, encoding="utf-8")

        # 3. 核心逻辑：加载字体
        font = None
        font_path = None
        windows_font_dir = "C:/Windows/Fonts/"  # Windows系统默认字体目录

        # 3.1 中文常见字体映射表
        chinese_font_map = {
            "SimHei": "simhei.ttf",  # 黑体（常规）
            "Microsoft YaHei": "msyh.ttc",  # 微软雅黑
            "SimSun": "simsun.ttc",  # 宋体
            "KaiTi": "simkai.ttf",  # 楷体
            "Arial": "arial.ttf",  # Arial
            "Arial Bold": "arialbd.ttf",  # Arial粗体
            "Times New Roman": "times.ttf",  # Times New Roman
        }

        # 3.2 优先使用映射表加载字体
        if font_family in chinese_font_map:
            target_font_file = chinese_font_map[font_family]
            font_path = os.path.join(windows_font_dir, target_font_file)

            if os.path.exists(font_path):
                try:
                    # 处理TTF集合文件（.ttc）的样式索引
                    if font_path.endswith(".ttc"):
                        if is_bold and is_italic:
                            font = ImageFont.truetype(
                                font_path, font_size, index=3, encoding="utf-8"
                            )
                        elif is_bold:
                            font = ImageFont.truetype(
                                font_path, font_size, index=1, encoding="utf-8"
                            )
                        elif is_italic:
                            font = ImageFont.truetype(
                                font_path, font_size, index=2, encoding="utf-8"
                            )
                        else:
                            font = ImageFont.truetype(
                                font_path, font_size, index=0, encoding="utf-8"
                            )
                    else:
                        if is_bold and f"{font_family} Bold" in chinese_font_map:
                            bold_font_file = chinese_font_map[f"{font_family} Bold"]
                            bold_font_path = os.path.join(
                                windows_font_dir, bold_font_file
                            )
                            if os.path.exists(bold_font_path):
                                font = ImageFont.truetype(
                                    bold_font_path, font_size, encoding="utf-8"
                                )
                            else:
                                font = ImageFont.truetype(
                                    font_path, font_size, encoding="utf-8"
                                )
                        else:
                            font = ImageFont.truetype(
                                font_path, font_size, encoding="utf-8"
                            )

                    print(f"✅ 成功加载字体：{font_family}，路径：{font_path}")

                except Exception as e:
                    print(f"❌ 加载映射字体失败：{str(e)}，尝试搜索方式加载")

        # 3.3 若映射表未命中，搜索字体目录
        if not font:
            search_keyword = font_family
            if is_bold and is_italic:
                search_keyword += " Bold Italic"
            elif is_bold:
                search_keyword += " Bold"
            elif is_italic:
                search_keyword += " Italic"

            matched_files = []
            for ext in [".ttf", ".ttc", ".otf"]:
                search_pattern = os.path.join(
                    windows_font_dir, f"*{search_keyword}*{ext}"
                )
                matched_files = glob.glob(search_pattern, recursive=False)

                if not matched_files:
                    search_pattern_lower = os.path.join(
                        windows_font_dir, f"*{search_keyword.lower()}*{ext}"
                    )
                    matched_files = glob.glob(search_pattern_lower, recursive=False)

                if matched_files:
                    font_path = matched_files[0]
                    break

            if matched_files:
                try:
                    # 关键修复：明确指定编码为utf-8
                    font = ImageFont.truetype(font_path, font_size, encoding="utf-8")
                    print(f"✅ 成功搜索并加载字体：{font_path}")
                except Exception as e:
                    print(f"❌ 加载搜索到的字体失败：{str(e)}")

        # 3.4 兜底方案
        if not font:
            # 尝试加载默认中文字体
            try:
                font = ImageFont.truetype("simhei.ttf", font_size, encoding="utf-8")
                print(f"⚠️ 使用系统默认中文字体")
            except:
                font = ImageFont.load_default()
                QMessageBox.warning(
                    self,
                    "字体加载失败",
                    f"当前选择的字体「{font_family}」无法加载，已自动切换为默认字体。\n建议选择以下系统自带字体：\n• SimHei（黑体）\n• Microsoft YaHei（微软雅黑）\n• SimSun（宋体）",
                )
                print(f"⚠️ 所有字体加载方式失败，使用Pillow默认字体")

        # 4. 计算文本尺寸（修复中文尺寸计算问题）
        try:
            # 尝试使用textbbox计算（Pillow 8.0+）
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except Exception as e:
            # 兼容旧版本Pillow
            print(f"使用textbbox失败，尝试textsize: {e}")
            text_width, text_height = draw.textsize(text, font=font)

        # 5. 计算水印位置
        img_width, img_height = image.size
        x = (img_width - text_width) * self.watermark_settings["position"][0]
        y = (img_height - text_height) * self.watermark_settings["position"][1]

        # 6. 绘制水印
        if rotation != 0:
            text_layer = Image.new("RGBA", (text_width, text_height), (0, 0, 0, 0))
            text_draw = ImageDraw.Draw(text_layer)

            if shadow_enabled:
                shadow_color = (0, 0, 0, int(color[3] * 0.5))
                text_draw.text((2, 2), text, font=font, fill=shadow_color)

            if stroke_enabled:
                stroke_width = 2
                for dx in [-stroke_width, 0, stroke_width]:
                    for dy in [-stroke_width, 0, stroke_width]:
                        if dx != 0 or dy != 0:
                            text_draw.text(
                                (dx, dy), text, font=font, fill=(0, 0, 0, color[3])
                            )

            text_draw.text((0, 0), text, font=font, fill=color)

            rotated_text = text_layer.rotate(
                rotation, expand=True, resample=Image.Resampling.BICUBIC
            )

            rotated_width, rotated_height = rotated_text.size
            x = x - (rotated_width - text_width) / 2
            y = y - (rotated_height - text_height) / 2

            watermark_layer.paste(rotated_text, (int(x), int(y)), rotated_text)

        else:
            if shadow_enabled:
                draw.text(
                    (x + 2, y + 2), text, font=font, fill=(0, 0, 0, int(color[3] * 0.5))
                )

            if stroke_enabled:
                stroke_width = 2
                for dx in [-stroke_width, 0, stroke_width]:
                    for dy in [-stroke_width, 0, stroke_width]:
                        if dx != 0 or dy != 0:
                            draw.text(
                                (x + dx, y + dy),
                                text,
                                font=font,
                                fill=(0, 0, 0, color[3]),
                            )

            draw.text((x, y), text, font=font, fill=color)

        # 7. 合并水印图层到原图
        return Image.alpha_composite(image, watermark_layer)

    def apply_image_watermark(self, image):
        """应用图片水印到原图"""
        # 创建原图副本
        img = image.copy()

        # 获取水印图片路径
        watermark_path = self.watermark_settings.get("image_path", "")
        if not watermark_path or not os.path.exists(watermark_path):
            return img  # 没有有效水印图片时返回原图

        try:
            # 打开水印图片
            with Image.open(watermark_path) as watermark_img:
                # 转换为RGBA以支持透明
                if watermark_img.mode not in ("RGBA", "LA"):
                    watermark_img = watermark_img.convert("RGBA")

                # 根据设置调整水印大小
                scale = self.watermark_settings["image_scale"] / 100.0
                new_width = int(watermark_img.width * scale)
                new_height = int(watermark_img.height * scale)

                # 确保水印尺寸有效
                new_width = max(10, new_width)
                new_height = max(10, new_height)

                # 调整水印大小（高质量缩放）
                watermark_resized = watermark_img.resize(
                    (new_width, new_height), Image.Resampling.LANCZOS
                )

                # 调整水印透明度
                transparency = self.watermark_settings["transparency"]
                alpha = watermark_resized.split()[3]  # 获取Alpha通道
                alpha = ImageEnhance.Brightness(alpha).enhance(transparency / 100.0)
                watermark_resized.putalpha(alpha)

                # 处理旋转
                rotation = self.watermark_settings["rotation"]
                if rotation != 0:
                    watermark_rotated = watermark_resized.rotate(
                        rotation, expand=True, resample=Image.Resampling.BICUBIC
                    )
                else:
                    watermark_rotated = watermark_resized

                # 计算水印位置
                img_width, img_height = img.size
                wm_width, wm_height = watermark_rotated.size

                # 根据相对位置计算绝对坐标
                x = int((img_width - wm_width) * self.watermark_settings["position"][0])
                y = int(
                    (img_height - wm_height) * self.watermark_settings["position"][1]
                )

                # 确保水印位置在图片范围内
                x = max(0, min(x, img_width - wm_width))
                y = max(0, min(y, img_height - wm_height))

                # 创建水印图层并合并
                watermark_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
                watermark_layer.paste(watermark_rotated, (x, y), watermark_rotated)

                return Image.alpha_composite(img, watermark_layer)

        except Exception as e:
            print(f"应用图片水印失败: {str(e)}")
            QMessageBox.warning(self, "错误", f"无法应用图片水印: {str(e)}")
            return img


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 使用Fusion风格，跨平台一致性更好
    window = WatermarkApp()
    window.show()
    sys.exit(app.exec())
