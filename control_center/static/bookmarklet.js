// =====================================================================
// MangaThaiAI-Studio: In-Browser Live Manga Translator (Bookmarklet Script)
// Connects to local Control Center at http://localhost:8000
// =====================================================================

(function() {
    if (window.__mangaThaiLoaded) {
        alert("MangaThaiAI Live Translator is already active on this page!");
        return;
    }
    window.__mangaThaiLoaded = true;

    // Determine API origin dynamically (works on localhost, LAN IP, or Cloudflare Tunnel on iPhone/iPad)
    const API_BASE = window.__MANGATHAI_API || (function() {
        const scripts = document.getElementsByTagName('script');
        for (let i = scripts.length - 1; i >= 0; i--) {
            if (scripts[i].src && scripts[i].src.includes('bookmarklet.js')) {
                try { return new URL(scripts[i].src).origin; } catch(e) {}
            }
        }
        return "http://localhost:8000";
    })();

    // 1. Create floating HUD Toolbar
    const hud = document.createElement("div");
    hud.id = "mangathai-hud";
    hud.style.cssText = `
        position: fixed;
        bottom: 24px;
        right: 24px;
        z-index: 999999;
        background: #0f172a;
        color: #f8fafc;
        border: 2px solid #6366f1;
        border-radius: 12px;
        padding: 14px 18px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.7);
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 13px;
        max-width: 320px;
        transition: all 0.3s ease;
    `;

    hud.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <b style="color:#a5b4fc; font-size:14px;">🎨 MangaThaiAI Live</b>
            <span id="mangathai-close" style="cursor:pointer; font-weight:bold; color:#94a3b8; font-size:16px;">&times;</span>
        </div>
        <p style="margin:0 0 12px; color:#cbd5e1; font-size:12px;">คลิกที่รูปภาพมังงะในหน้าเว็บนี้เพื่อแปลเป็นภาษาไทยทันที!</p>
        <div style="display:flex; flex-direction:column; gap:8px;">
            <button id="mangathai-mode-click" style="background:#4f46e5; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-weight:600; text-align:left;">
                👆 โหมดคลิกแปลรูปภาพ (Active)
            </button>
            <button id="mangathai-translate-all" style="background:#10b981; color:white; border:none; padding:8px 12px; border-radius:6px; cursor:pointer; font-weight:600; text-align:left;">
                ⚡ สแกนแปลทุกรูปในหน้านี้
            </button>
        </div>
        <div id="mangathai-status" style="margin-top:10px; font-size:11px; color:#94a3b8;">พร้อมรับคำสั่ง (Connected to Local AI)</div>
    `;

    document.body.appendChild(hud);

    const statusEl = document.getElementById("mangathai-status");

    // Close HUD
    document.getElementById("mangathai-close").onclick = () => {
        hud.remove();
        window.__mangaThaiLoaded = false;
        document.body.style.cursor = "default";
    };

    // Mode: Click image to translate
    let clickModeActive = true;
    document.body.style.cursor = "crosshair";

    async function translateImageElement(img) {
        const src = img.currentSrc || img.src;
        if (!src) return;

        statusEl.innerHTML = `<span style="color:#fbbf24;">⏳ กำลังแปลรูปภาพ...</span>`;
        img.style.opacity = "0.5";
        img.style.filter = "grayscale(50%)";

        try {
            const resp = await fetch(`${API_BASE}/api/translate-image-url`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ image_url: src, referer: window.location.href })
            });

            if (!resp.ok) throw new Error("HTTP error " + resp.status);
            const data = await resp.json();

            if (data.status === "success" && data.result_b64) {
                img.src = "data:image/png;base64," + data.result_b64;
                img.style.opacity = "1";
                img.style.filter = "none";
                statusEl.innerHTML = `<span style="color:#34d399;">✓ แปลรูปภาพสำเร็จ! (${data.bubbles_count} บอลลูน)</span>`;
            } else {
                throw new Error(data.error || "Translation failed");
            }
        } catch (e) {
            img.style.opacity = "1";
            img.style.filter = "none";
            statusEl.innerHTML = `<span style="color:#f87171;">✗ ข้อผิดพลาด: ${e.message}</span>`;
            console.error("MangaThaiAI error:", e);
        }
    }

    // Intercept clicks on images
    document.addEventListener("click", function(e) {
        if (!clickModeActive) return;
        if (hud.contains(e.target)) return;

        let target = e.target;
        if (target.tagName.toLowerCase() === "img") {
            e.preventDefault();
            e.stopPropagation();
            translateImageElement(target);
        }
    }, true);

    // Translate all images
    document.getElementById("mangathai-translate-all").onclick = async () => {
        const images = Array.from(document.querySelectorAll("img")).filter(img => {
            return img.width > 200 && img.height > 200 && !hud.contains(img);
        });

        if (!images.length) {
            statusEl.innerHTML = `<span style="color:#f87171;">ไม่พบรูปภาพมังงะขนาดใหญ่ในหน้านี้</span>`;
            return;
        }

        statusEl.innerHTML = `<span style="color:#fbbf24;">กำลังแปลทั้งหมด ${images.length} รูป...</span>`;
        for (let i = 0; i < images.length; i++) {
            statusEl.innerHTML = `<span style="color:#fbbf24;">กำลังแปลหน้า ${i + 1}/${images.length}...</span>`;
            await translateImageElement(images[i]);
        }
        statusEl.innerHTML = `<span style="color:#34d399;">✓ แปลครบทั้ง ${images.length} รูปเรียบร้อย!</span>`;
    };
})();
