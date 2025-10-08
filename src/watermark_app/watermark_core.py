from PIL import Image, ImageDraw, ImageFont

def apply_text_watermark(image_path, text, font_path=None, font_size=32, color=(255, 255, 255), alpha=128):
    """
    在图片上添加文本水印。
    :param image_path: 原始图片路径
    :param text: 水印文本
    :param font_path: 字体路径（None 表示使用默认字体）
    :param font_size: 字号
    :param color: 字体颜色 (R, G, B)
    :param alpha: 透明度 (0–255)
    :return: 带水印的 Image 对象
    """
    base = Image.open(image_path).convert("RGBA")
    txt_layer = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)

    font = ImageFont.truetype(font_path, font_size) if font_path else ImageFont.load_default()
    text_w, text_h = draw.textsize(text, font=font)
    pos = (base.size[0] - text_w - 20, base.size[1] - text_h - 20)  # 右下角

    r, g, b = color
    draw.text(pos, text, fill=(r, g, b, alpha), font=font)

    combined = Image.alpha_composite(base, txt_layer)
    return combined.convert("RGB")

def apply_image_watermark(image_path, watermark_path, scale=0.3, alpha=128):
    """
    在图片上添加图片水印。
    :param image_path: 原图路径
    :param watermark_path: 水印图片路径（必须为 PNG）
    :param scale: 缩放比例
    :param alpha: 透明度 (0–255)
    :return: 带水印的 Image 对象
    """
    base = Image.open(image_path).convert("RGBA")
    wm = Image.open(watermark_path).convert("RGBA")

    # 缩放水印
    w = int(base.width * scale)
    h = int(wm.height * w / wm.width)
    wm = wm.resize((w, h))

    # 调整透明度
    wm.putalpha(alpha)

    # 右下角
    pos = (base.width - w - 20, base.height - h - 20)
    base.alpha_composite(wm, dest=pos)

    return base.convert("RGB")
