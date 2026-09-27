"""
ينشئ صورة Thumbnail من صورة خلفية (عادة أول أو أقوى مشهد) + عنوان نصي بارز،
بدلاً من الاعتماد الكامل على مولّد صور عشوائي قد ينتج صورة غير مرتبطة بالموضوع
(هذه هي المشكلة الملاحظة في الفيديو المرجعي).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


def make_thumbnail(background_path: Path, title: str, out_path: Path, config: dict) -> Path:
    thumb_cfg = config["thumbnail"]
    img = Image.open(background_path).convert("RGB")
    img = img.resize((1280, 720))

    # طبقة تعتيم سفلية لتحسين وضوح النص
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle([0, 460, 1280, 720], fill=(0, 0, 0, 150))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(img)
    font_path = thumb_cfg.get("font_path")
    try:
        font = ImageFont.truetype(font_path, 90)
    except Exception:
        font = ImageFont.load_default()

    # تقسيم العنوان إلى سطرين إذا كان طويلاً
    words = title.upper().split()
    mid = len(words) // 2 or 1
    line1 = " ".join(words[:mid])
    line2 = " ".join(words[mid:])

    accent = thumb_cfg.get("accent_color", "#FFD400")

    def draw_stroked(text, y):
        x = 60
        for dx in (-3, 0, 3):
            for dy in (-3, 0, 3):
                draw.text((x + dx, y + dy), text, font=font, fill="black")
        draw.text((x, y), text, font=font, fill=accent)

    draw_stroked(line1, 480)
    if line2:
        draw_stroked(line2, 580)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, quality=95)
    return out_path
