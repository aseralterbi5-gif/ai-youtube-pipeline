"""
يبني الفيديو النهائي من: صور المشاهد + ملفات الصوت المرافقة لها.
لكل مشهد: يُنشئ مقطع فيديو بحركة تكبير/بانّ بطيئة (Ken Burns) بطول = مدة الصوت بالضبط،
ثم يدمج كل المقاطع تباعًا، ويضيف موسيقى خلفية اختيارية بمستوى صوت منخفض.

يعتمد على ffmpeg (يجب توفره في بيئة التشغيل - في GitHub Actions يُثبَّت في workflow).
"""
import json
import subprocess
from pathlib import Path


def _run(cmd: list) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"فشل أمر ffmpeg:\n{' '.join(cmd)}\n{result.stderr}")


def _get_duration(audio_path: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(audio_path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(out.stdout)["format"]["duration"])


def _build_scene_clip(image_path: Path, audio_path: Path, out_path: Path,
                       resolution: str, fps: int, ken_burns: bool) -> None:
    width, height = resolution.split("x")
    duration = _get_duration(audio_path)
    total_frames = max(int(duration * fps), fps)

    if ken_burns:
        # تكبير بطيء تدريجي من 1.0 إلى 1.08 طوال مدة المقطع
        zoom_filter = (
            f"scale=8000:-1,zoompan=z='min(zoom+0.0007,1.08)':"
            f"d={total_frames}:s={width}x{height}:fps={fps}"
        )
    else:
        zoom_filter = f"scale={width}:{height}"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(audio_path),
        "-vf", zoom_filter,
        "-c:v", "libx264", "-t", str(duration), "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest",
        str(out_path),
    ]
    _run(cmd)


def build_video(image_paths: list, audio_paths: list, out_path: Path,
                 config: dict, work_dir: Path) -> Path:
    resolution = config["video"]["resolution"]
    fps = config["video"]["fps"]
    ken_burns = config["video"].get("ken_burns", True)

    clips_dir = work_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    clip_paths = []
    for i, (img, aud) in enumerate(zip(image_paths, audio_paths)):
        clip_path = clips_dir / f"clip_{i:03d}.mp4"
        _build_scene_clip(img, aud, clip_path, resolution, fps, ken_burns)
        clip_paths.append(clip_path)

    # دمج المقاطع تباعًا عبر concat demuxer
    concat_list = work_dir / "concat_list.txt"
    concat_list.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in clip_paths), encoding="utf-8"
    )

    merged_path = work_dir / "merged_no_music.mp4"
    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list), "-c", "copy", str(merged_path),
    ])

    music_path = Path(config["video"].get("background_music_path", ""))
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if music_path and music_path.exists():
        # مزج الموسيقى بمستوى منخفض (٠.١٥) مع الصوت الأصلي، وتكرارها إذا كانت أقصر من الفيديو
        _run([
            "ffmpeg", "-y", "-i", str(merged_path),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex",
            "[1:a]volume=0.15[bg];[0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            str(out_path),
        ])
    else:
        merged_path.rename(out_path)

    return out_path
