# نظام إنتاج فيديوهات يوتيوب آليًا بالذكاء الاصطناعي

نظام يعمل بالكامل في السحابة عبر **GitHub Actions** — يعني يعمل حسب جدول زمني
حتى لو كان جهازك مغلقًا تمامًا، لأن التنفيذ يتم على خوادم GitHub وليس جهازك.

**السلسلة الكاملة تلقائيًا:**
اختيار موضوع → سكربت بالذكاء الاصطناعي → تقسيم مشاهد → توليد صور → توليد صوت (TTS) →
مونتاج فيديو (Ken Burns) → صورة مصغرة → رفع مباشر إلى يوتيوب → إشعار تيليجرام بالنتيجة.

---

## 0) لماذا يعمل "حتى لو الجهاز مغلق"؟

كل شيء يُنفَّذ داخل `.github/workflows/auto_pipeline.yml` على خوادم GitHub وفق
جدول Cron. أنت فقط ترفع هذا المشروع مرة واحدة إلى GitHub وتضبط المفاتيح
السرية (Secrets)، وبعدها GitHub نفسه يشغّل السكربت في موعده تلقائيًا للأبد.
جهازك لا علاقة له بالتنفيذ إطلاقًا بعد هذه الخطوة.

بديل آخر (إذا احتجت موارد/وقت تنفيذ أكبر من حدود GitHub Actions المجانية):
نفس المشروع + `cron` عادي على خادم VPS رخيص (Hetzner / DigitalOcean) يعمل 24/7 —
اطلب مني إعداد نسخة VPS إذا احتجتها لاحقًا.

---

## 1) التثبيت المحلي (اختياري، للتجربة قبل الرفع لـ GitHub)

```bash
pip install -r requirements.txt
sudo apt install ffmpeg   # أو المكافئ حسب نظامك
python main.py
```

---

## 2) رفع المشروع إلى GitHub

```bash
cd ai_youtube_pipeline
git init
git add .
git commit -m "init: automated youtube pipeline"
git branch -M main
git remote add origin https://github.com/<username>/<repo>.git
git push -u origin main
```

---

## 3) الحصول على مفاتيح API المطلوبة

| المفتاح | من أين | إلزامي؟ |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com | نعم (لتوليد السكربت) |
| `OPENAI_API_KEY` | platform.openai.com | نعم (لتوليد الصور، ما لم تستخدم Stability) |
| `STABILITY_API_KEY` | platform.stability.ai | فقط إذا اخترت `image: stability` في config.yaml |
| `ELEVENLABS_API_KEY` | elevenlabs.io | فقط إذا اخترت `tts: elevenlabs` (الافتراضي `edge-tts` مجاني، لا يحتاج مفتاح) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | عبر @BotFather على تيليجرام | اختياري، للإشعارات فقط |
| `YOUTUBE_API_KEY` | Google Cloud Console → Credentials → "API key" (بسيط، بدون OAuth) | فقط إذا فعّلت `channel_analysis.enabled: true` |

> **جديد:** خطوة "تحليل قناة ناجحة" (الخطوة الأولى في الفيديو المرجعي) أصبحت
> مطبّقة الآن فعليًا. فعّلها في `config.yaml`:
> ```yaml
> channel_analysis:
>   enabled: true
>   reference_channel_id: "UCxxxxxxxxxxxxxxxxxxxx"
> ```
> النظام يجلب أحدث عناوين القناة المرجعية، يستخرج نمطها الناجح، ويقترح
> مواضيع جديدة بنفس النمط تلقائيًا قبل كل حلقة.

---

## 4) الخطوة الأهم: توليد YouTube Refresh Token (مرة واحدة فقط)

هذه الخطوة الوحيدة التي تحتاج تفاعلًا بشريًا (تسجيل دخول Google)، لكنها **تُنفَّذ
مرة واحدة فقط على جهازك**، والنتيجة (Refresh Token) تُستخدم بعدها إلى الأبد
آليًا بدون أي تدخل بشري لاحق:

1. اذهب إلى [Google Cloud Console](https://console.cloud.google.com/) → أنشئ مشروعًا جديدًا.
2. فعّل **YouTube Data API v3** من "APIs & Services > Library".
3. من "APIs & Services > Credentials" أنشئ **OAuth client ID** من نوع **Desktop app**.
   احفظ `Client ID` و `Client Secret`.
4. شغّل السكربت المساعد محليًا مرة واحدة فقط (على جهازك):

```bash
python get_refresh_token.py
```

أدخل `Client ID` و`Client Secret` عند الطلب. سيفتح متصفحًا لتسجيل الدخول بحساب
يوتيوب الخاص بالقناة والموافقة على صلاحية الرفع. سيطبع السكربت `YT_REFRESH_TOKEN`
مرة واحدة؛ احفظه كـ GitHub Actions secret ولا تضفه إلى ملفات المشروع أو Git.

---

## 5) إضافة كل المفاتيح كـ Secrets في GitHub

في صفحة المستودع على GitHub:
`Settings → Secrets and variables → Actions → New repository secret`

أضف كل هذه الأسماء بالقيم المطابقة:
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `YT_CLIENT_ID`, `YT_CLIENT_SECRET`,
`YT_REFRESH_TOKEN` (وأي مفاتيح اختيارية أخرى استخدمتها).

---

## 6) التفعيل

- الجدولة متوقفة مبدئيًا في `.github/workflows/auto_pipeline.yml` حتى تنتهي
  تجربة التشغيل اليدوي ومراجعة أول فيديو خاص. بعد الاطمئنان، أزل التعليق عن
  سطري `schedule` و`cron` هناك (`0 12 * * 1,4` = كل اثنين وخميس الساعة 12:00 UTC).
- لتجربة فورية بدون انتظار الجدول: من تبويب **Actions** في GitHub، افتح
  workflow باسم "Auto YouTube Pipeline" ثم اضغط **Run workflow**.
- أول مرة اترك `upload_privacy: private` في `config.yaml` وراجع الفيديو الناتج
  يدويًا في يوتيوب قبل تحويله لاحقًا إلى `public`.

---

## ⚠️ ملاحظات مهمة قبل تشغيله بشكل دائم

1. **السياسات:** يوتيوب صريح بخصوص المحتوى "المُعاد استخدامه بشكل آلي دون قيمة
   مضافة" (Reused/Repetitious content) — قد يُستبعد من الإعلانات أو يُخفَّض
   في التوصيات إذا لم يكن هناك تحرير/قيمة بشرية حقيقية. النظام هنا يبني فيديو
   كامل، لكن يُنصح بمراجعة كل حلقة يدويًا (خصوصًا دقة المعلومات التاريخية)
   قبل النشر العلني، على الأقل في البداية.
2. **دقة المعلومات:** الـ LLM قد يُخطئ في تفاصيل تاريخية. تم توجيهه في
   الـ prompt لتجنّب الاختلاق، لكن هذا لا يضمن 100%. راجع قبل النشر.
3. **حقوق الصور المولّدة:** بعض الأنماط أو الأوصاف قد تُنتج صورًا قريبة الشبه
   من أعمال محمية أو شخصيات حقيقية — تجنّب طلب صور لأشخاص معاصرين بالاسم.
4. **التكلفة:** كل حلقة تستهلك رصيدًا فعليًا من LLM + توليد الصور + (اختياريًا)
   TTS مدفوع. راقب الاستهلاك من لوحات كل مزوّد.
5. النجاح المالي المعروض في أي فيديو مرجعي (مشاهدات/أرباح) خاص بتلك القناة
   تحديدًا، ولا يضمن نفس النتائج لقناة جديدة — النجاح يعتمد أيضًا على جودة
   الموضوع والعنوان والـ Thumbnail والمنافسة، وليس فقط على الأتمتة.

---

## هيكل المشروع

```
ai_youtube_pipeline/
├── config.yaml                  # كل الإعدادات القابلة للتعديل
├── main.py                      # المنسّق الرئيسي (Orchestrator)
├── requirements.txt
├── modules/
│   ├── topic_picker.py          # اختيار الموضوع
│   ├── script_writer.py         # LLM: سكربت + تقسيم مشاهد
│   ├── image_generator.py       # توليد صور المشاهد
│   ├── tts_generator.py         # تحويل النص لصوت
│   ├── video_builder.py         # مونتاج ffmpeg + Ken Burns
│   ├── thumbnail_maker.py       # صورة مصغرة بعنوان بارز
│   ├── youtube_uploader.py      # رفع آلي بالكامل عبر Refresh Token
│   └── notifier.py              # إشعار تيليجرام اختياري
└── .github/workflows/
    └── auto_pipeline.yml        # الجدولة السحابية (تعمل بدون جهازك)
```
