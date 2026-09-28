"""
يرفع الفيديو النهائي + الصورة المصغرة إلى يوتيوب تلقائيًا بدون أي تدخل بشري،
باستخدام Refresh Token محفوظ مسبقًا (يُنشأ مرة واحدة يدويًا فقط - راجع README).

هذا هو ما يسمح للنظام بالعمل "حتى لو كان الجهاز مغلقًا": لا حاجة لفتح متصفح
أو تسجيل دخول تفاعلي أثناء التشغيل الآلي على GitHub Actions أو أي خادم سحابي.
"""
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def _get_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: Path, thumbnail_path: Path, title: str,
                  description: str, tags: list, config: dict) -> str:
    youtube = _get_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": tags[:15],
            "categoryId": "27",  # Education
        },
        "status": {
            "privacyStatus": config["channel"].get("upload_privacy", "private"),
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(
                config["channel"].get("contains_synthetic_media", False)
            ),
        },
    }

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"رفع الفيديو: {int(status.progress() * 100)}%")

    video_id = response["id"]

    youtube.thumbnails().set(
        videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))
    ).execute()

    return f"https://youtu.be/{video_id}"
