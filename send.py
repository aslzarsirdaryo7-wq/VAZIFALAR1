"""
GitHub Actions orqali ishlaydigan vazifa yuboruvchi.
Har kuni 20:00 (Toshkent) da GitHub shu faylni ishga tushiradi va
har bir ishchiga ERTANGI vazifalarini Telegramdan yuboradi.

Navbat sanaga qarab hisoblanadi (hech narsa saqlash shart emas):
har ish kuni vazifalar bitta keyingi ishchiga suriladi, shuning uchun
hech kimga ikki kun ketma-ket bir xil vazifa tushmaydi.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone

# ================== SOZLAMALAR ==================
WORKERS = [
    {"name": "Dinara",  "id": 988638675},
    {"name": "Dilnora", "id": 7554393626},
    {"name": "Shahlo",  "id": 6780892136},
    {"name": "Nozima",  "id": 8471109451},
]

TASKS = [
    "Vitrina tozalash",
    "Tovar yoyish",
    "Instagramni yuritish",
    "Tovar sortirovka",
    "Telegram bilan shug'ullanish",
    "Flayer tarqatish",
    "Kelgan odamga botni/dasturni tushuntirish va ulash",
    "Tozalikka navbatchilik",
]

WORK_DAYS = {0, 1, 2, 3, 4, 5}   # 0=Dushanba ... 6=Yakshanba (yakshanba dam)
START = date(2026, 11, 27)       # navbat hisobi boshlanadigan kun
# ================================================

TOKEN = os.environ.get("BOT_TOKEN", "").strip()
ADMIN_ID = os.environ.get("ADMIN_ID", "").strip() or "7474029233"  # rahbar
TASHKENT = timezone(timedelta(hours=5))
WEEKDAYS = ["Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba"]


def work_day_number(d: date) -> int:
    """START dan d gacha nechta ish kuni o'tganini sanaydi."""
    n, cur, step = 0, START, (1 if d >= START else -1)
    while cur != d:
        if cur.weekday() in WORK_DAYS:
            n += step
        cur += timedelta(days=step)
    return n


def assign(day: int) -> dict:
    result = {w["name"]: [] for w in WORKERS}
    for i, task in enumerate(TASKS):
        result[WORKERS[(i + day) % len(WORKERS)]["name"]].append(task)
    return result


def check_token():
    """Token to'g'riligini tekshiradi va bot nomini chiqaradi."""
    if not TOKEN:
        print("❌ XATO: BOT_TOKEN topilmadi! Settings → Secrets and variables → Actions ga "
              "BOT_TOKEN nomi bilan token qo'shing.")
        sys.exit(1)
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{TOKEN}/getMe", timeout=20) as r:
            me = json.load(r)["result"]
        print(f"✅ Token to'g'ri. Bot: @{me['username']}  — hamma shu botga /start bosishi kerak!")
    except Exception as e:
        print(f"❌ XATO: token noto'g'ri ({e}). BotFather'dan tokenni qayta nusxalab, secret'ni yangilang.")
        sys.exit(1)


def send(chat_id, text) -> bool:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=20)
        return True
    except urllib.error.HTTPError as e:
        reason = e.read().decode(errors="ignore")
        print(f"❌ Yuborilmadi ({chat_id}): {e.code} {reason}")
        return False
    except Exception as e:
        print(f"❌ Yuborilmadi ({chat_id}): {e}")
        return False


def main():
    check_token()
    now = datetime.now(TASHKENT)
    manual = os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch"
    tomorrow = now.date() + timedelta(days=1)

    if not manual and tomorrow.weekday() not in WORK_DAYS:
        print("Ertaga dam olish kuni — yuborilmaydi.")
        return
    while tomorrow.weekday() not in WORK_DAYS:
        tomorrow += timedelta(days=1)

    plan = assign(work_day_number(tomorrow))
    label = f"{tomorrow.strftime('%d.%m.%Y')}, {WEEKDAYS[tomorrow.weekday()]}"

    failed = []
    for w in WORKERS:
        body = "\n".join(f"{i}. {t}" for i, t in enumerate(plan[w["name"]], 1)) or "Vazifa yo'q 🙂"
        text = (f"Assalomu alaykum, {w['name']}! 🌙\n\n"
                f"📋 Ertangi vazifalaringiz ({label}):\n\n{body}\n\n"
                f"Yaxshi dam oling, ertaga omad! 💪")
        if not send(w["id"], text):
            failed.append(w["name"])

    summary = [f"✅ {label} vazifalari yuborildi:"]
    for w in WORKERS:
        summary.append(f"\n👤 {w['name']}:")
        summary += [f"   • {t}" for t in plan[w["name"]]]
    if failed:
        summary.append("\n⚠️ Yetib bormadi: " + ", ".join(failed) + "\n(botga /start bosmagan bo'lishi mumkin)")
    print("\n".join(summary))
    admin_ok = send(ADMIN_ID, "\n".join(summary)) if ADMIN_ID else True
    if not admin_ok:
        print("❌ Adminga (sizga) yuborilmadi — botga /start bosing.")
    if failed or not admin_ok:
        print("\n⚠️ Ba'zi xabarlar yetib bormadi. Sabab: o'sha odam yuqoridagi botga /start bosmagan "
              "('chat not found' / 'Forbidden') yoki ID xato.")
        sys.exit(1)


if __name__ == "__main__":
    main()
