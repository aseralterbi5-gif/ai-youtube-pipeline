"""
يحلّل قناة يوتيوب ناجحة مرجعية (كما فعل صاحب الفيديو الأصلي بأداة TubeGenAI)
ويستخرج نمط العناوين الناجحة، ثم يطلب من الـLLM اقتراح مواضيع جديدة بنفس النمط.

هذه الخطوة كانت ناقصة في النسخة السابقة من المشروع - وهي أول خطوة في الفيديو المرجعي:
"تحليل قناة ناجحة" قبل "اختيار فكرة فيديو".

يستخدم YouTube Data API v3 بمفتاح API عادي (قراءة فقط - لا يحتاج OAuth إطلاقًا،
مختلف تمامًا عن مفتاح الرفع).
"""
import os
from typing import List

import requests

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


def _get_uploads_playlist_id(channel_id: str, api_key: str) -> str:
    resp = requests.get(
        f"{YOUTUBE_API_BASE}/channels",
        params={"part": "contentDetails", "id": channel_id, "key": api_key},
        timeout=30,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        raise ValueError(f"لم يتم العثور على القناة: {channel_id}")
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def fetch_recent_titles(channel_id: str, api_key: str, max_results: int = 25) -> List[str]:
    """يجلب أحدث عناوين فيديوهات القناة المرجعية (بيانات عامة فقط، لا حاجة لملكية القناة)."""
    uploads_playlist_id = _get_uploads_playlist_id(channel_id, api_key)

    titles = []
    page_token = None
    while len(titles) < max_results:
        resp = requests.get(
            f"{YOUTUBE_API_BASE}/playlistItems",
            params={
                "part": "snippet",
                "playlistId": uploads_playlist_id,
                "maxResults": min(50, max_results - len(titles)),
                "pageToken": page_token,
                "key": api_key,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        titles.extend(item["snippet"]["title"] for item in data.get("items", []))
        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return titles[:max_results]


ANALYSIS_PROMPT_TEMPLATE = """\
هذه قائمة أحدث عناوين فيديوهات من قناة يوتيوب ناجحة في نفس مجال '{niche}':

{titles_block}

المطلوب:
1) استخرج بإيجاز (سطرين فقط) النمط المشترك بين هذه العناوين (الصياغة، طول العنوان، نوع الفضول الذي تثيره).
2) بناءً على هذا النمط، اقترح 8 عناوين فيديو جديدة ومختلفة تمامًا عن القائمة أعلاه،
   لكن بنفس الأسلوب والنمط الناجح.

أخرج النتيجة بصيغة JSON فقط بدون أي نص إضافي:
{{
  "pattern_summary": "...",
  "suggested_topics": ["...", "..."]
}}
"""


def analyze_reference_channel(llm_client, channel_id: str, niche: str) -> dict:
    api_key = os.environ["YOUTUBE_API_KEY"]
    titles = fetch_recent_titles(channel_id, api_key)

    if not titles:
        raise ValueError("لم يتم جلب أي عناوين من القناة المرجعية.")

    titles_block = "\n".join(f"- {t}" for t in titles)
    prompt = ANALYSIS_PROMPT_TEMPLATE.format(niche=niche, titles_block=titles_block)

    raw = llm_client.generate_text(prompt, max_tokens=800)
    import json
    import re

    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
    return json.loads(cleaned)
