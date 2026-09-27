"""
يحوّل نص كل مشهد إلى ملف صوتي.
الخيار الافتراضي: edge-tts (مجاني تمامًا، لا يحتاج مفتاح API، جودة جيدة).
خيار بديل: ElevenLabs (جودة أعلى، يحتاج مفتاح ورصيد).
"""
import asyncio
import os
from pathlib import Path


async def _edge_tts_save(text: str, out_path: Path, voice: str = "en-US-GuyNeural") -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def generate_narration_audio(text: str, out_path: Path, provider: str = "edge-tts") -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if provider == "edge-tts":
        asyncio.run(_edge_tts_save(text, out_path))

    elif provider == "elevenlabs":
        import requests
        api_key = os.environ["ELEVENLABS_API_KEY"]
        voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        resp = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={"xi-api-key": api_key, "accept": "audio/mpeg"},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
            timeout=120,
        )
        resp.raise_for_status()
        out_path.write_bytes(resp.content)

    else:
        raise ValueError(f"مزوّد TTS غير مدعوم: {provider}")

    return out_path


def generate_all_scene_audio(script: dict, out_dir: Path, provider: str = "edge-tts") -> list:
    paths = []
    for scene in script["scenes"]:
        n = scene["scene_number"]
        out_path = out_dir / f"scene_{n:03d}.mp3"
        generate_narration_audio(scene["narration"], out_path, provider)
        paths.append(out_path)
    return paths
