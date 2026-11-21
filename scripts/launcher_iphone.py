"""
MangaThaiAI-Studio: 24/7 Free Launcher for iPhone & iPad
Starts local server + Cloudflare Tunnel + Generates instant QR code for iPhone Safari.
"""

import os
import re
import sys
import time
import subprocess
from pathlib import Path
import qrcode

BASE_DIR = Path("D:/code/MangaThaiAI-Studio")
VENV_PYTHON = BASE_DIR / ".venv/Scripts/python.exe"
CLOUDFLARED = BASE_DIR / "cloudflared.exe"
URL_FILE = BASE_DIR / "IPHONE_URL.txt"
QR_IMG = BASE_DIR / "IPHONE_QR.png"


def is_server_running():
    import urllib.request
    try:
        with urllib.request.urlopen("http://localhost:8000/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def start_server():
    if is_server_running():
        print("  ✓ Local server already running on port 8000")
        return None
    print("  🚀 Starting MangaThaiAI Server on http://0.0.0.0:8000...")
    cmd = [str(VENV_PYTHON), "-m", "uvicorn", "control_center.app:app", "--host", "0.0.0.0", "--port", "8000"]
    proc = subprocess.Popen(cmd, cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for ready
    for _ in range(15):
        if is_server_running():
            print("  ✓ Server is online and ready!")
            return proc
        time.sleep(0.8)
    return proc


def print_qr_and_info(tunnel_url: str):
    # Save URL to file
    with open(URL_FILE, "w", encoding="utf-8") as f:
        f.write(tunnel_url + "\n")

    # Generate QR Code
    qr = qrcode.QRCode(border=1)
    qr.add_data(tunnel_url)
    qr.make(fit=True)

    # Save PNG QR image
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(str(QR_IMG))

    print("\n" + "═" * 60)
    print("  ⚡ MangaThaiAI-Studio: ลิงก์สำหรับ iPhone & iPad พร้อมใช้งาน! ⚡")
    print("═" * 60)
    print(f"\n  🌐 URL สำหรับเปิดบน iPhone / iPad:\n     👉 {tunnel_url}\n")
    print("  📷 สแกน QR Code นี้ด้วยกล้อง iPhone / iPad เพื่อเปิดทันที:\n")

    # Print ASCII QR Code in terminal
    qr.print_ascii(invert=True)

    print("\n" + "─" * 60)
    print("  💡 วิธีติดตั้งบนหน้าจอ iPhone / iPad (PWA ใช้งานเต็มจอ 24 ชม):")
    print("     1. สแกน QR Code หรือเปิดลิงก์ข้างต้นใน Safari")
    print("     2. กดปุ่มแชร์ (ไอคอนกล่องลูกศรชี้ขึ้น 📤)")
    print("     3. เลือก 'Add to Home Screen' (เพิ่มไปยังหน้าจอโฮม)")
    print("     4. คุณจะได้แอป MangaThaiAI บนหน้าจอหลัก ใช้งานได้ฟรี 24 ชม.!")
    print("─" * 60)
    print(f"  📁 บันทึกลิงก์ไว้ที่: {URL_FILE}")
    print(f"  🖼️ รูปภาพ QR Code: {QR_IMG}\n")


def main():
    print("\n[1/3] ตรวจสอบเซิร์ฟเวอร์...")
    server_proc = start_server()

    print("\n[2/3] ตรวจสอบ Cloudflare Tunnel (ฟรี 100%)...")
    if not CLOUDFLARED.exists():
        print("  📥 กำลังดาวน์โหลด cloudflared.exe...")
        import urllib.request
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        urllib.request.urlretrieve(url, str(CLOUDFLARED))
        print("  ✓ ดาวน์โหลดสำเร็จ!")

    print("\n[3/3] กำลังสร้าง Public HTTPS Tunnel สำหรับ iPhone/iPad...")
    cmd = [str(CLOUDFLARED), "tunnel", "--url", "http://localhost:8000", "--no-autoupdate"]
    tunnel_proc = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    for line in tunnel_proc.stdout:
        m = url_pattern.search(line)
        if m:
            tunnel_url = m.group(0)
            print_qr_and_info(tunnel_url)
            break

    try:
        tunnel_proc.wait()
    except KeyboardInterrupt:
        print("\nกำลังปิดระบบ...")
        tunnel_proc.terminate()
        if server_proc:
            server_proc.terminate()


if __name__ == "__main__":
    main()
