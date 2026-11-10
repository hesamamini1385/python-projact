import asyncio
import edge_tts
import os
import re

# ============ تنظیمات ============
OUTPUT = "output_long.mp3"
VOICE = "en-US-JennyNeural"
RATE = "-15%"          # سرعت: "-20%" آرام‌تر، "+10%" تندتر، "+0%" عادی
MAX_RETRIES = 3
RETRY_DELAY = 2


# ============ گرفتن متن طولانی از کاربر ============
def get_text():
    print("📝 متن انگلیسی را وارد کن.")
    print("   (چند خط می‌توانی بچسبانی. برای پایان، یک خط خالی بزن و Enter.)\n")
    lines = []
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "" and lines:
            break
        lines.append(line)
    return "\n".join(lines).strip()


# ============ تقسیم متن ============
def split_text(text, max_chars=800):
    pattern = r'(?<=[.!?。！？])\s+'
    sentences = re.split(pattern, text)
    chunks, current = [], ""
    for s in sentences:
        if not s.strip():
            continue
        if len(s) > max_chars:
            if current:
                chunks.append(current); current = ""
            for i in range(0, len(s), max_chars):
                chunks.append(s[i:i+max_chars])
            continue
        if len(current) + len(s) + 1 > max_chars:
            chunks.append(current); current = s
        else:
            current = (current + " " + s).strip() if current else s
    if current:
        chunks.append(current)
    return [c for c in chunks if c.strip()]


# ============ ساخت صدا با تلاش مجدد ============
async def synthesize_chunk(chunk, voice, rate, retries=MAX_RETRIES):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            communicate = edge_tts.Communicate(text=chunk, voice=voice, rate=rate)
            audio = b""
            async for data in communicate.stream():
                if data["type"] == "audio":
                    audio += data["data"]
            if not audio:
                raise RuntimeError("پاسخ خالی از سرور")
            return audio
        except Exception as e:
            last_error = e
            print(f"      ⚠️ تلاش {attempt}/{retries} ناموفق: {type(e).__name__}")
            if attempt < retries:
                await asyncio.sleep(RETRY_DELAY)
    raise RuntimeError(f"پس از {retries} تلاش شکست خورد: {last_error}")


# ============ اجرای اصلی ============
async def main():
    text = get_text()
    if not text:
        print("❌ متنی وارد نشد.")
        return

    print(f"\n📄 متن دریافت شد ({len(text)} کاراکتر)")
    chunks = split_text(text)
    print(f"✂️ به {len(chunks)} تکه تقسیم شد.\n")

    all_audio = []
    for i, chunk in enumerate(chunks, 1):
        print(f"   🎙️ تکه {i}/{len(chunks)} ({len(chunk)} کاراکتر)...")
        try:
            audio = await synthesize_chunk(chunk, VOICE, RATE)
            all_audio.append(audio)
        except Exception as e:
            print(f"      ❌ تکه {i} رد شد: {e}")

    if not all_audio:
        print("\n❌ هیچ تکه‌ای ساخته نشد. VPN را روشن/خاموش کن و دوباره امتحان کن.")
        return

    with open(OUTPUT, "wb") as f:
        for a in all_audio:
            f.write(a)

    print(f"\n✅ فایل ذخیره شد: {os.path.abspath(OUTPUT)}")
    print(f"   ({len(all_audio)} از {len(chunks)} تکه موفق)")


await main()
