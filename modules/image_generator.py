"""
يحوّل كل "visual_description" في المشاهد إلى صورة فعلية،
مع إضافة توجيه أسلوب ثابت (style) لكل الصور حتى تتّسق بصريًا مع بعضها
(هذه هي المشكلة التي أشار إليها الفيديو المرجعي: عدم الاتساق البصري بين المشاهد).
"""
import os
import base64
from pathlib import Path

STYLE_SUFFIXES = {
    "realistic": "photorealistic, cinematic lighting, highly detailed, 8k",
    "painting": "oil painting style, dramatic lighting, fine art, textured brush strokes",
    "3d_model": "3D render, cinematic, octane render, realistic materials",
    "drawing": "detailed pencil and ink illustration, cross-hatching shading",
    "comic": "comic book illustration style, bold outlines, dramatic shading",
    "bw": "black and white, high contrast, dramatic shadows, monochrome",
    "low_poly": "low poly 3D art style, geometric, flat shading",
}


def _style_suffix(style: str) -> str:
    return STYLE_SUFFIXES.get(style, STYLE_SUFFIXES["painting"])


class ImageGenerator:
    def __init__(self, provider: str, style: str, aspect_ratio: str = "16:9"):
        self.provider = provider
        self.style = style
        self.aspect_ratio = aspect_ratio
        if provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        elif provider == "stability":
            self.api_key = os.environ["STABILITY_API_KEY"]
        else:
            raise ValueError(f"مزوّد صور غير مدعوم: {provider}")

    def generate(self, prompt: str, out_path: Path) -> Path:
        full_prompt = f"{prompt}, {_style_suffix(self.style)}. No text, no watermark, no logos."
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if self.provider == "openai":
            size = "1536x1024" if self.aspect_ratio == "16:9" else "1024x1024"
            result = self.client.images.generate(
                model="gpt-image-1",
                prompt=full_prompt,
                size=size,
                n=1,
            )
            image_b64 = result.data[0].b64_json
            out_path.write_bytes(base64.b64decode(image_b64))

        elif self.provider == "stability":
            import requests
            resp = requests.post(
                "https://api.stability.ai/v2beta/stable-image/generate/core",
                headers={"authorization": f"Bearer {self.api_key}", "accept": "image/*"},
                files={"none": ""},
                data={"prompt": full_prompt, "aspect_ratio": self.aspect_ratio, "output_format": "png"},
                timeout=120,
            )
            resp.raise_for_status()
            out_path.write_bytes(resp.content)

        return out_path


def generate_all_scene_images(gen: ImageGenerator, script: dict, out_dir: Path) -> list:
    """يولّد صورة لكل مشهد ويعيد قائمة بمسارات الصور بنفس ترتيب المشاهد."""
    paths = []
    for scene in script["scenes"]:
        n = scene["scene_number"]
        out_path = out_dir / f"scene_{n:03d}.png"
        gen.generate(scene["visual_description"], out_path)
        paths.append(out_path)
    return paths
