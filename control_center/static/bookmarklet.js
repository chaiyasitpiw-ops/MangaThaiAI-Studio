// =====================================================================
// MangaThaiAI-Studio: In-Browser Live Manga Translator (Mobile & Desktop Bookmarklet)
// Connects to Cloud 24/7 AI (Render: https://mangathaiai-studio.onrender.com)
// Supports: 18+ Adult Localizer, Korean, Russian, English, Chinese, Japanese
// =====================================================================

(function() {
    if (window.__mangaThaiLoaded) {
        const existing = document.getElementById("mangathai-hud");
        if (existing) {
            existing.style.display = existing.style.display === "none" ? "block" : "none";
            return;
        }
    }
    window.__mangaThaiLoaded = true;

    // Determine Cloud API origin
    const API_BASE = window.__MANGATHAI_API || (function() {
        const scripts = document.getElementsByTagName('script');
        for (let i = scripts.length - 1; i >= 0; i--) {
            if (scripts[i].src && scripts[i].src.includes('bookmarklet.js')) {
                try { return new URL(scripts[i].src).origin; } catch(e) {}
            }
        }
        if (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") {
            return "http://localhost:8000";
        }
        return "https://mangathaiai-studio.onrender.com";
    })();

    // 1. Create floating mobile-friendly HUD Toolbar
    const hud = document.createElement("div");
    hud.id = "mangathai-hud";
    hud.style.cssText = `
        position: fixed;
        bottom: 16px;
        right: 16px;
        z-index: 2147483647;
        background: rgba(15, 23, 42, 0.96);
        color: #f8fafc;
        border: 2px solid #8b5cf6;
        border-radius: 16px;
        padding: 14px 16px;
        box-shadow: 0 12px 35px rgba(0, 0, 0, 0.85);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 13px;
        width: calc(100vw - 32px);
        max-width: 340px;
        backdrop-filter: blur(12px);
        box-sizing: border-box;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    `;

    hud.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:16px;">🎨</span>
                <b style="color:#c4b5fd; font-size:14px;">MangaThaiAI Cloud 24H</b>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span id="mangathai-min" style="cursor:pointer; color:#94a3b8; font-size:16px; padding:2px 6px;">─</span>
                <span id="mangathai-close" style="cursor:pointer; color:#94a3b8; font-size:18px; font-weight:bold; padding:2px 6px;">&times;</span>
            </div>
        </div>

        <div id="mangathai-body">
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; margin-bottom:10px;">
                <div>
                    <label style="font-size:10px; color:#94a3b8; display:block; margin-bottom:2px;">🌐 ภาษาต้นฉบับ:</label>
                    <select id="mangathai-lang" style="width:100%; background:#1e293b; color:#f8fafc; border:1px solid #475569; border-radius:6px; padding:4px 6px; font-size:11px; outline:none;">
                        <option value="ko" selected>🇰🇷 เกาหลี</option>
                        <option value="ru">🇷🇺 รัสเซีย</option>
                        <option value="en">🇺🇸 อังกฤษ</option>
                        <option value="cn">🇨🇳 จีน</option>
                        <option value="ja">🇯🇵 ญี่ปุ่น</option>
                        <option value="auto">🌐 อัตโนมัติ</option>
                    </select>
                </div>
                <div>
                    <label style="font-size:10px; color:#94a3b8; display:block; margin-bottom:2px;">🎭 โทนสำนวน:</label>
                    <select id="mangathai-tone" style="width:100%; background:#1e293b; color:#f8fafc; border:1px solid #475569; border-radius:6px; padding:4px 6px; font-size:11px; outline:none;">
                        <option value="adult_18" selected>🔞 มังงะ 18+ (เสียว, ถึงอารมณ์)</option>
                        <option value="shonen">⚔️ โชเน็น (แก, ข้า, ลุย)</option>
                        <option value="casual">💬 เป็นกันเอง (นาย, เรา)</option>
                        <option value="standard">🌸 สุภาพ / ทั่วไป</option>
                    </select>
                </div>
            </div>

            <div style="display:flex; flex-direction:column; gap:6px;">
                <button id="mangathai-translate-all" style="background:linear-gradient(135deg, #10b981, #059669); color:white; border:none; padding:10px 12px; border-radius:8px; cursor:pointer; font-weight:700; font-size:12px; display:flex; align-items:center; justify-content:center; gap:6px; box-shadow:0 2px 8px rgba(16,185,129,0.3);">
                    ⚡ สแกนแปลทุกรูปในหน้านี้ทันที
                </button>
                <button id="mangathai-open-studio" style="background:linear-gradient(135deg, #6366f1, #8b5cf6); color:white; border:none; padding:8px 12px; border-radius:8px; cursor:pointer; font-weight:600; font-size:11px; display:flex; align-items:center; justify-content:center; gap:6px;">
                    📖 เปิดอ่านใน MangaThaiAI Studio (เต็มจอ)
                </button>
            </div>

            <div id="mangathai-status" style="margin-top:10px; font-size:11px; color:#a5b4fc; text-align:center; padding:4px; background:rgba(0,0,0,0.25); border-radius:6px;">
                พร้อมใช้งาน (เชื่อมต่อ Cloud 24H ฟรี)
            </div>
        </div>
    `;

    document.body.appendChild(hud);

    const statusEl = document.getElementById("mangathai-status");
    const bodyEl = document.getElementById("mangathai-body");
    const langSelect = document.getElementById("mangathai-lang");
    const toneSelect = document.getElementById("mangathai-tone");

    // Close / Minimize
    document.getElementById("mangathai-close").onclick = () => {
        hud.remove();
        window.__mangaThaiLoaded = false;
    };
    document.getElementById("mangathai-min").onclick = () => {
        bodyEl.style.display = bodyEl.style.display === "none" ? "block" : "none";
    };

    // Helper: Find all valid manga images on this page
    function getMangaImages() {
        const allImgs = Array.from(document.querySelectorAll("img"));
        const seen = new Set();
        const validImgs = [];

        for (const img of allImgs) {
            if (hud.contains(img)) continue;
            const src = (img.currentSrc || img.src || img.getAttribute("data-src") || img.getAttribute("data-lazy-src") || img.getAttribute("data-original") || "").trim();
            if (!src || seen.has(src)) continue;
            const lower = src.toLowerCase();
            if (lower.includes("logo") || lower.includes("icon") || lower.includes("avatar") || lower.includes("banner") || lower.includes("badge") || lower.includes("thumb") || lower.includes(".svg")) continue;

            const isChapterKw = lower.includes("chapter") || lower.includes("manga") || lower.includes("webtoon") || lower.includes("comic") || lower.includes("storage") || lower.includes("quicksharefiles") || lower.includes("cdn");
            const isLarge = (img.naturalWidth > 200 || img.width > 200 || img.naturalHeight > 300 || img.height > 300);

            if (isChapterKw || isLarge || allImgs.length < 150) {
                seen.add(src);
                validImgs.push({ element: img, url: src });
            }
        }
        return validImgs;
    }

    // Translate single image element
    async function translateImageElement(item) {
        const { element: img, url: src } = item;
        statusEl.innerHTML = `<span style="color:#fbbf24;">⏳ กำลังแปลภาพ...</span>`;
        if (img) {
            img.style.transition = "filter 0.3s ease";
            img.style.filter = "brightness(0.6)";
        }

        try {
            const resp = await fetch(`${API_BASE}/api/translate-image-url`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    image_url: src,
                    referer: window.location.href,
                    tone: toneSelect.value,
                    source_lang: langSelect.value
                })
            });

            if (!resp.ok) throw new Error("HTTP " + resp.status);
            const data = await resp.json();

            if (data.status === "success" && data.result_b64) {
                let finalSrc = data.result_b64;
                if (!finalSrc.startsWith("data:")) {
                    finalSrc = (finalSrc.startsWith("/9j/") ? "data:image/jpeg;base64," : "data:image/png;base64,") + finalSrc;
                }
                if (img) {
                    img.src = finalSrc;
                    img.removeAttribute("srcset");
                    img.style.filter = "none";
                }
                return true;
            } else {
                throw new Error(data.error || "แปลไม่สำเร็จ");
            }
        } catch (e) {
            if (img) img.style.filter = "none";
            console.warn("Translate failed for:", src, e);
            return false;
        }
    }

    // ⚡ Translate all images on page
    document.getElementById("mangathai-translate-all").onclick = async () => {
        const items = getMangaImages();
        if (!items.length) {
            statusEl.innerHTML = `<span style="color:#f87171;">⚠️ ไม่พบรูปภาพมังงะในหน้านี้ (ลองเลื่อนจอลงมาเล็กน้อย)</span>`;
            return;
        }

        const btn = document.getElementById("mangathai-translate-all");
        btn.disabled = true;
        btn.style.opacity = "0.7";

        let successCount = 0;
        for (let i = 0; i < items.length; i++) {
            statusEl.innerHTML = `<span style="color:#fbbf24;">กำลังแปลหน้า ${i + 1}/${items.length}...</span>`;
            const ok = await translateImageElement(items[i]);
            if (ok) successCount++;
        }

        btn.disabled = false;
        btn.style.opacity = "1";
        statusEl.innerHTML = `<span style="color:#34d399;">✓ แปลเสร็จสิ้น ${successCount}/${items.length} หน้า!</span>`;
    };

    // 📖 Open in MangaThaiAI Studio (passes extracted image URLs)
    document.getElementById("mangathai-open-studio").onclick = () => {
        const items = getMangaImages();
        if (!items.length) {
            alert("ไม่พบรูปภาพในหน้านี้ กรุณาลองใหม่อีกครั้ง");
            return;
        }
        const imgUrls = items.map(x => x.url);
        const payload = {
            title: document.title || "ตอนมังงะแปลไทย",
            source_url: window.location.href,
            images: imgUrls,
            tone: toneSelect.value,
            source_lang: langSelect.value
        };

        // Open Studio and transfer via postMessage or window.open
        const studioWin = window.open(`${API_BASE}/`, "_blank");
        if (studioWin) {
            const sendTimer = setInterval(() => {
                studioWin.postMessage({ type: "MANGATHAI_LOAD_IMAGES", data: payload }, "*");
            }, 800);
            setTimeout(() => clearInterval(sendTimer), 5000);
        }
    };
})();
