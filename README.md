# 🎨 MangaThaiAI-Studio

ระบบแปลมังงะภาษาญี่ปุ่นเป็นภาษาไทยอัตโนมัติด้วย AI พร้อมการลบข้อความในบอลลูน (Inpainting) และการจัดเรียงตัวอักษรภาษาไทย (Typesetting)
ออกแบบสถาปัตยกรรมแบบ **Distributed Multi-Machine (LAN Orchestration)** เพื่อรองรับการทำงานร่วมกันระหว่างโน้ตบุ๊กและคอมพิวเตอร์ประมวลผลสูง (Gaming PC)

---

## 🏗 สถาปัตยกรรมระบบ (System Architecture)

```
+-------------------------------------------------------------+
|               Laptop (Control Center)                      |
|               IP: 192.168.1.104                            |
|  - Web UI Dashboard (FastAPI / HTML5)                       |
|  - Task Queue & LAN Orchestrator                            |
|  - Storage Manager (D:\code\MangaThaiAI-Studio)             |
|  - Thai Typesetting & Word Segmentation (PyThaiNLP)        |
+-------------------------------------------------------------+
                              |
                     LAN Wi-Fi / Ethernet
                    (HTTP REST / WebSocket)
                              |
                              v
+-------------------------------------------------------------+
|               Gaming PC (Remote AI Worker)                 |
|               IP: 192.168.1.x : 8888                       |
|  - Text Detection (YOLOv8-manga / CRAFT)                   |
|  - Japanese Manga OCR (Manga-OCR)                           |
|  - Balloon Inpainting / Clean Plate (LaMa)                 |
|  - Thai Translation Engine (LLM - Qwen2.5 / Typhoon)        |
|  - Accelerated by NVIDIA CUDA VRAM                         |
+-------------------------------------------------------------+
```

---

## 🚀 ขั้นตอนการติดตั้งและการใช้งาน (Setup & Usage)

### 1. บน Laptop (Control Center)
1. ติดตั้ง Dependencies สำหรับ Control Center (แบบเบา ไม่เปลือง VRAM):
   ```powershell
   cd D:\code\MangaThaiAI-Studio
   .\.venv\Scripts\pip install -r requirements-control-center.txt
   ```
2. รันระบบ Web Dashboard:
   ```powershell
   .\.venv\Scripts\python -m control_center.app
   ```
   เปิดเบราว์เซอร์เข้าที่: `http://localhost:8000`

---

### 2. บน Gaming PC (Remote Worker)
1. **ขั้นตอน Audit Hardware (รันครั้งแรก):**
   คัดลอกไฟล์ `scripts/audit_gaming_pc.ps1` ไปรันบน PowerShell ของ Gaming PC:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\audit_gaming_pc.ps1
   ```
   *นำ IP Address และขนาด VRAM ที่ได้มาบันทึกลงใน `configs/config.yaml` ของเครื่อง Laptop*

2. **ติดตั้ง Dependencies สำหรับ Worker:**
   ```powershell
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   pip install -r requirements-worker.txt
   ```

3. **เริ่มรัน Worker Service:**
   ```powershell
   python -m remote_worker.worker_service
   ```
   Worker จะเปิดรับคำสั่งผ่านพอร์ต `8888` ในวง LAN ทันที

---

## 📁 โครงสร้างโปรเจกต์ (Directory Structure)

```
MangaThaiAI-Studio/
├── configs/
│   └── config.yaml                 # การตั้งค่าระบบ Network และโมเดล
├── control_center/
│   ├── app.py                      # FastAPI Web Dashboard & Gateway
│   ├── orchestrator.py             # ตัวควบคุมงานและยิงคำสั่งผ่าน LAN
│   └── typesetting/
│       └── renderer.py             # เครื่องมือจัดวางตัวอักษรภาษาไทยลงในบอลลูน
├── remote_worker/
│   ├── worker_service.py           # FastAPI Worker สำหรับรันบน Gaming PC
│   └── modules/                    # โมดูล AI (OCR, Inpainting, Translation)
├── scripts/
│   ├── audit_gaming_pc.ps1         # สคริปต์ตรวจฮาร์ดแวร์ Gaming PC (PowerShell)
│   └── audit_gaming_pc.py          # สคริปต์ตรวจฮาร์ดแวร์ Gaming PC (Python)
├── data/
│   ├── inputs/                     # ไฟล์ภาพมังงะต้นฉบับ
│   ├── outputs/                    # ไฟล์ภาพมังงะที่แปลและ Typeset แล้ว
│   └── cache/                      # แคชสำหรับประมวลผลชั่วคราว
├── requirements-control-center.txt # Dependencies สำหรับโน้ตบุ๊ก
├── requirements-worker.txt         # Dependencies สำหรับ Gaming PC
└── README.md
```

---

## 🔒 นโยบายความปลอดภัยของระบบ
- **Drive Isolation:** โปรเจกต์ทั้งหมดถูกกักให้อยู่ใน `D:\code\MangaThaiAI-Studio` เท่านั้น ไม่แตะต้องโฟลเดอร์ BME หรือไฟล์ส่วนตัวอื่นๆ ในเครื่อง
- **Cache Redirection:** ตั้งค่าแคชโมเดลขนาดใหญ่ลง Drive D (`D:\hf_cache` และ `D:\torch_cache`) เพื่อป้องกัน Drive C เต็ม
- **Read-Only / No unauthorized network:** ไม่มีการเชื่อมต่อข้ามเครื่องอัตโนมัติหากผู้ใช้ยังไม่ได้เปิดและระบุ IP ของ Gaming PC
