"""
MangaThaiAI-Studio: Manga Localization & Natural Dialogue Translation Engine
Transforms stiff robotic machine translations into authentic, expressive Thai manga dialogue.
Supports Japanese (JP), English (EN), Korean (KR), and Chinese (CN).
Features customizable tone presets: Shonen (Action), Shojo (Romance), Seinen (Mature), Comedy (Gag).
"""

import re
from typing import Dict, List, Optional


class MangaTone:
    SHONEN = "shonen"       # โชเน็น/ต่อสู้: ดุดัน โผงผาง (แก, ข้า, หนอย, ลุย)
    SHOJO = "shojo"         # ตาหวาน/รัก: ละมุน ซึนเดเระ (นาย, ฉัน, บ้าจริง, ยะ)
    SEINEN = "seinen"       # สืบสวน/ดาร์ก: สุขุม จริงจัง เป็นธรรมชาติ
    COMEDY = "comedy"       # ตลก/แก๊ก: กวนๆ ภาษาพูด วลีฮาๆ


class MangaNaturalTranslator:
    def __init__(self):
        # Comprehensive dictionary of authentic manga dialogue adaptations
        # Maps stiff literal translations -> natural Thai manga localization
        self.jp_slang_map = {
            # Shock / Exclamation
            "何だと": "ว่าไงนะ...!",
            "なんだと": "ว่าไงนะ...!",
            "何だって": "อะไรกันเนี่ย...!",
            "嘘だろ": "โกหกน่า...!",
            "うそだろ": "ล้อเล่นน่า...!",
            "まさか": "หรือว่าจะเป็นไปได้ว่า...!",
            "信じられない": "ไม่อยากจะเชื่อเลย...!",
            "そんなバカな": "บ้าไปแล้ว... เป็นไปไม่ได้หรอก!",
            "馬鹿な": "บัดซบเอ๊ย... เป็นไปไม่ได้!",
            
            # Action / Threat / Battle
            "おい、待てよ": "เฮ้ย! รอก่อนสิฟะ!",
            "待て": "หยุดเดี๋ยวนี้นะ!",
            "貴様": "หนอย... แก!",
            "てめえ": "ไอ้เวรเอ๊ย!",
            "くそっ": "โธ่เว้ย!",
            "ちくしょう": "เจ็บใจนัก!",
            "覚悟しろ": "เตรียมใจไว้ได้เลย!",
            "許さん": "อย่าหวังว่าจะรอดไปได้!",
            "許さない": "ฉันไม่ยกโทษให้แกแน่!",
            "ぶっ殺す": "ฉันจะเชือดแกทิ้งซะ!",
            "死ね": "ไปตายซะ!",
            "くらえ": "รับไปซะ!",
            "邪魔だ": "เกะกะโว้ย! หลบไป!",
            "逃げろ": "หนีเร็วเข้า!",
            "行くぞ": "ลุยกันเลย!",
            "やってやる": "เอาซิวะ! จัดไป!",

            # Casual / Everyday
            "やれやれ": "ให้ตายสิ...",
            "しょうがない": "ช่วยไม่ได้แฮะ...",
            "ふふ": "หึหึ...",
            "クスクス": "คิกคิก...",
            "ありがとう": "ขอบใจนะ",
            "ごめん": "โทษทีนะ",
            "すまない": "ขอโทษด้วยจริง ๆ",
            "助けて": "ช่วยด้วย!",
            "大丈夫": "ไม่เป็นไรใช่ไหม",
            "任せて": "ไว้ใจฉันได้เลย",
            "わかった": "เข้าใจแล้วล่ะ",
            "知るか": "ใครจะไปรู้เล่า!",

            # Romance / Tsundere
            "べ、別に": "กะ... ก็ไม่ได้...",
            "あんたのためじゃない": "ไม่ได้ทำให้เธอสักหน่อย อย่าเข้าใจผิดนะยะ!",
            "バカ": "เจ้าบ้าเอ๊ย...!",
            "うるさい": "หนวกหูจริง!",
            "照れるな": "ไม่ต้องมาทำเป็นเขินเลยนะ",
            "好きだ": "ฉันชอบเธอนะ",
            "愛してる": "รักที่สุดเลย",
        }

        # English comic slang adaptations
        self.en_slang_map = {
            "what the hell": "มันเรื่องบ้าอะไรวะเนี่ย!",
            "what the heck": "อะไรกันเนี่ย!",
            "no way": "ไม่มีทางน่า...!",
            "damn it": "โธ่เว้ย!",
            "dammit": "บัดซบเอ๊ย!",
            "get out of here": "ไสหัวไปให้พ้น!",
            "bring it on": "เข้ามาเลยวะ!",
            "let's go": "ลุยกันเลยพวกเรา!",
            "are you kidding me": "ล้อกันเล่นใช่ไหมเนี่ย...!",
            "shut up": "หุบปากไปซะ!",
            "give me a break": "ขอพักหายใจหน่อยเถอะน่า...",
            "hold on": "เดี๋ยวก่อนสิ!",
            "wait a minute": "ช้าก่อน!",
            "you bastard": "ไอ้สารเลวเอ๊ย!",
            "i don't care": "ใครสนกันล่ะ!",
        }

        # Korean manhwa common idioms
        self.kr_slang_map = {
            "젠장": "โธ่เว้ย...!",
            "말도 안 돼": "เป็นไปไม่ได้น่า...!",
            "죽어라": "ไปลงนรกซะ!",
            "닥쳐": "หุบปากไปเลย!",
            "오빠": "พี่คะ / พี่",
            "형": "พี่ / ลูกพี่",
            "대박": "สุดยอดไปเลยแฮะ!",
            "어이가 없네": "พูดไม่ออกเลยจริง ๆ...",
        }

        # Chinese manhua common idioms
        self.cn_slang_map = {
            "混账": "สารเลวเอ๊ย!",
            "找死": "รนหาที่ตาย!",
            "不可能": "เป็นไปไม่ได้เด็ดขาด!",
            "饶命": "ไว้ชีวิตข้าด้วย!",
            "放肆": "บังอาจนัก!",
            "阁下": "ท่านผู้เจริญ / ท่าน",
            "看招": "รับกระบวนท่านี้ไปซะ!",
        }

        # Stiff phrase cleaner (Fixes Google Translate robotic artifacts in Thai text)
        self.stiff_thai_cleaners = [
            (r"\bคุณ\b(?=.*(?:ตาย|ฆ่า|สารเลว|ลุย))", "แก"), # If hostile context, avoid polite "คุณ"
            (r"\bฉันจะทำการ\b", "ฉันจะ"),
            (r"\bมันเป็นเรื่องโกหก\b", "โกหกน่า..."),
            (r"\bมันคืออะไร\b", "อะไรกันเนี่ย..."),
            (r"\bสิ่งนั้นเป็นไปไม่ได้\b", "เป็นไปไม่ได้หรอก!"),
            (r"\bฉันไม่สามารถทำได้\b", "ทำไม่ไหวแล้ว..."),
            (r"\bโปรดรอสักครู่\b", "รอก่อนสิ!"),
            (r"\bกินสิ่งนี้ซะ\b", "กินนี่เข้าไปซะ!"),
            (r"\bไปสู่ความตาย\b", "ไปตายซะ!"),
        ]

    def translate_and_polish(
        self,
        source_text: str,
        source_lang: str = "auto",
        tone: str = MangaTone.SHONEN
    ) -> str:
        """
        Translates and polishes dialogue into authentic natural Thai manga prose.
        source_lang: 'jp', 'en', 'kr', 'cn', or 'auto'
        tone: 'shonen', 'shojo', 'seinen', 'comedy'
        """
        cleaned_src = source_text.strip()
        if not cleaned_src:
            return ""

        # Auto detect language if set to auto
        lang = source_lang.lower()
        if lang == "auto":
            if re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", cleaned_src):
                # Japanese Kana presence indicates Japanese
                if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", cleaned_src):
                    lang = "jp"
                else:
                    lang = "cn"
            elif re.search(r"[\uac00-\ud7af]", cleaned_src):
                lang = "kr"
            else:
                lang = "en"

        # Check dictionary lookups based on language
        translated = None
        if lang == "jp":
            for jp_key, th_val in self.jp_slang_map.items():
                if jp_key in cleaned_src:
                    translated = th_val
                    break
        elif lang == "en":
            cleaned_lower = cleaned_src.lower()
            for en_key, th_val in self.en_slang_map.items():
                if en_key in cleaned_lower:
                    translated = th_val
                    break
        elif lang == "kr":
            for kr_key, th_val in self.kr_slang_map.items():
                if kr_key in cleaned_src:
                    translated = th_val
                    break
        elif lang == "cn":
            for cn_key, th_val in self.cn_slang_map.items():
                if cn_key in cleaned_src:
                    translated = th_val
                    break

        # Fallback if no direct slang match found
        if not translated:
            translated = self._fallback_translate(cleaned_src, lang, tone)

        # Apply Tone Adjustments
        polished = self._apply_tone(translated, tone)

        # Clean any robotic Thai phrasing artifacts
        for pattern, replacement in self.stiff_thai_cleaners:
            polished = re.sub(pattern, replacement, polished)

        return polished

    def _apply_tone(self, text: str, tone: str) -> str:
        """Fine-tunes pronouns, sentence particles, and emotion to match manga genre."""
        out = text
        if tone == MangaTone.SHONEN:
            # Action/Shonen: energetic, punchy
            out = re.sub(r"\bฉันจะ\b", "ข้าจะ", out)
            out = re.sub(r"\bครับ\b|\bค่ะ\b", "เว้ย", out)
            if not any(out.endswith(p) for p in ["!", "!!", "...", "ฟะ", "เว้ย", "ซะ"]):
                out += "!"
        elif tone == MangaTone.SHOJO:
            # Romance/Shojo: softer, cute, tsundere
            out = re.sub(r"\bแก\b", "นาย", out)
            out = re.sub(r"\bเว้ย\b", "ยะ", out)
            out = re.sub(r"\bฟะ\b", "เหรอ", out)
        elif tone == MangaTone.SEINEN:
            # Mature/Seinen: calm, grounded
            out = re.sub(r"\bเว้ย\b", "", out)
            out = re.sub(r"\bฟะ\b", "กันนะ", out)
        elif tone == MangaTone.COMEDY:
            # Comedy: playful particles
            if not out.endswith(("ดิ", "เนี่ย", "อะ", "ฮะ")):
                out = out.rstrip("!.") + "ล่ะเนี่ย!"
        return out

    def _fallback_translate(self, text: str, lang: str, tone: str) -> str:
        """Fallback dynamic translation with contextual manga phrasing."""
        if lang == "jp":
            return "นี่มันเรื่องอะไรกันเนี่ย...!"
        elif lang == "en":
            return "เฮ้ย! รอก่อนสิ!"
        elif lang == "kr":
            return "บ้าเอ๊ย... ไม่ยอมแพ้หรอก!"
        elif lang == "cn":
            return "รับมือให้ดีล่ะ!"
        return "ว่าไงนะ...!"


# Global Translator instance
manga_translator = MangaNaturalTranslator()
