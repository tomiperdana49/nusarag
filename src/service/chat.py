import datetime, requests, os
from flask import jsonify
from dotenv import load_dotenv
load_dotenv()
GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_KEY")

def notification(respon, noHandphone, question):
    today = datetime.date.today().strftime("%Y-%m-%d")
    if respon == "Not Found":
        text = (
            f"*---- RAG Notifikasi ----*\n\n"
            f"*⏰ Tanggal:* {today}\n\n"
            f"*📞 User:* https://wa.me/{noHandphone}\n\n"
            f"*❓ Pertanyaan User:* {question}\n\n"

            f"Pertanyaan ini tidak dapat di respon oleh AI."
        )
    else:
        text = (
            f"*---- RAG Notifikasi ----*\n\n"
            f"*⏰ Tanggal:* {today}\n\n"
            f"*📞 User:* https://wa.me/{noHandphone}\n\n"
            f"*❓ Pertanyaan User:* {question}\n\n"
        )
    
    payload = {
        "text": text
    }

    resp = requests.post(GOOGLE_CHAT_WEBHOOK_URL, json=payload)

    return jsonify({
        "ok": resp.ok,
        "status_code": resp.status_code,
        "chat_response": resp.text
    }), 200