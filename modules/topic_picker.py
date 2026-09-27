"""
يختار موضوع الفيديو القادم.
المنطق: يحتفظ بملف data/used_topics.json بالمواضيع المستخدمة سابقًا
حتى لا يكرر نفس الموضوع، ويختار أول موضوع غير مستخدم من config.yaml.
إذا نفدت القائمة، يطلب من الـ LLM اقتراح مواضيع جديدة بنفس النمط.
"""
import json
import os
from pathlib import Path

USED_TOPICS_FILE = Path("data/used_topics.json")


def _load_used() -> list:
    if USED_TOPICS_FILE.exists():
        return json.loads(USED_TOPICS_FILE.read_text(encoding="utf-8"))
    return []


def _save_used(used: list) -> None:
    USED_TOPICS_FILE.parent.mkdir(parents=True, exist_ok=True)
    USED_TOPICS_FILE.write_text(
        json.dumps(used, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def pick_topic(config: dict, llm_client=None, extra_topics: list = None) -> str:
    # extra_topics: مواضيع مقترحة من تحليل القناة المرجعية (channel_analyzer)
    # تُعطى أولوية أعلى من seed_topics الثابتة في config.yaml لأنها أحدث وأقرب للترند
    seed_topics = (extra_topics or []) + config.get("seed_topics", [])
    used = _load_used()

    for topic in seed_topics:
        if topic not in used:
            used.append(topic)
            _save_used(used)
            return topic

    # القائمة اليدوية نفدت -> نطلب من الـ LLM اقتراح مواضيع جديدة بنفس النمط
    if llm_client is None:
        raise RuntimeError(
            "نفدت المواضيع اليدوية في config.yaml ولا يوجد عميل LLM لتوليد مواضيع جديدة."
        )

    niche = config["channel"]["niche"]
    prompt = (
        f"اقترح 10 عناوين فيديو يوتيوب جديدة ومختلفة تمامًا عن هذه القائمة، "
        f"ضمن مجال '{niche}'، كل عنوان في سطر منفصل بدون ترقيم:\n"
        + "\n".join(used)
    )
    new_ideas_raw = llm_client.generate_text(prompt, max_tokens=400)
    new_ideas = [line.strip("-• ").strip() for line in new_ideas_raw.splitlines() if line.strip()]
    new_ideas = [t for t in new_ideas if t not in used]

    if not new_ideas:
        raise RuntimeError("فشل توليد مواضيع جديدة من الـ LLM.")

    chosen = new_ideas[0]
    used.append(chosen)
    _save_used(used)
    return chosen
