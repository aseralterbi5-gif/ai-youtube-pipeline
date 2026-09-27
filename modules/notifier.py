"""
إشعار اختياري عبر تيليجرام عند نجاح أو فشل التشغيل التلقائي،
حتى تعرف نتيجة العملية دون الحاجة لفتح أي جهاز أو متابعة يدوية.
"""
import os
import requests


def notify(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[تنبيه] لم يتم إعداد تيليجرام - تخطي الإشعار.")
        print(message)
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": message},
            timeout=15,
        )
    except Exception as e:
        print(f"[تحذير] فشل إرسال إشعار تيليجرام: {e}")
