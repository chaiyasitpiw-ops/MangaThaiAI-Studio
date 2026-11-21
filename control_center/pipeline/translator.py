"""
MangaThaiAI-Studio: Manga Localization & Natural Dialogue Translation Engine
Transforms stiff robotic machine translations into authentic, expressive Thai manga dialogue.
Supports Japanese (JP), English (EN), Korean (KR), and Chinese (CN).
Features customizable tone presets: Shonen (Action), Shojo (Romance), Seinen (Mature), Comedy (Gag).
"""

import re
from typing import Any, Dict, List, Optional
import httpx


class MangaTone:
    SHONEN = "shonen"       # โชเน็น/ต่อสู้: ดุดัน โผงผาง (แก, ข้า, หนอย, ลุย)
    SHOJO = "shojo"         # ตาหวาน/รัก: ละมุน ซึนเดเระ (นาย, ฉัน, บ้าจริง, ยะ)
    SEINEN = "seinen"       # สืบสวน/ดาร์ก: สุขุม จริงจัง เป็นธรรมชาติ
    COMEDY = "comedy"       # ตลก/แก๊ก: กวนๆ ภาษาพูด วลีฮาๆ
    ADULT_18 = "adult_18"   # 🔞 18+ / มังงะผู้ใหญ่: เร้าอารมณ์ ครางเสียว จัดหนัก เผ็ดร้อน ดาร์ก & ฟิน


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

        # English comic & manhwa slang adaptations
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
            # Webtoon / Fantasy / Overgeared specific manhwa terms & emotional sound effects
            "hahaha": "ฮ่าๆๆๆ!",
            "mwahahaha": "วะฮ่าฮ่าฮ่า!",
            "mwahahaha!!!": "วะฮ่าฮ่าฮ่า!",
            "sigh": "เฮ้อ...",
            "coff": "แค่กๆ...",
            "cough": "แค่กๆ...",
            "grr": "หนอย...",
            "blech": "แหวะ...",
            "pewpew": "ปิ้วๆ~",
            "pewpew~": "ปิ้วๆ~",
            "pew pew": "ปิ้วๆ~",
            "bullets of love": "กระสุนแห่งความรัก!",
            "sweet potato latte": "ลาเต้มันหวาน",
            "huh": "หา?!",
            "huh?": "หา?!",
            "king's quest": "เควสต์ของราชา",
            "the king's role": "บทบาทของราชา",
            "declaration of war": "การประกาศสงคราม",
            "linked quest": "เควสต์ต่อเนื่อง",
            "quest clear conditions": "เงื่อนไขการเคลียร์ภารกิจ",
            "quest clear condition": "เงื่อนไขการเคลียร์ภารกิจ",
            "level requirement": "เงื่อนไขเลเวล",
            "crafting recipe": "สูตรสร้างไอเทม",
            "exclusive quest": "เควสต์เฉพาะตัว",
            "exclusive quests": "เควสต์เฉพาะตัว",
            "status window": "หน้าต่างสถานะ",
            "the last one was a real pain": "คราวก่อนแทบกระอักเลือดเลยแฮะ",
            "i wonder what this one has in store": "อยากรู้จริงว่าคราวนี้จะมีอะไรรออยู่",
            "please resolve the troubles of the people": "โปรดช่วยคลี่คลายความทุกข์ยากของราษฎรด้วยเถิด",
            "you have experienced the lives of the people and learned their suffering": "ท่านได้สัมผัสชีวิตของผู้คนและรับรู้ถึงความทุกข์ยากของพวกเขาแล้ว",
            "the rewards are pretty impressive": "รางวัลตอบแทนยอดเยี่ยมสมน้ำสมเนื้อจริง ๆ",
            "am i supposed to find time for that": "จะเอาเวลาที่ไหนไปทำฟะเนี่ย?!",
            "am i supposed to find time for that?!": "จะเอาเวลาที่ไหนไปทำฟะเนี่ย?!",
            "they hold us back at every turn": "พวกมันคอยขัดแข้งขัดขาเราตลอดเลย",
            "grr, those fucking imperial bastards": "หนอย... ไอ้พวกจักรวรรดิเวรเอ๊ย...",
            "you arrogant imperial bastards": "ไอ้พวกสวะจักรวรรดิอวดดี!",
            "you arrogant imperial bastards!!!": "ไอ้พวกสวะจักรวรรดิอวดดี!",
            "become prey for my army! mwahahaha!!!": "จงมาเป็นเหยื่อให้กองทัพของข้าซะ! วะฮ่าฮ่าฮ่า!",
            "become prey for my army": "จงมาเป็นเหยื่อให้กองทัพของข้าซะ!",
            "there is a way to really screw the empire over. would you like to hear it?": "มีวิธีเอาคืนจักรวรรดิให้สาสมอยู่ครับ อยากฟังไหมล่ะครับ?",
            "a way to screw the empire over? what is": "วิธีเอาคืนจักรวรรดิเรอะ? มันคืออะไร",
            "the empire will attack valhalla soon": "อีกไม่ช้าจักรวรรดิจะเข้าโจมตีวัลฮัลลาครับ",
            "go to valhalla and help ares": "ไปที่วัลฮัลลาแล้วช่วยอาเรสซะ",
            "isn't it dangerous to openly oppose the empire": "การไปขัดข้อกับจักรวรรดิตรงๆ มันไม่อันตรายไปหน่อยเรอะ?",
            "isn't it dangerous to openly oppose the empire?": "การไปขัดข้อกับจักรวรรดิตรงๆ มันไม่อันตรายไปหน่อยเรอะ?",
            "that's why you should go alone, without any troops": "เพราะงั้นถึงต้องไปคนเดียวโดยไม่มีกองทหารไงครับ",
            "with your identity concealed. of course": "แน่นอนว่าต้องปิดบังตัวตนด้วยครับ",
            "between this and madra's quest, there's no end in sight": "ไหนจะเควสต์นี้ ไหนจะเควสต์ของมาดราอีก มองไม่เห็นจุดสิ้นสุดเลยแฮะ",
            "even helping ten people a day would": "ต่อให้ช่วยวันละสิบคนก็ยัง...",
            "did it count all the good deeds ruby has done as the saintess": "หรือว่ามันนับรวมความดีทั้งหมดที่รูบี้ทำในฐานะนักบุญหญิงไปด้วยเรอะ?!",
            "did it count all the good deeds ruby has done as the saintess?!": "หรือว่ามันนับรวมความดีทั้งหมดที่รูบี้ทำในฐานะนักบุญหญิงไปด้วยเรอะ?!",
            "it should only count the good deeds she has done since the overgeared kingdom was founded, but she has already reached 5,000": "มันควรจะนับแค่ความดีหลังจากก่อตั้งอาณาจักรโอเวอร์เกียร์สิ แต่นี่เธอช่วยไปถึง 5,000 คนแล้วเรอะ?!",
            "you seem to be in a good mood": "ดูอารมณ์ดีจังนะ",
            "sister! want me to buy you a sweet potato latte": "น้องสาว! ให้พี่ซื้อลาเต้มันหวานให้เอาไหม?!",
            "sister! want me to buy you a sweet potato latte?": "น้องสาว! ให้พี่ซื้อลาเต้มันหวานให้เอาไหม?!",
            "what does that mean? why did the quest suddenly": "หมายความว่ายังไงกัน? ทำไมจู่ๆ เควสต์ถึง...",
            "what does that mean? why did the quest suddenly-?!": "หมายความว่ายังไงกัน? ทำไมจู่ๆ เควสต์ถึง...",
            # 18+ Adult English comic & webtoon terms
            "i'm cumming": "ฉันจะเสร็จแล้ว...!",
            "i'm coming": "ฉันจะเสร็จแล้ว...!",
            "cum for me": "เสร็จพร้อมฉันนะ...",
            "cum inside me": "แตกข้างในฉันเลย...",
            "fill me up": "เติมเต็มข้างในฉันที...",
            "it feels so good": "มันรู้สึกดีเหลือเกิน...",
            "feels so good": "รู้สึกดีสุดๆ...",
            "deeper": "ลึกกว่านี้อีก...",
            "harder": "แรงกว่านี้อีก...",
            "don't stop": "อย่าหยุดนะ...",
            "please don't stop": "ได้โปรดอย่าหยุดนะ...",
            "i can't take it anymore": "ฉันทนไม่ไหวแล้ว...",
            "i can't hold it": "จะกลั้นไม่ไหวแล้ว...",
            "it's so big": "มันใหญ่เกินไปแล้ว...",
            "so big": "ใหญ่จัง...",
            "so tight": "แน่นไปหมดเลย...",
            "i'm so wet": "แฉะไปหมดแล้ว...",
            "suck it": "ช่วยอมให้หน่อยสิ...",
            "lick it": "เลียตรงนั้นสิ...",
            "fuck me": "จัดฉันที... / เอาฉันแรงๆ เลย...",
            "fuck harder": "กระแทกแรงกว่านี้...",
            "ahhn": "อ๊าง...!",
            "ahh": "อ่าห์...",
            "ngh": "อื้ม...!",
            "mmph": "อื้อออ...",
        }

        # Korean manhwa common idioms & 18+ Adult webtoon terms
        self.kr_slang_map = {
            "젠장": "โธ่เว้ย...!",
            "말도 안 돼": "เป็นไปไม่ได้น่า...!",
            "죽어라": "ไปลงนรกซะ!",
            "닥쳐": "หุบปากไปเลย!",
            "오빠": "พี่คะ / พี่",
            "형": "พี่ / ลูกพี่",
            "대박": "สุดยอดไปเลยแฮะ!",
            "어이가 없네": "พูดไม่ออกเลยจริง ๆ...",
            "퀘스트": "เควสต์",
            "상태창": "หน้าต่างสถานะ",
            "레벨업": "เลเวลอัป!",
            # 18+ Adult Manhwa (NewXtoon, Toptoon, Lezhin)
            "다 따먹음": "จับกินเรียบ",
            "따먹음": "จัดการเรียบ / ฟันเรียบ",
            "따먹다": "จับกิน / เคลม / ฟัน",
            "그럼우선 무릎끓고 빨아주실래요?": "งั้นก่อนอื่น คุกเข่าลงแล้วช่วยอมให้ฉันหน่อยได้ไหม...?",
            "그럼우선 무릎꿇고 빨아주실래요?": "งั้นก่อนอื่น คุกเข่าลงแล้วช่วยอมให้ฉันหน่อยได้ไหม...?",
            "그럼우선": "งั้นก่อนอื่น...",
            "무릎끓고": "คุกเข่าลง...",
            "무릎꿇고": "คุกเข่าลง...",
            "빨아주실래요?": "ช่วยอมให้หน่อยได้ไหม...?",
            "빨아주실래요": "ช่วยอมให้หน่อยได้ไหม...",
            "빨아줘": "อมให้หน่อยสิ...",
            "빨아": "ดูดสิ... / อมเข้าไป...",
            "하앙": "อ๊าง...!",
            "하아": "ฮ้าาา...",
            "앗": "อ๊ะ...!",
            "읏": "อื้ม...!",
            "응": "อืม...",
            "기분 좋아": "รู้สึกดีจัง...",
            "너무 좋아": "ฟินสุดๆ เลย...",
            "더 깊이": "ลึกกว่านี้อีก...",
            "더 세게": "แรงกว่านี้...",
            "안돼": "ไม่นะ... / อย่านะ...",
            "가버려": "จะเสร็จแล้ว...!",
            "갈 것 같아": "จะทนไม่ไหวแล้ว...",
            "싸줘": "แตกข้างในนะ...",
            "싸버렸어": "แตกออกมาแล้ว...",
            "젖었어": "แฉะไปหมดแล้ว...",
            "크다": "ใหญ่จัง...",
            "너무 커": "มันใหญ่เกินไปแล้ว...",
            "넣어줘": "ใส่เข้ามาสิ...",
            "만져줘": "จับตรงนั้นสิ...",
            "신음": "เสียงคราง",
        }

        # Russian manga / manhwa & 18+ adult terms
        self.ru_slang_map = {
            # Exclamations & General
            "что за черт": "อะไรวะเนี่ย!",
            "черт": "บัดซบเอ๊ย!",
            "черт возьми": "โธ่เว้ย!",
            "блин": "ให้ตายสิ!",
            "сука": "เวรเอ๊ย!",
            "блять": "ไอ้เวรเอ๊ย!",
            "бля": "ชิบหาย!",
            "не может быть": "เป็นไปไม่ได้น่า...!",
            "подожди": "เดี๋ยวก่อนสิ!",
            "стой": "หยุดนะ!",
            "заткнись": "หุบปากไปซะ!",
            "пошел ты": "ไสหัวไปซะ!",
            "пожалуйста": "ได้โปรดเถอะ...",
            "спасибо": "ขอบใจนะ",
            "невероятно": "เหลือเชื่อเลย...",
            # 18+ Adult Russian terms
            "я кончаю": "ฉันจะเสร็จแล้ว...!",
            "кончаю": "จะเสร็จแล้ว...!",
            "глубже": "ลึกกว่านี้อีก...",
            "сильнее": "แรงกว่านี้...",
            "еще": "เอาอีก...",
            "не останавливайся": "อย่าหยุดนะ...",
            "так хорошо": "มันรู้สึกดีเหลือเกิน...",
            "мне так приятно": "ฟินสุดๆ เลย...",
            "не могу больше": "ทนไม่ไหวแล้ว...",
            "внутри": "ข้างใน...",
            "кончи в меня": "แตกข้างในฉันเลย...",
            "трахать": "จัดหนัก / ทำเรื่องอย่างว่า",
            "отсоси": "อมให้หน่อยสิ...",
            "соси": "ดูดสิ...",
            "мокрая": "แฉะไปหมดแล้ว...",
            "такой большой": "ใหญ่จังเลย...",
            "ах": "อ่าห์...",
            "ох": "โอ๊ย... / อ๊ะ...",
            "ух": "ซี้ด...",
            "ммм": "อืมมม...",
        }

        # Chinese manhua common idioms & 18+ Adult terms
        self.cn_slang_map = {
            "混账": "สารเลวเอ๊ย!",
            "找死": "รนหาที่ตาย!",
            "不可能": "เป็นไปไม่ได้เด็ดขาด!",
            "饶命": "ไว้ชีวิตข้าด้วย!",
            "放肆": "บังอาจนัก!",
            "阁下": "ท่านผู้เจริญ / ท่าน",
            "看招": "รับกระบวนท่านี้ไปซะ!",
            # 18+ Adult Chinese terms
            "好爽": "เสียวจัง...!",
            "好舒服": "รู้สึกดีเหลือเกิน...",
            "高潮": "เสร็จสม / จุดสุดยอด",
            "快到了": "ใกล้จะเสร็จแล้ว...",
            "受不了了": "ทนไม่ไหวแล้ว...",
            "受不了": "ไม่ไหวแล้ว...",
            "用力点": "แรงอีกสิ...",
            "用力": "แรงๆ เลย...",
            "深一点": "ลึกกว่านี้อีก...",
            "还要": "ยังอยากได้อีก...",
            "不要停": "อย่าหยุดนะ...",
            "射在里面": "แตกข้างในเลย...",
            "射了": "ปล่อยออกมาแล้ว...",
            "太大了": "มันใหญ่เกินไปแล้ว...",
            "好大": "ใหญ่จัง...",
            "湿透了": "แฉะไปหมดแล้ว...",
            "慢一点": "ช้าหน่อยสิ...",
            "舔我": "เลียให้ฉันที...",
            "嗯啊": "อื้อหือ...!",
            "啊哈": "อ๊าง...!",
        }

        # Stiff phrase cleaner (Fixes Google Translate robotic artifacts in Thai text)
        self.stiff_thai_cleaners = [
            (r"\bคุณ\b(?=.*(?:ตาย|ฆ่า|สารเลว|ลุย|แก))", "แก"),
            (r"\bฉันจะทำการ\b", "ฉันจะ"),
            (r"\bทำการ([ก-๙]+)", r"\1"),
            (r"\bมีความสามารถในการ\b", "สามารถ"),
            (r"\bมีความจำเป็นต้อง\b", "จำเป็นต้อง"),
            (r"\bมันเป็นเรื่องโกหก\b", "โกหกน่า..."),
            (r"\bมันคืออะไร\b", "อะไรกันเนี่ย..."),
            (r"\bสิ่งนั้นเป็นไปไม่ได้\b", "เป็นไปไม่ได้หรอก!"),
            (r"\bฉันไม่สามารถทำได้\b", "ทำไม่ไหวแล้ว..."),
            (r"\bโปรดรอสักครู่\b", "รอก่อนสิ!"),
            (r"\bกินสิ่งนี้ซะ\b", "กินนี่เข้าไปซะ!"),
            (r"\bไปสู่ความตาย\b", "ไปตายซะ!"),
            # Manhwa / Game terminology fixes from raw MT
            (r"คำถามของกษัตริย์", "เควสต์ของราชา"),
            (r"ภารกิจของกษัตริย์", "เควสต์ของราชา"),
            (r"คำถามที่เชื่อมโยง", "เควสต์ต่อเนื่อง"),
            (r"คำถามพิเศษเฉพาะ", "เควสต์พิเศษ"),
            (r"คำถามเหล่านี้เป็นเอกสิทธิ์", "เควสต์เหล่านี้เป็นเควสต์เฉพาะตัว"),
            (r"ภารกิจเหล่านี้มีไว้สำหรับกษัตริย์เท่านั้น", "เควสต์เหล่านี้มีไว้สำหรับราชาเท่านั้น"),
            (r"ชุดคำถาม", "ชุดเควสต์"),
            (r"ข้อกำหนดระดับ", "เงื่อนไขเลเวล"),
            (r"ตามข้อกำหนดระดับของมัน", "เพราะติดเงื่อนไขเลเวล"),
            (r"สูตรการประดิษฐ์", "สูตรสร้างไอเทม"),
            (r"ความโลภกลายเป็น", "กริดกลายเป็น"),
            (r"ความโลภ", "กริด"),
            (r"กรีดฮาดาเสร็จสิ้นแล้ว", "กริดได้เคลียร์เรียบร้อยแล้ว"),
            (r"บทบาทของกษัตริย์", "บทบาทของราชา"),
            (r"บาทบาทราชา", "บทบาทของราชา"),
            (r"บาทบาท", "บทบาท"),
            (r"บทบาทราชา", "บทบาทของราชา"),
            (r"<KING'?S\s*SWORD>", "ดาบแห่งราชา"),
            (r"<POLITICAL\s*POWER>", "อำนาจทางการเมือง"),
            (r"\bมีอะไรอยู่ในร้าน\b", "จะมีอะไรรออยู่บ้าง"),
            (r"\bมีอะไรในร้าน\b", "จะมีอะไรรออยู่บ้าง"),
            (r"ฉันสงสัยว่า(?:อันนี้|สิ่งนี้|คราวนี้)?จะมีอะไรรออยู่บ้าง", "อยากรู้จริงว่าคราวนี้จะมีอะไรรออยู่"),
            (r"(?:มัน|อัน|คราว|ครั้ง)?(?:ก่อน|ที่แล้ว|สุดท้าย)?(?:คือ|เป็น)?ความเจ็บปวดที่แท้จริง", "คราวก่อนแทบกระอักเลือดเลยแฮะ"),
            (r"ฉันจะหาเวลาทำสิ่งนั้นได้อย่างไร", "จะเอาเวลาที่ไหนไปทำฟะเนี่ย"),
            (r"สมาชิกราชวงศ์ RUBY", "สมาชิกราชวงศ์ รูบี้"),
            (r"สมาชิกราชวงศ์รูบี้", "สมาชิกราชวงศ์ รูบี้"),
            (r"\bRUBY\b", "รูบี้"),
            (r"ในเบเฮ็น", "ในเบเฮน"),
            (r"ตามชื่อที่แนะนำ", "ก็ตามชื่อนั่นแหละ"),
            (r"โปรดแก้ไขปัญหาของประชาชน", "โปรดช่วยคลี่คลายความทุกข์ยากของราษฎรด้วยเถิด"),
            (r"คุณได้สัมผัสชีวิตของผู้คนและเรียนรู้ความทุกข์ของพวกเขา", "ท่านได้สัมผัสวิถีชีวิตของผู้คนและรับรู้ถึงความทุกข์ยากของพวกเขาแล้ว"),
            (r"ในฐานะนักบุญ", "ในฐานะนักบุญหญิง"),
            (r"กริดได้เสร็จสิ้น", "กริดได้เคลียร์"),
            (r"ส่วนแรกของเควสต์", "เควสต์ส่วนแรก"),
            (r"ไม่สามารถรวมเอาความแข็งแกร่งของมันไว้ในที่เดียวได้", "ไม่สามารถทุ่มเทกำลังทั้งหมดไว้ที่เดียวได้หรอก"),
            (r"สิ่งอำนวยความสะดวกด้านเคมีบำบัด", "โรงเล่นแร่แปรธาตุ"),
            (r"สิ่งอำนวยความสะดวกในการเล่นแร่แปรธาตุ", "โรงเล่นแร่แปรธาตุ"),
            (r"สิ่งอำนวยความสะดวกการเล่นแร่แปรธาตุ", "โรงเล่นแร่แปรธาตุ"),
            (r"การเล่นแร่แปรธาตุของเรย์ดัน", "การเล่นแร่แปรธาตุของไรดัน"),
            (r"เรย์ดัน", "ไรดัน"),
            (r"ลอเอล", "เลาเอล"),
            (r"ทำภารกิจสำเร็จแล้ว", "เคลียร์เควสต์สำเร็จแล้ว"),
            (r"ปลดล็อคสถานะภารกิจของคุณ", "เป็นรางวัลเควสต์"),
            (r"อาณาจักรที่โอเวอร์เกียร์", "อาณาจักรโอเวอร์เกียร์"),
            (r"OVER\s*GEARED\s*KINGDOM", "อาณาจักรโอเวอร์เกียร์"),
            (r"OVERGEARED\s*KINGDOM", "อาณาจักรโอเวอร์เกียร์"),
            (r"Over\s*Geared\s*Kingdom", "อาณาจักรโอเวอร์เกียร์"),
            (r"ทำไมคำถามถึงจู่ๆ", "ทำไมเควสต์ถึงจู่ๆ"),
            (r"ทำไมถึงถามอย่างกะทันหัน", "ทำไมเควสต์ถึงเด้งขึ้นมาดื้อๆ"),
            (r"นักบุญหญิงเอส", "นักบุญหญิง"),
            (r"ฉันสงสัยว่าสิ่งนี้มีอะไรบ้าง", "อยากรู้จริงว่าคราวนี้จะมีอะไรรออยู่"),
            (r"ฉันสงสัยว่าสิ่งนี้คืออะไร", "อยากรู้จริงว่าคราวนี้คืออะไร"),
            (r"สิ่งนี้มีอะไรบ้าง", "จะมีอะไรรออยู่บ้าง"),
            # 18+ Adult Manhwa / Manga phrasing fixes (Eliminate robotic literal machine translation)
            (r"กินเพื่อนร่วมห้อง", "จับเพื่อนร่วมห้องกินเรียบ"),
            (r"กินเพื่อนร่วมชั้น", "จับเพื่อนร่วมห้องกินเรียบ"),
            (r"กินเพื่อนๆ", "จับเพื่อนกินเรียบ"),
            (r"กินพวกเธอ", "จัดพวกเธอซะเรียบ"),
            (r"เย็ดฉันให้หนักขึ้น", "เอาฉันแรงกว่านี้สิ"),
            (r"เย็ดฉันแรงขึ้น", "กระแทกฉันแรงกว่านี้สิ"),
            (r"เย็ดฉัน", "จัดฉันที"),
            (r"เย็ด", "จัดหนัก"),
            (r"คุณจะคุกเข่าดูดฉันไหม", "ช่วยคุกเข่าลงแล้วอมให้ฉันหน่อยได้ไหม"),
            (r"คุณจะคุกเข่าดูดผมไหม", "ช่วยคุกเข่าลงแล้วอมให้ผมหน่อยได้ไหม"),
            (r"คุณจะคุกเข่า", "คุกเข่าลง"),
            (r"ดูดฉันไหม", "อมให้ฉันหน่อยได้ไหม"),
            (r"ดูดผมไหม", "อมให้ผมหน่อยได้ไหม"),
            (r"ดูดของฉัน", "อมของฉัน"),
            (r"ดูดของผม", "อมของผม"),
            (r"\bไก่ผู้\b", "ท่อนเอ็น"),
            (r"\bแมว\b(?=.*(?:เปียก|แฉะ|เสร็จ|สอด|ใส่))", "ร่องรัก"),
            (r"การมีเพศสัมพันธ์", "ทำเรื่องอย่างว่า"),
            (r"มีเพศสัมพันธ์", "ทำเรื่องอย่างว่า"),
            (r"หลั่งน้ำอสุจิ", "ปล่อยน้ำรัก"),
            (r"จุดสุดยอดทางเพศ", "จุดสุดยอด"),
            (r"การสำเร็จความใคร่", "ช่วยตัวเอง"),
            (r"ฉันกำลังคัมมิง", "ฉันจะเสร็จแล้ว..."),
            (r"คัมมิง", "เสร็จแล้ว"),
            (r"ลึกลงไปอีก", "ลึกกว่านี้อีก"),
            (r"รู้สึกดีมาก(?=.*[~!\. …])", "รู้สึกดีชะมัด"),
        ]

    def polish_thai_dialogue(self, thai_text: str, tone: str = MangaTone.SHONEN) -> str:
        """Polishes raw Thai translation with authentic manga tone and removes robotic artifacts."""
        out = thai_text.strip()
        if not out:
            return ""
        for pattern, replacement in self.stiff_thai_cleaners:
            out = re.sub(pattern, replacement, out)
        out = self._apply_tone(out, tone)
        return out

    def lookup_slang(self, source_text: str, source_lang: str = "auto") -> Optional[str]:
        """Looks up exact or short-phrase matches in the manga slang dictionary. Returns None if not found."""
        cleaned_src = source_text.strip()
        if not cleaned_src:
            return None

        words_count = len(cleaned_src.split())
        lang = source_lang.lower()
        if lang == "auto":
            if re.search(r"[\u0400-\u04ff]", cleaned_src):
                lang = "ru"
            elif re.search(r"[\uac00-\ud7af\u1100-\u11ff]", cleaned_src):
                lang = "kr"
            elif re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", cleaned_src):
                lang = "jp" if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", cleaned_src) else "cn"
            else:
                lang = "en"

        if lang == "jp":
            for jp_key, th_val in self.jp_slang_map.items():
                if jp_key in cleaned_src:
                    return th_val
        elif lang == "en":
            cleaned_lower = cleaned_src.lower()
            if cleaned_lower in self.en_slang_map:
                return self.en_slang_map[cleaned_lower]
            if words_count <= 4:
                for en_key, th_val in self.en_slang_map.items():
                    if en_key == cleaned_lower or en_key in cleaned_lower:
                        return th_val
        elif lang in ("kr", "ko"):
            for kr_key, th_val in self.kr_slang_map.items():
                if kr_key in cleaned_src:
                    return th_val
        elif lang == "ru":
            cleaned_lower = cleaned_src.lower()
            if cleaned_lower in self.ru_slang_map:
                return self.ru_slang_map[cleaned_lower]
            if words_count <= 3:
                for ru_key, th_val in self.ru_slang_map.items():
                    if ru_key == cleaned_lower or ru_key in cleaned_lower:
                        return th_val
        elif lang in ("cn", "zh"):
            for cn_key, th_val in self.cn_slang_map.items():
                if cn_key in cleaned_src:
                    return th_val
        return None

    def _unpack_api_result(self, data: Any) -> str:
        """Safely unwraps nested list structures returned by translation APIs."""
        while isinstance(data, list) and len(data) > 0:
            data = data[0]
        return str(data).strip() if data else ""

    def _query_translation_api(self, text: str, source_lang: str = "auto") -> Optional[str]:
        """Queries reliable translation APIs with automatic multi-engine failover."""
        lang_code_map = {
            "auto": "auto",
            "en": "en",
            "english": "en",
            "kr": "ko",
            "ko": "ko",
            "korean": "ko",
            "ru": "ru",
            "russian": "ru",
            "cyrillic": "ru",
            "cn": "zh-CN",
            "zh": "zh-CN",
            "chinese": "zh-CN",
            "jp": "ja",
            "ja": "ja",
            "japanese": "ja",
        }
        sl = lang_code_map.get(source_lang.lower(), "auto")

        # Engine 1: Google dict-chrome-ex (High speed, avoids 429 rate limit)
        try:
            url = "https://clients5.google.com/translate_a/t"
            params = {"client": "dict-chrome-ex", "sl": sl, "tl": "th", "q": text}
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36"}
            r = httpx.get(url, params=params, headers=headers, timeout=6.0)
            if r.status_code == 200:
                unpacked = self._unpack_api_result(r.json())
                if unpacked:
                    return unpacked
        except Exception:
            pass

        # Engine 2: MyMemory API Fallback
        try:
            url = "https://api.mymemory.translated.net/get"
            langpair = f"{sl}|th" if sl != "auto" else "en|th"
            params = {"q": text, "langpair": langpair}
            r = httpx.get(url, params=params, timeout=5.0)
            if r.status_code == 200:
                res = r.json().get("responseData", {}).get("translatedText", "")
                if res and isinstance(res, str) and not res.startswith("MYMEMORY WARNING"):
                    return res.strip()
        except Exception:
            pass

        return None

    def translate_and_polish(
        self,
        source_text: str,
        source_lang: str = "auto",
        tone: str = MangaTone.SHONEN
    ) -> str:
        """
        Translates and polishes dialogue into authentic natural Thai manga prose.
        source_lang: 'kr', 'ru', 'en', 'cn', 'jp', or 'auto'
        tone: 'adult_18', 'shonen', 'shojo', 'seinen', 'comedy'
        """
        cleaned_src = source_text.strip()
        if not cleaned_src:
            return ""

        # Auto detect language if set to auto
        lang = source_lang.lower()
        if lang == "auto":
            if re.search(r"[\u0400-\u04ff]", cleaned_src):
                lang = "ru"
            elif re.search(r"[\uac00-\ud7af\u1100-\u11ff]", cleaned_src):
                lang = "kr"
            elif re.search(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff]", cleaned_src):
                lang = "jp" if re.search(r"[\u3040-\u309f\u30a0-\u30ff]", cleaned_src) else "cn"
            else:
                lang = "en"

        # 1. Check slang dictionary for authentic manga expressions
        translated = self.lookup_slang(cleaned_src, source_lang=lang)

        # 2. If not in slang map, query real translation engine
        if not translated:
            api_res = self._query_translation_api(cleaned_src, source_lang=lang)
            translated = api_res if api_res else cleaned_src

        # 3. Apply Tone Adjustments
        polished = self._apply_tone(translated, tone)

        # 4. Clean any robotic Thai phrasing artifacts
        for pattern, replacement in self.stiff_thai_cleaners:
            polished = re.sub(pattern, replacement, polished)

        return polished

    def _apply_tone(self, text: str, tone: str) -> str:
        """Fine-tunes pronouns, sentence particles, and removes artificial symbols to match MangaX style."""
        out = text

        # Strip fake artificial symbols
        out = re.sub(r"[<>]", "", out)              # Remove < > tags
        out = re.sub(r"^\*+\s*", "", out)           # Remove leading asterisks
        out = re.sub(r"[\s\·\|]+", " ", out).strip() # Clean bullets and stray pipes
        out = re.sub(r"\b(USD|USD\s*ต่างๆ)\b", "", out) # Clean accidental OCR acronyms
        # Fix unclosed brackets safely without appending duplicate closing brackets
        if "[" in out and "]" not in out:
            out = out + "]"
        if "(" in out and ")" not in out:
            out = out + ")"

        if tone == MangaTone.ADULT_18:
            # 🔞 18+ Adult Tone: Sensual, intimate, passionate, evocative adult dialogue
            out = re.sub(r"\bคุณจะ\b", "ช่วย", out)
            out = re.sub(r"\bคุณ\b", "เธอ", out)
            out = re.sub(r"\bดูดฉัน\b", "อมให้ฉัน", out)
            out = re.sub(r"\bดูดผม\b", "อมให้ผม", out)
            out = re.sub(r"\bกินผม\b", "จัดผม", out)
            out = re.sub(r"\bกินฉัน\b", "จัดฉัน", out)
            out = re.sub(r"\bเว้ย\b", "", out)
            out = re.sub(r"\bฟะ\b", "นะ...", out)
            if not out.endswith(("!", "?", "...", "…", "~")):
                out = out + "..."
        elif tone == MangaTone.SHONEN:
            # Action/Shonen: energetic, punchy dialogue without breaking characters
            out = re.sub(r"\bฉันจะทำการ\b", "ข้าจะ", out)
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
            out = re.sub(r"\bล่ะ\b", "ล่ะเนี่ย", out)
        return out.strip()


# Global Translator instance
manga_translator = MangaNaturalTranslator()
