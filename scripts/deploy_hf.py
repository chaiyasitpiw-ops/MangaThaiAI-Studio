"""
MangaThaiAI-Studio: Automated 24/7 Free Cloud Deployment to Hugging Face Spaces
Deploys the full Dockerized studio to Hugging Face Spaces for 100% free, always-on hosting.
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path("D:/code/MangaThaiAI-Studio")
TOKEN_FILE = BASE_DIR / "hf_token.txt"
CLOUD_URL_FILE = BASE_DIR / "CLOUD_URL.txt"
CLOUD_QR_FILE = BASE_DIR / "CLOUD_QR.png"


def main():
    print("\n" + "═" * 65)
    print("  🚀 MangaThaiAI-Studio: ระบบอัปโหลดขึ้น Cloud ฟรี 24 ชม.")
    print("     (Hugging Face Spaces - เปิดใช้งานได้ตลอดชีพ แม้ปิดคอม)")
    print("═" * 65)

    try:
        from huggingface_hub import HfApi
        import qrcode
    except ImportError:
        print("\n❌ กำลังติดตั้งโมดูลที่จำเป็น...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "huggingface_hub", "qrcode[pil]"])
        from huggingface_hub import HfApi
        import qrcode

    # 1. Read or prompt for Hugging Face Token
    token = None
    if TOKEN_FILE.exists():
        saved = TOKEN_FILE.read_text(encoding="utf-8").strip()
        if saved.startswith("hf_"):
            token = saved

    if not token:
        print("\n🔑 ขั้นตอนการเชื่อมต่อ Hugging Face (ทำเพียงครั้งแรก):")
        print("   1. สมัครสมาชิกฟรีที่: https://huggingface.co/join")
        print("   2. ไปที่หน้าสร้าง Token: https://huggingface.co/settings/tokens")
        print("   3. กด 'Create new token' -> เลือก Type: 'Write' -> Copy โค้ด (ขึ้นต้นด้วย hf_...)\n")
        
        entered = input("👉 วาง Hugging Face Token ของคุณที่นี่ (หรือกด Enter ถ้ามีไฟล์): ").strip()
        if not entered and TOKEN_FILE.exists():
            entered = TOKEN_FILE.read_text(encoding="utf-8").strip()
        
        if not entered.startswith("hf_"):
            print("❌ Token ไม่ถูกต้อง (ต้องขึ้นต้นด้วย hf_...) กรุณาลองใหม่อีกครั้ง")
            return
        
        token = entered
        TOKEN_FILE.write_text(token, encoding="utf-8")
        print("  ✓ บันทึก Token เรียบร้อยแล้ว")

    # 2. Authenticate
    api = HfApi(token=token)
    try:
        user_info = api.whoami()
        username = user_info["name"]
        print(f"\n  ✓ เข้าสู่ระบบสำเร็จในชื่อ: @{username}")
    except Exception as e:
        print(f"❌ Token ไม่ถูกต้อง หรือหมดอายุ: {e}")
        TOKEN_FILE.unlink(missing_ok=True)
        return

    # 3. Choose Space Name
    space_name = "mangathai-ai"
    repo_id = f"{username}/{space_name}"
    print(f"\n📦 ชื่อ Space บน Cloud: {repo_id}")

    # 4. Create Space (Docker SDK)
    print("  ⏳ กำลังเตรียมพื้นที่ Space บน Hugging Face...")
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            exist_ok=True,
            private=False
        )
        print("  ✓ สร้าง/เชื่อมต่อ Space สำเร็จ!")
    except Exception as e:
        print(f"❌ ไม่สามารถสร้าง Space ได้: {e}")
        return

    # 5. Upload files
    print("\n📤 กำลังอัปโหลดไฟล์โปรเจกต์ขึ้น Cloud (ใช้เวลาประมาณ 10-20 วินาที)...")
    ignore_patterns = [
        ".venv/**",
        "__pycache__/**",
        "*.pyc",
        ".git/**",
        "cloudflared.exe",
        "data/outputs/cache/*.json",
        "*.log",
        "test_*.png",
        "test_*.py",
        "debug_*.py",
        "hf_token.txt",
    ]

    try:
        api.upload_folder(
            folder_path=str(BASE_DIR),
            repo_id=repo_id,
            repo_type="space",
            ignore_patterns=ignore_patterns,
            commit_message="Deploy MangaThaiAI Studio 24/7"
        )
        print("  ✓ อัปโหลดไฟล์ทั้งหมดขึ้น Cloud เสร็จสมบูรณ์แล้ว!")
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาดในการอัปโหลด: {e}")
        return

    # 6. Generate Direct Cloud URL and QR Code
    direct_app_url = f"https://{username}-{space_name}.hf.space"
    space_manage_url = f"https://huggingface.co/spaces/{repo_id}"

    # Save URL
    with open(CLOUD_URL_FILE, "w", encoding="utf-8") as f:
        f.write(direct_app_url + "\n")

    # Generate QR Code
    qr = qrcode.QRCode(border=1)
    qr.add_data(direct_app_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(CLOUD_QR_FILE))

    print("\n" + "═" * 65)
    print("  🎉 ติดตั้งบน Cloud สำเร็จ 100%! ระบบกำลัง Build คอนเทนเนอร์")
    print("═" * 65)
    print(f"\n  🌐 URL สำหรับ iPhone & iPad (เปิดใช้งานได้ 24 ชม. ตลอดชีพ):")
    print(f"     👉 {direct_app_url}")
    print(f"\n  📊 หน้าแดชบอร์ดจัดการ Space:")
    print(f"     👉 {space_manage_url}\n")
    print("  📷 สแกน QR Code นี้เพื่อเปิดบน iPhone / iPad Safari ทันที:\n")

    qr.print_ascii(invert=True)

    print("\n" + "─" * 65)
    print("  💡 หมายเหตุการรันครั้งแรก:")
    print("     - Hugging Face จะใช้เวลาสร้าง Container ประมาณ 1-2 นาที")
    print("     - หลังจากนั้นจะออนไลน์ 24 ชั่วโมง ฟรีตลอดชีพ ไม่ต้องเปิดคอมทิ้งไว้เลย!")
    print("     - บน iPhone/iPad: เปิด Safari -> แชร์ -> 'Add to Home Screen'")
    print("─" * 65 + "\n")


if __name__ == "__main__":
    main()
