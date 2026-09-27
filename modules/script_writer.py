"""
يولّد سكربت الفيديو الكامل ثم يقسّمه إلى مشاهد (Scenes)،
كل مشهد يحتوي: نص الراوي (لسطر الصوت) + وصف بصري (لتوليد الصورة).

النمط: Research/Idea -> Script -> Scene breakdown -> (يُستخدم لاحقًا لـ Images/TTS)
"""
import json
import os
import re


class LLMClient:
    """طبقة تجريدية بسيطة فوق Anthropic أو OpenAI حتى يسهل التبديل بينهما."""

    def __init__(self, provider: str = "anthropic"):
        self.provider = provider
        if provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            self.model = "claude-sonnet-4-6"
        elif provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
            self.model = "gpt-4.1"
        else:
            raise ValueError(f"مزوّد LLM غير مدعوم: {provider}")

    def generate_text(self, prompt: str, max_tokens: int = 4000) -> str:
        if self.provider == "anthropic":
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return "".join(block.text for block in resp.content if block.type == "text")
        else:
            resp = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.choices[0].message.content


SCRIPT_PROMPT_TEMPLATE = """\
اكتب سكربت راوٍ (Voice-over Narration Script) لفيديو يوتيوب وثائقي تاريخي بعنوان:
"{topic}"

المتطلبات:
- اللغة: {language}
- الطول: يكفي لفيديو مدته تقريبًا {minutes} دقيقة (بمعدل ~140 كلمة/دقيقة تقريبًا).
- أسلوب سردي جذاب (Documentary storytelling)، جمل قصيرة وواضحة تصلح للقراءة الصوتية.
- اعتمد على معلومات تاريخية عامة معروفة، وتجنب أي ادّعاءات غير مؤكدة أو مختلقة.
- لا تخترع أسماء أو تواريخ أو إحصائيات دقيقة غير موثوقة؛ عند عدم اليقين استخدم صياغة عامة.
- قسّم النص إلى مشاهد (Scenes) مرقّمة، كل مشهد فقرة واحدة (3-6 جمل).

أخرج النتيجة بصيغة JSON فقط بدون أي نص إضافي قبله أو بعده، بالشكل التالي:
{{
  "title": "...",
  "scenes": [
    {{
      "scene_number": 1,
      "narration": "نص الراوي لهذا المشهد",
      "visual_description": "وصف بصري تفصيلي بالإنجليزية يصلح كـ prompt لتوليد صورة تمثل هذا المشهد، بدون نص مكتوب داخل الصورة"
    }}
  ]
}}
"""


def generate_script(llm: LLMClient, topic: str, config: dict) -> dict:
    prompt = SCRIPT_PROMPT_TEMPLATE.format(
        topic=topic,
        language=config["channel"]["language"],
        minutes=config["channel"]["video_length_minutes"],
    )
    raw = llm.generate_text(prompt, max_tokens=6000)

    # تنظيف احتياطي في حال أضاف النموذج ```json ... ``` حول الناتج
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
    data = json.loads(cleaned)

    if "scenes" not in data or not data["scenes"]:
        raise ValueError("فشل توليد المشاهد: الناتج لا يحتوي على scenes صالحة.")

    return data
