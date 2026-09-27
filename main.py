"""
نقطة التشغيل الرئيسية للنظام الآلي الكامل.
يُستدعى هذا الملف مجدولًا (Scheduled) من GitHub Actions - أنظر:
.github/workflows/auto_pipeline.yml

التسلسل الكامل:
اختيار موضوع -> سكربت + مشاهد -> صور -> صوت -> فيديو -> صورة مصغرة -> رفع يوتيوب -> إشعار
"""
import sys
import traceback
from datetime import datetime
from pathlib import Path

import yaml

from modules.topic_picker import pick_topic
from modules.channel_analyzer import analyze_reference_channel
from modules.script_writer import LLMClient, generate_script
from modules.image_generator import ImageGenerator, generate_all_scene_images
from modules.tts_generator import generate_all_scene_audio
from modules.video_builder import build_video
from modules.thumbnail_maker import make_thumbnail
from modules.youtube_uploader import upload_video
from modules.notifier import notify


def load_config() -> dict:
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_pipeline() -> str:
    config = load_config()
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    work_dir = Path("data") / run_id
    work_dir.mkdir(parents=True, exist_ok=True)

    llm = LLMClient(provider=config["providers"]["llm"])

    extra_topics = []
    ca_cfg = config.get("channel_analysis", {})
    if ca_cfg.get("enabled") and ca_cfg.get("reference_channel_id"):
        print("1) تحليل القناة المرجعية...")
        try:
            analysis = analyze_reference_channel(
                llm, ca_cfg["reference_channel_id"], config["channel"]["niche"]
            )
            extra_topics = analysis.get("suggested_topics", [])
            print(f"   -> نمط العناوين: {analysis.get('pattern_summary', '')}")
            print(f"   -> {len(extra_topics)} فكرة مقترحة من القناة المرجعية")
        except Exception as e:
            print(f"   تحذير: فشل تحليل القناة المرجعية ({e}) - سيُستخدم seed_topics بدلاً منه")

    print("2) اختيار الموضوع...")
    topic = pick_topic(config, llm_client=llm, extra_topics=extra_topics)
    print(f"   -> {topic}")

    print("3) توليد السكربت وتقسيم المشاهد...")
    script = generate_script(llm, topic, config)
    (work_dir / "script.json").write_text(
        __import__("json").dumps(script, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("4) توليد الصور لكل مشهد...")
    img_gen = ImageGenerator(
        provider=config["providers"]["image"],
        style=config["image"]["style"],
        aspect_ratio=config["image"]["aspect_ratio"],
    )
    image_paths = generate_all_scene_images(img_gen, script, work_dir / "images")

    print("5) توليد التعليق الصوتي لكل مشهد...")
    audio_paths = generate_all_scene_audio(
        script, work_dir / "audio", provider=config["providers"]["tts"]
    )

    print("6) بناء الفيديو النهائي...")
    final_video = build_video(
        image_paths, audio_paths, work_dir / "final_video.mp4", config, work_dir
    )

    print("7) إنشاء الصورة المصغرة...")
    thumb_path = make_thumbnail(
        image_paths[0], script["title"], work_dir / "thumbnail.jpg", config
    )

    print("8) الرفع إلى يوتيوب...")
    description = (
        f"{script['title']}\n\n"
        "تم إنتاج هذا الفيديو بمساعدة نظام آلي (AI-assisted production).\n"
    )
    tags = [config["channel"]["niche"]]
    video_url = upload_video(
        final_video, thumb_path, script["title"], description, tags, config
    )

    print(f"تم بنجاح: {video_url}")
    return video_url


if __name__ == "__main__":
    try:
        url = run_pipeline()
        notify(f"✅ تم إنشاء ورفع فيديو جديد بنجاح:\n{url}")
    except Exception:
        error_text = traceback.format_exc()
        print(error_text, file=sys.stderr)
        notify(f"❌ فشل التشغيل الآلي:\n{error_text[-1500:]}")
        sys.exit(1)
