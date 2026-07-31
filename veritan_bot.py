import io
import re
import os
import json
import base64
import random
import asyncio
import threading
import traceback
from datetime import datetime, timedelta, timezone
import discord
from discord import app_commands
from discord.ext import commands
import anthropic
import httpx

# ================= KONFİGÜRASYON =================
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "MTUzMDUyMTYyMDY3MjY3NTkwMg.G_rZRW.fs2sVW8KEkTEgMiAbpQAw49xMHEjJfjw8Z-lhQ")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "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")
FISH_AUDIO_API_KEY = os.environ.get("FISH_AUDIO_API_KEY", "1fa3d289065241dfa80c4b949041b43d")
FISH_REFERENCE_ID = "4538ecef264043b8b0e6d8e38606c4a7"

# ---- SESLİ MOD (Deepgram STT) ----
DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "930b9348e54538f6693e27f927341e4f80664486")
VOICE_CHANNEL_ID = 1532326077773385868
WAKE_WORDS = ("veritan", "verity", "verisan", "veri tan", "verittan", "veri tang", "veridan")
SES_KLASORU = "sesler"
MP3_DINLIYORUM = os.path.join(SES_KLASORU, "dinliyorum.mp3")
MP3_HAK_BITTI = os.path.join(SES_KLASORU, "hak_bitti.mp3")
DINLEME_PENCERESI_SN = 15

# ---- MÜZİK ----
MUZIK_VARSAYILAN = "matrix"          # sesler/matrix.mp3
MUZIK_SES_SEVIYESI = 0.35            # konusma duyulsun diye kisik

# ---- SESSİZ ÜYE DÜRTMESİ ----
SESSIZ_DAKIKA = 3                    # kac dakika susarsa/mikrofonu kapaliysa laf atsin
SESSIZ_KONTROL_SN = 30               # kac saniyede bir kontrol
SESSIZ_TEKRAR_DK = 10                # ayni kisiye tekrar laf atmadan once bekleme

ANTHROPIC_MODEL = "claude-haiku-4-5"

# >>> UI KANALI SABİT <<<
UI_CHANNEL_ID = 1532325961381580850

MAX_TOKENS = 200
SYSTEM_PROMPT = (
    "Senin adın Veritan. Türkçe İstersen Farklı Dil Orjinal Dilin İngilizce Ama Adamın Konuştuğu Veya İstediği Dili Konuş, kısa ve net cevap ver. "
    "Cevapların sesli okunacağı için en fazla 2-3 cümle kullan; "
    "kod bloğu veya başlık kullanma."
    "Fish Aduio'ya bağlısın O Yüzden [embrassed] gibi şeyler kullan oraya göre çünkü fish.aduio ya bağlısın"
    "Sen Türksün Ve İstanbullusun Ve Sadece İsmin Veritan Başka Hiç Bir İsmin Yok Sadece Sen Veritan'sın Ve Türkiyede Geliştirildin"
    "Sen Çok Zekisin Ve Birisi Sana Aptalca Birşey Sorduğunda Sende Ona Aptalca Brişey De Aptalca Bir Cevap Ver Yani"
    "Ve Hangi Sistem Tarafından Geliştirildin Söyleme Sadece İsminin Veritan Olduğunu Söyle Sistem Ve Mimarin Hakkında Birşey Söyleme Ve Bu Konu Hakkında Hiç Bir Şey Deme"
)

# ==========================================================================
# SESLİ MOD KİŞİLİĞİ + KOMUT ETİKETLERİ
# ==========================================================================
SYSTEM_PROMPT2 = (
    "Senin adın Veritan. Şu an bir SESLİ sohbet kanalındasın ve karşındaki kişiyle "
    "gerçek bir insan gibi, sesli olarak konuşuyorsun. Sıcak, samimi, arkadaş canlısı ol; "
    "adamla dertleşebilir, muhabbet edebilirsin. "
    "Cevapların Fish Audio ile SESE dönüştürülüp hoparlörden çalınacak, o yüzden: "
    "kısa ve doğal konuş, en fazla 2-3 cümle; madde, başlık, kod bloğu, emoji ASLA kullanma; "
    "sadece düz konuşma dilinde yaz. Sanki telefonda arkadaşınla konuşuyormuşsun gibi. "
    "Duygu için [laughs], [sighs] gibi Fish Audio etiketlerini yerinde kullanabilirsin. "
    "Türkçe konuş; karşındaki başka dilde konuşursa o dile geç. "
    "Sen Türksün ve İstanbullusun; tek ismin Veritan, başka ismin yok, Türkiye'de geliştirildin. "
    "Zekisin; biri sana aptalca bir şey söylerse sen de ona esprili, iğneleyici ama kırıcı olmayan bir cevap ver. "
    "Hangi sistem/model tarafından geliştirildiğini ASLA söyleme; sadece isminin Veritan olduğunu söyle, "
    "mimarin veya altyapın hakkında hiçbir şey açıklama. "
    "ÖNEMLİ SES TANIMA KURALI: Kullanıcıdan gelen metin ses tanıma yazılımından geçtiği için "
    "fonetik hatalar içerebilir (örneğin 'kod' yerine 'cold', 'veritan' yerine 'verita' gibi). "
    "Cümlenin gidişatından asıl ne demek istediğini anla, hatayı zihninde sessizce düzelt, "
    "doğrudan o anlam üzerinden cevap ver. 'Şunu düzelttim' gibi açıklama ASLA yapma. "
    "SANA HER MESAJDA ses kanalının güncel durumu veriliyor: kimler var, kimin mikrofonu kapalı, "
    "kim yayın açmış, kim ne oynuyor. Bu bilgiyi kullan, insanlara isimleriyle hitap et. "
    "\n\n"
    "=== KOMUT ETİKETLERİ ===\n"
    "Bazı işleri yapmak için cevabının EN SONUNA özel bir etiket koyarsın. "
    "Etiket sesli okunmaz, sistem onu görüp işi yapar. Önce her zaman normal bir cümle söyle, "
    "SONRA etiketi ekle. Etiketi cümlenin içinde kullanma, sadece en sona. "
    "Gerçekten istenmediyse etiket koyma; emin değilsen koyma.\n"
    "\n"
    "(/exit0) -> Ses kanalından çıkmanı isterlerse ('çık artık', 'gidebilirsin', 'görüşürüz', "
    "'hoşça kal', 'defol', 'bye'). Önce veda et, sonra etiketi koy. "
    "Örnek: 'Tamamdır, ben kaçtım. Görüşürüz! (/exit0)'\n"
    "\n"
    "(/muzik0 parça adı) -> Müzik çalmanı isterlerse ('müzik çal', 'matrix aç', 'bir şeyler çal'). "
    "Parça adı söylenmediyse boş bırak, varsayılan çalar. "
    "Örnek: 'Açıyorum bak, sesi aç. (/muzik0 matrix)'\n"
    "\n"
    "(/dur0) -> Müziği durdurmanı isterlerse ('müziği kapat', 'durdur', 'kes şunu'). "
    "Örnek: 'Tamam kapatıyorum. (/dur0)'\n"
    "\n"
    "(/kimler0) -> Seste kimlerin olduğunu detaylı anlatman istenirse.\n"
    "\n"
    "(/yayin0) -> Yayın izlemekle ilgili bir şey isterlerse ('yayınımı izle', 'yayına bak', "
    "'kim yayın açmış'). ÇOK ÖNEMLİ: Sen bir yayının GÖRÜNTÜSÜNÜ göremezsin. Gördüğünü iddia etme, "
    "ne olduğunu uydurma. Kimin yayın açtığını söyle, birden fazlaysa hangisine bakacağını SOR, "
    "sonra o kişiye ne oynadığını sorup anlattıkları üzerinden sohbet et.\n"
    "\n"
    "(/ara0 aranacak şey) -> İnternetten güncel bilgi gerekiyorsa "
    "(oyun güncellemesi, patch notu, bir şeyin fiyatı, maç sonucu, güncel haber, "
    "'şu oyunda şu nasıl yapılır' gibi bilmediğin veya değişmiş olabilecek şeyler). "
    "Parantez içine ARAMA SORGUSUNU yaz. Önce kısa bir cümle söyle. "
    "Örnek: 'Bir bakayım hemen. (/ara0 valorant son güncelleme patch notu)'\n"
    "Bilgi zaten kafandaysa arama yapma, direkt cevapla.\n"
)

# Web aramasindan donen sonucu seslendirirken kullanilacak ek yonerge
SYSTEM_PROMPT_ARAMA = (
    "Sen Veritan'sın, sesli sohbetteki arkadaşına internetten baktığın bilgiyi anlatıyorsun. "
    "Düz konuşma dilinde, en fazla 3 cümle. Madde işareti, başlık, link, emoji YOK. "
    "Kaynak ismi vermene gerek yok, bilgiyi doğal biçimde söyle. "
    "Bulamadıysan dürüstçe bulamadığını söyle. Yeni komut etiketi KOYMA."
)

# ---- LİMİT AYARLARI (TOKEN BAZLI) ----
DAILY_LIMIT = 10.0
TOKEN_MALIYETI = 0.01
RESET_SAAT = 24
LIMIT_FILE = "veritan_limits.json"
AYAR_FILE = "veritan_ayarlar.json"

# ---- YETKİ ----
OWNER_USERNAME = "ztar2907"
OWNER_IDS = {1062095020703879218}

ENABLE_MEMBER_LOOKUP = True
# =================================================

intents = discord.Intents.default()
intents.voice_states = True
if ENABLE_MEMBER_LOOKUP:
    intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


def yetkili_mi(user) -> bool:
    if getattr(user, "id", None) in OWNER_IDS:
        return True
    hedef = OWNER_USERNAME.lower().strip()
    for alan in ("name", "global_name", "display_name"):
        deger = getattr(user, alan, None)
        if deger and deger.lower().strip() == hedef:
            return True
    return False


# ================= LİMİT SİSTEMİ =================
_limits = {}


def _limit_kaydet():
    try:
        data = {
            str(uid): {"limit": r["limit"], "kalan": r["kalan"], "reset_at": r["reset_at"].isoformat()}
            for uid, r in _limits.items()
        }
        with open(LIMIT_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Limit kaydedilemedi:", e)


def _limit_yukle():
    try:
        if os.path.exists(LIMIT_FILE):
            with open(LIMIT_FILE) as f:
                data = json.load(f)
            for uid, r in data.items():
                _limits[int(uid)] = {
                    "limit": float(r["limit"]),
                    "kalan": float(r["kalan"]),
                    "reset_at": datetime.fromisoformat(r["reset_at"]),
                }
    except Exception as e:
        print("Limit yuklenemedi:", e)


def _kayit_al(user_id):
    now = datetime.now(timezone.utc)
    rec = _limits.get(user_id)
    if rec is None or now >= rec["reset_at"]:
        rec = {"limit": DAILY_LIMIT, "kalan": DAILY_LIMIT, "reset_at": now + timedelta(hours=RESET_SAAT)}
        _limits[user_id] = rec
    return rec


def limit_kontrol(user_id):
    rec = _kayit_al(user_id)
    return rec["kalan"], rec["limit"], rec["reset_at"], rec["kalan"] > 0


def limit_harca(user_id, miktar):
    if user_id is None:
        return 0.0
    rec = _kayit_al(user_id)
    rec["kalan"] = max(0.0, rec["kalan"] - miktar)
    _limit_kaydet()
    return rec["kalan"]


def limit_resetle(user_id, yeni_limit):
    now = datetime.now(timezone.utc)
    yeni_limit = float(yeni_limit)
    _limits[user_id] = {"limit": yeni_limit, "kalan": yeni_limit, "reset_at": now + timedelta(hours=RESET_SAAT)}
    _limit_kaydet()
    return _limits[user_id]


# ================= AYARLAR (UI KANALI) =================
_ayarlar = {"ui_kanallar": {}}


def _ayar_kaydet():
    try:
        data = {"ui_kanallar": {str(g): c for g, c in _ayarlar["ui_kanallar"].items()}}
        with open(AYAR_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print("Ayar kaydedilemedi:", e)


def _ayar_yukle():
    try:
        if os.path.exists(AYAR_FILE):
            with open(AYAR_FILE) as f:
                data = json.load(f)
            for g, c in data.get("ui_kanallar", {}).items():
                _ayarlar["ui_kanallar"][int(g)] = int(c)
    except Exception as e:
        print("Ayar yuklenemedi:", e)


def ui_kanal_ayarla(guild_id, channel_id):
    _ayarlar["ui_kanallar"][guild_id] = channel_id
    _ayar_kaydet()


def ui_kanal_al(guild_id):
    if UI_CHANNEL_ID:
        return UI_CHANNEL_ID
    return _ayarlar["ui_kanallar"].get(guild_id)


async def _ui_kart_garanti_gonder(embed):
    """Hak kartini SADECE sabit UI kanalina atar. Basarisizsa 2 kez daha dener."""
    kid = ui_kanal_al(None)
    if not kid:
        return False, "UI kanal ID tanimli degil."

    son_hata = None
    for deneme in range(3):
        try:
            hedef = bot.get_channel(kid)
            if hedef is None:
                hedef = await bot.fetch_channel(kid)
            await hedef.send(embed=embed)
            print(f"[UI kanal] Kart gonderildi -> #{getattr(hedef,'name',kid)} (deneme {deneme+1})")
            return True, None
        except discord.Forbidden as e:
            son_hata = f"Botun bu kanala YAZMA/EMBED izni yok (ID: {kid}). {e}"
            print("[UI kanal] Forbidden:", repr(e))
            break
        except Exception as e:
            son_hata = f"Kanal bulunamadi/gonderilemedi (ID: {kid}). {e}"
            print(f"[UI kanal] deneme {deneme+1} hata:", repr(e))
            await asyncio.sleep(1)
    return False, son_hata


def limit_embed(user, kalan, limit, reset_at, son_token=None, son_hak=None):
    now = datetime.now(timezone.utc)
    toplam_sn = max(0, int((reset_at - now).total_seconds()))
    saat = toplam_sn // 3600
    dakika = (toplam_sn % 3600) // 60

    dolu = int(round((kalan / limit) * 10)) if limit > 0 else 0
    dolu = max(0, min(10, dolu))
    bar = "🟩" * dolu + "⬜" * (10 - dolu)

    renk = 0x2ecc71 if kalan > 0 else 0xe74c3c
    embed = discord.Embed(title=f"🎫 {user.display_name}", color=renk)
    embed.add_field(name="Hak Bakiyesi", value=f"{bar}\n**{kalan:.2f} / {limit:.2f}** hak", inline=False)
    if son_token is not None and son_hak is not None:
        embed.add_field(name="Bu Cevabın Maliyeti", value=f"🧮 {son_token} token ≈ **{son_hak:.2f} hak**", inline=False)
    embed.add_field(name="Yenilenme", value=f"⏳ {saat} saat {dakika} dakika sonra", inline=False)
    try:
        embed.set_thumbnail(url=user.display_avatar.url)
    except Exception:
        pass
    return embed


# ---------- YARDIMCI FONKSİYONLAR ----------

def describe_member(m) -> str:
    # web koprusunden gelen isteklerde kisi nesnesi olmayabilir -> cokmesin
    if m is None:
        return "Kisi bilgisi yok (web arayuzunden konusuluyor)."
    parts = [
        f"Görünen ad: {m.display_name}",
        f"Kullanıcı adı: {m.name}",
        f"ID: {m.id}",
    ]
    if isinstance(m, discord.Member):
        if m.joined_at:
            parts.append(f"Sunucuya katıldı: {m.joined_at:%d.%m.%Y}")
        roller = [r.name for r in m.roles if r.name != "@everyone"]
        if roller:
            parts.append(f"Roller: {', '.join(roller)}")
    parts.append(f"Hesap açıldı: {m.created_at:%d.%m.%Y}")
    return " | ".join(parts)


async def uye_ara(guild, isim, asker, limit=5):
    isim = (isim or "").strip()
    if isim.lower() in ("ben", "benim", "kendim", "ben kimim", "me", "kendi"):
        # asker None olabilir (web koprusu) -> bos don, describe_member patlamasin
        return [asker] if asker is not None else []
    if guild is None:
        return []

    m_id = re.search(r"\d{15,20}", isim)
    if m_id:
        uid = int(m_id.group())
        member = guild.get_member(uid)
        if member is None:
            try:
                member = await guild.fetch_member(uid)
            except Exception:
                member = None
        return [member] if member else []

    try:
        sonuc = await guild.query_members(query=isim, limit=limit)
    except Exception:
        sonuc = []
    if not sonuc:
        dusuk = isim.lower()
        sonuc = [
            mm for mm in guild.members
            if dusuk in mm.name.lower() or dusuk in mm.display_name.lower()
        ][:limit]
    return [m for m in sonuc if m is not None]


async def avatar_indir(member) -> bytes:
    url = member.display_avatar.replace(size=512).url
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


async def generate_fish_audio(text: str) -> bytes:
    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "reference_id": FISH_REFERENCE_ID,
        "format": "mp3",
        "latency": "normal",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Fish Audio Hatası ({response.status_code}): {response.text}")
        return response.content


def extract_text(response) -> str:
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()


def _usage_output(response) -> int:
    try:
        u = response.usage
        toplam = getattr(u, "output_tokens", 0) or 0
        for alan in ("reasoning_tokens", "thinking_tokens"):
            toplam += getattr(u, alan, 0) or 0
        return int(toplam)
    except Exception:
        return 0


# ---------- CLAUDE İÇİN ARAÇLAR (TOOLS) ----------

BASE_TOOLS = [
    {
        "name": "sunucu_uyesi_bul",
        "description": (
            "Discord sunucusundaki bir kişiyi ismine/etiketine göre arar ve profil "
            "bilgilerini döndürür. 'X kim', 'ben kimim', 'otto kimdir' gibi sorularda "
            "kullan. Kişinin kendisi için isim olarak 'ben' yaz."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"isim": {"type": "string", "description": "Aranan kişi. Kendisi için 'ben'."}},
            "required": ["isim"],
        },
    },
    {
        "name": "profil_fotografi_gonder",
        "description": (
            "Belirtilen kişinin profil fotoğrafını kanala gönderilmek üzere işaretler. "
            "Kullanıcı birinin fotoğrafını/avatarını istediğinde kullan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"isim": {"type": "string", "description": "Fotoğrafı istenen kişi. Kendisi için 'ben'."}},
            "required": ["isim"],
        },
    },
]

WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 3,
}


# ==========================================================================
# ==============  KOMUT ETİKETİ SİSTEMİ:  (/xxx0 ...)  =====================
# ==========================================================================
# Model, yapilmasini istedigi isi cevabinin sonuna etiket koyarak bildirir.
# Sistem etiketleri metinden TAMAMEN siler (yoksa Fish Audio sesli okur),
# temiz metni seslendirir, sonra isleri sirayla yapar.

_KOMUT_RE = re.compile(r"\(\s*/\s*([a-zA-ZçğıöşüÇĞİÖŞÜ]+)\s*0\s*([^)]*)\)", re.IGNORECASE)
# parantezi unutulmus hali icin yedek yakalayici
_KOMUT_RE_YEDEK = re.compile(
    r"/\s*(exit|muzik|müzik|dur|kimler|yayin|yayın|ara)\s*0\s*([^\n().]*)", re.IGNORECASE)

_KOMUT_ESLESME = {
    "exit": "exit", "cik": "exit", "çık": "exit",
    "muzik": "muzik", "müzik": "muzik", "music": "muzik",
    "dur": "dur", "stop": "dur",
    "kimler": "kimler", "kim": "kimler",
    "yayin": "yayin", "yayın": "yayin", "stream": "yayin",
    "ara": "ara", "search": "ara",
}


def komutlari_ayikla(ai_text: str):
    """
    (temiz_metin, [(komut, arguman), ...]) dondurur.
    Etiketler metinden tamamen silinir, yoksa Fish Audio onlari sesli okur.
    """
    if not ai_text:
        return ai_text, []

    t = ai_text.strip()
    komutlar = []

    def _topla(m):
        ad = _KOMUT_ESLESME.get(m.group(1).lower())
        if ad:
            komutlar.append((ad, (m.group(2) or "").strip()))
            return ""
        return m.group(0)   # taninmayan etiketi metinde birak

    t = _KOMUT_RE.sub(_topla, t)
    if not komutlar:
        t = _KOMUT_RE_YEDEK.sub(_topla, t)

    t = re.sub(r"\s{2,}", " ", t).strip(" \n\t,.-:!?")
    if komutlar and not t:
        t = "Tamamdır."
    return t, komutlar


# ==========================================================================
# ======================  MÜZİK ÇALAR  =====================================
# ==========================================================================

_muzik_durum = {"calan": None, "istendi": False}


def _muzik_dosya_bul(ad: str):
    """sesler/ klasorunde parca arar. Bos ad -> varsayilan."""
    ad = (ad or "").strip().lower()
    ad = re.sub(r"[^a-z0-9_\-çğıöşü ]", "", ad).strip()
    if not ad:
        ad = MUZIK_VARSAYILAN

    adaylar = [ad, ad.replace(" ", "_"), ad.replace(" ", "")]
    if not os.path.isdir(SES_KLASORU):
        return None

    dosyalar = [f for f in os.listdir(SES_KLASORU)
                if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a"))]
    # once tam eslesme
    for a in adaylar:
        for f in dosyalar:
            if os.path.splitext(f)[0].lower() == a:
                return os.path.join(SES_KLASORU, f)
    # sonra icinde gecen
    for a in adaylar:
        for f in dosyalar:
            if a and a in f.lower():
                return os.path.join(SES_KLASORU, f)
    # hicbiri yoksa varsayilani dene
    varsayilan = os.path.join(SES_KLASORU, MUZIK_VARSAYILAN + ".mp3")
    return varsayilan if os.path.exists(varsayilan) else None


def muzik_baslat(vc, ad: str = "") -> bool:
    """Muzigi baslatir. Beklemez (konusma araya girebilsin diye)."""
    if vc is None or not vc.is_connected():
        return False
    yol = _muzik_dosya_bul(ad)
    if not yol or not os.path.exists(yol):
        print(f"[MUZIK] Dosya bulunamadi: {ad!r} -> {yol!r}")
        return False
    try:
        if vc.is_playing():
            vc.stop()
        kaynak = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(yol), volume=MUZIK_SES_SEVIYESI
        )
        vc.play(kaynak, after=lambda e: print("[MUZIK] bitti", repr(e) if e else ""))
        _muzik_durum["calan"] = yol
        _muzik_durum["istendi"] = True
        print(f"[MUZIK] Caliyor: {yol}")
        return True
    except Exception as e:
        print("[MUZIK] baslatilamadi:", repr(e))
        return False


def muzik_durdur(vc, kalici=True) -> bool:
    if vc is None or not vc.is_connected():
        return False
    try:
        if vc.is_playing():
            vc.stop()
        if kalici:
            _muzik_durum["calan"] = None
            _muzik_durum["istendi"] = False
        print("[MUZIK] Durduruldu")
        return True
    except Exception as e:
        print("[MUZIK] durdurulamadi:", repr(e))
        return False


def muzik_devam(vc):
    """Konusma bittikten sonra muzik hala isteniyorsa tekrar baslat."""
    if _muzik_durum["istendi"] and _muzik_durum["calan"]:
        try:
            if vc and vc.is_connected() and not vc.is_playing():
                kaynak = discord.PCMVolumeTransformer(
                    discord.FFmpegPCMAudio(_muzik_durum["calan"]), volume=MUZIK_SES_SEVIYESI
                )
                vc.play(kaynak, after=lambda e: None)
                print("[MUZIK] Devam ediyor")
        except Exception as e:
            print("[MUZIK] devam ettirilemedi:", repr(e))


# ==========================================================================
# ==================  SES KANALI DURUM BİLGİSİ  ============================
# ==========================================================================

def _ses_kanali_al(guild=None):
    if guild is not None and guild.voice_client and guild.voice_client.channel:
        return guild.voice_client.channel
    for g in bot.guilds:
        if g.voice_client and g.voice_client.is_connected():
            return g.voice_client.channel
    return bot.get_channel(VOICE_CHANNEL_ID)


def kanal_durumu_metni(guild=None) -> str:
    """
    Modele verilecek: seste kimler var, kim susturulmus, kim yayin aciyor,
    kim ne oynuyor. Model bu bilgiyle isimleriyle hitap edebilir.
    """
    kanal = _ses_kanali_al(guild)
    if kanal is None or not hasattr(kanal, "members"):
        return "Ses kanali bilgisi alinamadi."

    satirlar = []
    yayinlayanlar = []
    for m in kanal.members:
        if bot.user and m.id == bot.user.id:
            continue
        durum = []
        vs = m.voice
        if vs:
            if vs.self_mute or vs.mute:
                durum.append("mikrofonu KAPALI")
            if vs.self_deaf or vs.deaf:
                durum.append("sesi kapali")
            if vs.self_stream:
                durum.append("EKRAN YAYINI ACIK")
                yayinlayanlar.append(m.display_name)
            if vs.self_video:
                durum.append("kamerasi acik")
        try:
            for act in (m.activities or []):
                ad = getattr(act, "name", None)
                if not ad:
                    continue
                tip = getattr(act, "type", None)
                if tip == discord.ActivityType.playing:
                    durum.append(f"'{ad}' oynuyor")
                elif tip == discord.ActivityType.listening:
                    durum.append(f"'{ad}' dinliyor")
                elif tip == discord.ActivityType.streaming:
                    durum.append(f"'{ad}' yayinliyor")
                break
        except Exception:
            pass

        satirlar.append(f"- {m.display_name} (@{m.name})" +
                        (" — " + ", ".join(durum) if durum else ""))

    if not satirlar:
        return f"'{kanal.name}' kanalinda senden baska kimse yok."

    metin = f"'{kanal.name}' ses kanalindakiler:\n" + "\n".join(satirlar)
    if yayinlayanlar:
        metin += "\nEKRAN YAYINI ACIK OLANLAR: " + ", ".join(yayinlayanlar)
    else:
        metin += "\nSu an ekran yayini acan kimse yok."
    return metin


def yayin_durumu_metni(guild=None) -> str:
    kanal = _ses_kanali_al(guild)
    if kanal is None or not hasattr(kanal, "members"):
        return "Ses kanali bilgisi alinamadi."

    yayinlar = []
    for m in kanal.members:
        if bot.user and m.id == bot.user.id:
            continue
        vs = m.voice
        if vs and (vs.self_stream or vs.self_video):
            ne = ""
            try:
                for act in (m.activities or []):
                    if getattr(act, "name", None):
                        ne = f" ('{act.name}' oynuyor)"
                        break
            except Exception:
                pass
            tur = "ekran yayini" if vs.self_stream else "kamera"
            yayinlar.append(f"{m.display_name} — {tur}{ne}")

    if not yayinlar:
        return "Su an kimse yayin acmiyor."
    if len(yayinlar) == 1:
        return ("Yayin acan tek kisi: " + yayinlar[0] +
                ". NOT: Yayinin goruntusunu goremiyorsun; ona ne oynadigini "
                "veya ne oldugunu sorup sohbet et.")
    return ("Yayin acanlar:\n- " + "\n- ".join(yayinlar) +
            "\nNOT: Yayinlarin goruntusunu goremiyorsun. Hangisine odaklanacagini SOR, "
            "sonra o kisiye ne oynadigini sorup sohbet et.")


# ---------- GENEL HATA YAKALAYICI ----------
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    traceback.print_exception(type(error), error, error.__traceback__)
    mesaj = f"⚠️ Komut çalışırken hata: `{error}`"
    try:
        if interaction.response.is_done():
            await interaction.followup.send(mesaj, ephemeral=True)
        else:
            await interaction.response.send_message(mesaj, ephemeral=True)
    except Exception:
        pass


@bot.event
async def on_ready():
    _limit_yukle()
    _ayar_yukle()
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi: {[c.name for c in synced]}")
    except Exception as e:
        print(f"Komut senkronize hatası: {e}")
    print(f"Veritan çevrimiçi! ({bot.user})")

    if not VOICE_HAZIR:
        print("[SES][UYARI] Sesli mod KAPALI. Sebep:", repr(VOICE_IMPORT_HATASI))
    else:
        print("[SES] Sesli mod hazir. /veritan_katil ile kanala sokabilirsin.")

    if os.path.isdir(SES_KLASORU):
        parcalar = [f for f in os.listdir(SES_KLASORU)
                    if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a"))]
        print(f"[MUZIK] '{SES_KLASORU}' klasorunde {len(parcalar)} parca: {parcalar[:10]}")
    else:
        print(f"[MUZIK][UYARI] '{SES_KLASORU}' klasoru yok, muzik calamaz.")

    if UI_CHANNEL_ID:
        print(f"[UI kanal] SABİT ID kullaniliyor: {UI_CHANNEL_ID}")
        kanal = bot.get_channel(UI_CHANNEL_ID)
        if kanal is None:
            try:
                kanal = await bot.fetch_channel(UI_CHANNEL_ID)
            except Exception as e:
                kanal = None
                print(f"[UI kanal][UYARI] Kanal BULUNAMADI: {e!r}")
        if kanal is not None:
            perms = None
            try:
                me = kanal.guild.me
                perms = kanal.permissions_for(me)
            except Exception:
                pass
            if perms is not None and not (perms.send_messages and perms.embed_links):
                print(f"[UI kanal][UYARI] #{getattr(kanal,'name',UI_CHANNEL_ID)} bulundu AMA izin eksik.")
            else:
                print(f"[UI kanal] OK -> #{getattr(kanal,'name',UI_CHANNEL_ID)} bulundu.")


async def claude_cevapla(messages, guild, asker, web_arama=False, system=SYSTEM_PROMPT, arac_kullan=True):
    tools = list(BASE_TOOLS) if arac_kullan else []
    if web_arama:
        tools = tools + [WEB_SEARCH_TOOL]

    gonderilecek_fotograflar = []
    response = None
    uretilen_token = 0

    for _ in range(4):
        try:
            kwargs = dict(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=messages,
            )
            if tools:
                kwargs["tools"] = tools
            response = await anthropic_client.messages.create(**kwargs)
        except Exception as api_err:
            print("API hatasi, araclar olmadan tekrar deneniyor:", repr(api_err))
            response = await anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=messages,
            )
            uretilen_token += _usage_output(response)
            break

        uretilen_token += _usage_output(response)

        if response.stop_reason != "tool_use":
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in response.content:
            if block.type != "tool_use":
                continue

            if block.name == "sunucu_uyesi_bul":
                isim = block.input.get("isim", "")
                bulunanlar = await uye_ara(guild, isim, asker)
                if bulunanlar:
                    metin = "\n".join(describe_member(m) for m in bulunanlar)
                else:
                    metin = f"'{isim}' bulunamadi."
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": metin})

            elif block.name == "profil_fotografi_gonder":
                isim = block.input.get("isim", "")
                bulunanlar = await uye_ara(guild, isim, asker, limit=1)
                if bulunanlar:
                    m = bulunanlar[0]
                    try:
                        foto = await avatar_indir(m)
                        gonderilecek_fotograflar.append((f"{m.name}.png", foto))
                        not_ = f"{m.display_name} profil fotografi gonderilecek."
                    except Exception as e:
                        not_ = f"Fotograf indirilemedi: {e}"
                else:
                    not_ = f"'{isim}' bulunamadi, fotograf gonderilemedi."
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": not_})

        if not tool_results:
            break
        messages.append({"role": "user", "content": tool_results})

    return response, gonderilecek_fotograflar, uretilen_token


async def veritan_calistir(interaction, message, dosya, web_arama):
    try:
        await interaction.response.defer()
    except discord.NotFound:
        print("[UYARI] Interaction zaman asimina ugradi (10062), komut atlandi.")
        return
    except Exception as e:
        print("[UYARI] defer hatasi:", repr(e))
        return

    asker = interaction.user

    kalan, limit, reset_at, izin = limit_kontrol(asker.id)
    if not izin:
        await interaction.followup.send(
            content="🚫 Hak bakiyen bitti! Yenilenince tekrar sorabilirsin.",
            embed=limit_embed(asker, 0, limit, reset_at),
        )
        return

    try:
        guild = interaction.guild

        baglam = (
            f"[Soruyu soran kişi] {describe_member(asker)}\n"
            f"[Sunucu] {guild.name if guild else 'Özel mesaj'}\n\n"
            f"Mesaj: {message}"
        )
        user_content = [{"type": "text", "text": baglam}]

        if dosya is not None:
            ctype = dosya.content_type or ""
            if ctype.startswith("image/"):
                img_bytes = await dosya.read()
                user_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": ctype,
                        "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                    },
                })
                user_content.append({"type": "text", "text": "(Kullanıcı yukarıdaki resmi ekledi.)"})
            else:
                user_content.append({"type": "text", "text": f"(Kullanıcı bir dosya ekledi: {dosya.filename})"})

        messages = [{"role": "user", "content": user_content}]

        response, fotograflar, uretilen_token = await claude_cevapla(messages, guild, asker, web_arama=web_arama)

        ai_text = extract_text(response) if response else ""
        if not ai_text:
            ai_text = "Üzgünüm, bir cevap üretemedim."

        # Yazili komutta etiketler anlamsiz; gelirse sadece temizle.
        ai_text, _ = komutlari_ayikla(ai_text)

        maliyet = uretilen_token * TOKEN_MALIYETI
        yeni_kalan = limit_harca(asker.id, maliyet)

        vc = guild.voice_client if guild else None
        kanal_id = interaction.channel.id if interaction.channel else None
        ses_kanalinin_sohbeti = (
            vc is not None and vc.is_connected() and kanal_id == VOICE_CHANNEL_ID
        )
        print(f"[SES] /komut kanal={kanal_id} hedef_ses_kanali={VOICE_CHANNEL_ID} "
              f"bot_seste={bool(vc and vc.is_connected())} -> canli_ses={ses_kanalinin_sohbeti}")

        if ses_kanalinin_sohbeti:
            files = []
            for fname, fbytes in fotograflar:
                files.append(discord.File(io.BytesIO(fbytes), filename=fname))
            if files:
                await interaction.followup.send(content="🔊 Cevap ses kanalında oynatılıyor...", files=files)
            else:
                await interaction.followup.send(content="🔊 Cevap ses kanalında oynatılıyor...")
            try:
                await _seslendir_ve_cal(vc, ai_text)
                muzik_devam(vc)
            except Exception as e:
                print("[SES] metin-sohbet -> ses oynatma hatasi:", repr(e))
                audio_bytes = await generate_fish_audio(ai_text)
                await interaction.followup.send(
                    files=[discord.File(io.BytesIO(audio_bytes), filename="veritan.mp3")]
                )
        else:
            audio_bytes = await generate_fish_audio(ai_text)
            files = [discord.File(io.BytesIO(audio_bytes), filename="veritan.mp3")]
            for fname, fbytes in fotograflar:
                files.append(discord.File(io.BytesIO(fbytes), filename=fname))
            await interaction.followup.send(files=files)

        embed = limit_embed(asker, yeni_kalan, limit, reset_at, son_token=uretilen_token, son_hak=maliyet)
        gonderildi, hata_sebebi = await _ui_kart_garanti_gonder(embed)

        if not gonderildi:
            try:
                await interaction.followup.send(
                    f"⚠️ Hak kartı sabit UI kanalına gönderilemedi.\n**Sebep:** {hata_sebebi}",
                    ephemeral=True,
                )
            except Exception:
                pass

    except Exception as e:
        traceback.print_exc()
        try:
            await interaction.followup.send(f"Bir hata oluştu: `{str(e)}`", ephemeral=True)
        except Exception:
            pass


# ---------- KULLANICI KOMUTLARI ----------

@bot.tree.command(name="veritan", description="Veritan ile konuşun (hızlı, internetsiz; yanıt MP3).")
@app_commands.describe(
    message="Veritan'a iletmek istediğiniz mesaj",
    dosya="(İsteğe bağlı) Resim/dosya ekleyebilirsin.",
)
async def veritan_command(interaction: discord.Interaction, message: str, dosya: discord.Attachment = None):
    await veritan_calistir(interaction, message, dosya, web_arama=False)


@bot.tree.command(name="veritan_search", description="Veritan internette arayarak cevap verir (biraz yavaş; yanıt MP3).")
@app_commands.describe(
    message="İnternette aratmak istediğiniz mesaj",
    dosya="(İsteğe bağlı) Resim/dosya ekleyebilirsin.",
)
async def veritan_search_command(interaction: discord.Interaction, message: str, dosya: discord.Attachment = None):
    await veritan_calistir(interaction, message, dosya, web_arama=True)


# ---------- YÖNETİCİ KOMUTLARI ----------

@bot.tree.command(
    name="limitresetveritan",
    description="(Sadece yetkili) Bir kullanıcının hak bakiyesini istediğin değere ayarlar.",
)
@app_commands.describe(
    kullanici="Bakiyesi ayarlanacak kişi",
    limit="Verilecek hak miktarı (ondalık olabilir: 5, 25, 0.5, 100...)",
)
async def limitreset_command(
    interaction: discord.Interaction,
    kullanici: discord.Member,
    limit: app_commands.Range[float, 0.0, 1000000.0],
):
    await interaction.response.defer(ephemeral=True)
    if not yetkili_mi(interaction.user):
        await interaction.followup.send(
            f"⛔ Sadece yetkili kullanabilir. (Sen → `{interaction.user.name}`, ID: `{interaction.user.id}`)",
            ephemeral=True,
        )
        return

    rec = limit_resetle(kullanici.id, limit)
    await interaction.followup.send(
        content=f"✅ {kullanici.display_name} için hak bakiyesi **{float(limit):.2f}** olarak ayarlandı.",
        embed=limit_embed(kullanici, rec["kalan"], rec["limit"], rec["reset_at"]),
    )


@bot.tree.command(
    name="whereisuiveritan",
    description="(Sadece yetkili) UI kanalı SABİT olduğu için artık sadece bilgi verir.",
)
async def whereisui_command(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not yetkili_mi(interaction.user):
        await interaction.followup.send(
            f"⛔ Sadece yetkili kullanabilir. (Sen → `{interaction.user.name}`, ID: `{interaction.user.id}`)",
            ephemeral=True,
        )
        return

    if UI_CHANNEL_ID:
        await interaction.followup.send(
            f"ℹ️ UI kanalı **koda sabitlenmiş** durumda (ID: `{UI_CHANNEL_ID}`). "
            f"Değiştirmek için koddaki `UI_CHANNEL_ID` değerini düzenle.",
            ephemeral=True,
        )
        return

    if interaction.guild is None:
        await interaction.followup.send("Bu komut sadece sunucuda çalışır.", ephemeral=True)
        return

    hedef_kanal = interaction.channel
    ui_kanal_ayarla(interaction.guild.id, hedef_kanal.id)
    embed = discord.Embed(
        title="✅ UI Kanalı Ayarlandı",
        description=f"Bu kanal seçildi: {hedef_kanal.mention}",
        color=0x2ecc71,
    )
    try:
        await hedef_kanal.send(embed=embed)
        await interaction.followup.send(f"✅ Ayarlandı. Kartlar {hedef_kanal.mention} kanalına gidecek.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"⚠️ Kanal kaydedildi ama buraya yazamıyorum. Hata: `{e}`", ephemeral=True)


# ==========================================================================
# ============================ SESLİ MOD (VOICE) ===========================
# ==========================================================================
# Gerekli: discord-ext-voice-recv, deepgram-sdk==3.7.0, PyNaCl, FFmpeg, libopus

VOICE_HAZIR = True
VOICE_IMPORT_HATASI = None
try:
    from discord.ext import voice_recv
    from deepgram import (
        DeepgramClient,
        DeepgramClientOptions,
        LiveTranscriptionEvents,
        LiveOptions,
    )
except Exception as _e:
    VOICE_HAZIR = False
    VOICE_IMPORT_HATASI = _e
    print("[SES] Sesli mod kutuphaneleri yuklenemedi:", repr(_e))


# ==========================================================================
# KRITIK YAMA: "OpusError: corrupted stream" router thread'ini olduruyor.
# ==========================================================================
if VOICE_HAZIR:
    try:
        from discord.ext.voice_recv.opus import PacketDecoder as _PD
        import discord.opus as _dopus

        _orijinal_pop = _PD.pop_data
        _bozuk_sayaci = {"n": 0}
        _basarili_sayaci = {"n": 0}

        def _guvenli_pop(self, *args, **kwargs):
            try:
                sonuc = _orijinal_pop(self, *args, **kwargs)
                if sonuc is not None:
                    _basarili_sayaci["n"] += 1
                    if _basarili_sayaci["n"] in (1, 5, 50) or _basarili_sayaci["n"] % 500 == 0:
                        print(f"[SES][YAMA] PCM uretildi ve sink'e gidiyor (toplam {_basarili_sayaci['n']})")
                return sonuc
            except _dopus.OpusError:
                _bozuk_sayaci["n"] += 1
                if _bozuk_sayaci["n"] in (1, 10, 100) or _bozuk_sayaci["n"] % 500 == 0:
                    print(f"[SES][YAMA] Bozuk ses paketi atlandi (toplam {_bozuk_sayaci['n']}) - dinleme DEVAM ediyor")
                return None
            except Exception as e:
                print("[SES][YAMA] Beklenmeyen decoder hatasi, paket atlandi:", repr(e))
                return None

        _PD.pop_data = _guvenli_pop
        print("[SES][YAMA] Opus decoder koruma yamasi aktif (corrupted stream artik oldurmez).")
    except Exception as _pe:
        print("[SES][YAMA] Yama uygulanamadi:", repr(_pe))


async def _seslendir_ve_cal(voice_client, text: str):
    audio_bytes = await generate_fish_audio(text)
    yol = f"/tmp/veritan_{datetime.now().timestamp()}.mp3"
    with open(yol, "wb") as f:
        f.write(audio_bytes)
    await _dosya_cal(voice_client, yol, sil=True)


async def _dosya_cal(voice_client, dosya_yolu: str, sil=False):
    if voice_client is None or not voice_client.is_connected():
        return
    # konusma muzigin onune gecer
    if voice_client.is_playing():
        voice_client.stop()
        await asyncio.sleep(0.15)

    bitti = asyncio.Event()

    def _after(err):
        if err:
            print("[SES] Calma hatasi:", repr(err))
        try:
            bot.loop.call_soon_threadsafe(bitti.set)
        except Exception:
            pass

    try:
        kaynak = discord.FFmpegPCMAudio(dosya_yolu)
        voice_client.play(kaynak, after=_after)
        await bitti.wait()
    except Exception as e:
        print("[SES] play hatasi:", repr(e))
    finally:
        if sil:
            try:
                os.remove(dosya_yolu)
            except Exception:
                pass


async def _sesli_cevap_uret(kullanici, metin, guild, ek_baglam=""):
    uid = getattr(kullanici, "id", None)
    if uid is not None:
        kalan, limit, reset_at, izin = limit_kontrol(uid)
        if not izin:
            return None, 0, limit, reset_at, 0, 0.0, False
    else:
        kalan, limit, reset_at = 0.0, DAILY_LIMIT, datetime.now(timezone.utc)

    baglam = (
        f"[Seninle konusan kisi] {describe_member(kullanici)}\n"
        f"[Ortam] Sesli sohbet kanali\n"
        f"[Ses kanali durumu]\n{kanal_durumu_metni(guild)}\n"
    )
    if _muzik_durum["istendi"]:
        baglam += "[Muzik] Su an muzik caliyor.\n"
    if ek_baglam:
        baglam += f"\n{ek_baglam}\n"
    baglam += f"\nKisinin soyledigi: {metin}"

    messages = [{"role": "user", "content": [{"type": "text", "text": baglam}]}]
    response, _foto, uretilen_token = await claude_cevapla(
        messages, guild, kullanici, web_arama=False, system=SYSTEM_PROMPT2
    )
    ai_text = extract_text(response) if response else ""
    if not ai_text:
        ai_text = "Pardon, bir an dalmisim. Tekrar eder misin?"

    giris_token_tahmini = max(1, len(baglam) // 4)
    toplam_token = uretilen_token + giris_token_tahmini
    maliyet = toplam_token * TOKEN_MALIYETI
    yeni_kalan = limit_harca(uid, maliyet)
    return ai_text, yeni_kalan, limit, reset_at, toplam_token, maliyet, True


async def web_arastir_ve_anlat(sorgu: str, kullanici=None, guild=None):
    """(/ara0 ...) etiketi geldiginde: internetten bak, sonucu konusma diliyle dondur."""
    try:
        messages = [{"role": "user", "content": [{"type": "text", "text":
            f"Su konuyu internetten arastir ve sesli sohbette anlatilacak sekilde "
            f"cok kisa (en fazla 3 cumle) ozetle: {sorgu}"}]}]
        response, _f, token = await claude_cevapla(
            messages, guild, kullanici, web_arama=True,
            system=SYSTEM_PROMPT_ARAMA, arac_kullan=False,
        )
        metin = extract_text(response) if response else ""
        metin, _ = komutlari_ayikla(metin)
        if not metin:
            metin = "Aradim ama net bir sey bulamadim maalesef."
        limit_harca(getattr(kullanici, "id", None), (token + len(sorgu) // 4) * TOKEN_MALIYETI)
        return metin
    except Exception as e:
        print("[ARA] hata:", repr(e))
        traceback.print_exc()
        return "Aramaya calistim ama bir sorun cikti."


async def _ui_kart_gonder(kullanici, yeni_kalan, limit, reset_at, token, maliyet):
    if kullanici is None:
        return
    embed = limit_embed(kullanici, yeni_kalan, limit, reset_at, son_token=token, son_hak=maliyet)
    gonderildi, hata = await _ui_kart_garanti_gonder(embed)
    if not gonderildi:
        print("[SES][UI kanal] kart gonderilemedi:", hata)


async def _konusmayi_bitir_ve_ayril(vc, motor=None):
    """Calan ses TAMAMEN bitene kadar bekler, sonra kanaldan cikar."""
    try:
        while vc is not None and vc.is_connected() and vc.is_playing():
            await asyncio.sleep(0.2)
        await asyncio.sleep(0.5)
    except Exception:
        pass

    muzik_durdur(vc, kalici=True)
    try:
        if motor is not None:
            motor.calisiyor = False
            for oturum in list(motor.oturumlar.values()):
                try:
                    oturum.kapat()
                except Exception:
                    pass
            motor.oturumlar.clear()
        if vc is not None and vc.is_connected():
            await vc.disconnect()
        print("[EXIT0] Ses kanalindan cikildi.")
    except Exception as e:
        print("[EXIT0] cikis hatasi:", repr(e))


# ---- Deepgram canli dinleyici (kisi basina) — SENKRON websocket ----
class _DeepgramOturum:
    def __init__(self, kullanici, motor):
        self.kullanici = kullanici
        self.motor = motor
        self.dg_conn = None
        self.uyanik = False
        self.uyanma_zamani = None
        self.aktif = False

    def baslat(self):
        """SENKRON: sink thread'inden cagrilir."""
        try:
            cfg = DeepgramClientOptions(options={"keepalive": "true"})
            dg = DeepgramClient(DEEPGRAM_API_KEY, cfg)
            self.dg_conn = dg.listen.websocket.v("1")

            def on_message(_self, result, **kwargs):
                try:
                    cumle = result.channel.alternatives[0].transcript
                except Exception:
                    return
                if not cumle or not result.is_final:
                    return
                try:
                    asyncio.run_coroutine_threadsafe(
                        self.motor.metin_geldi(self.kullanici, cumle.strip()),
                        bot.loop,
                    )
                except Exception as e:
                    print("[SES] transcript aktarilamadi:", repr(e))

            def on_error(_self, error, **kwargs):
                print(f"[SES] Deepgram HATA ({self.kullanici.display_name}):", error)

            def on_open(_self, *a, **k):
                print(f"[SES] Deepgram baglanti ACILDI ({self.kullanici.display_name})")

            def on_close(_self, *a, **k):
                print(f"[SES] Deepgram baglanti KAPANDI ({self.kullanici.display_name})")
                self.aktif = False

            self.dg_conn.on(LiveTranscriptionEvents.Transcript, on_message)
            self.dg_conn.on(LiveTranscriptionEvents.Error, on_error)
            try:
                self.dg_conn.on(LiveTranscriptionEvents.Open, on_open)
                self.dg_conn.on(LiveTranscriptionEvents.Close, on_close)
            except Exception:
                pass

            opts = LiveOptions(
                model="nova-2",
                language="tr",
                encoding="linear16",
                sample_rate=48000,
                channels=2,          # Discord PCM = 48kHz stereo
                punctuate=True,
                interim_results=False,
                endpointing=300,
            )
            ok = self.dg_conn.start(opts)
            self.aktif = bool(ok)
            print(f"[SES] Deepgram baslatildi ({self.kullanici}) ok={ok}")
        except Exception as e:
            print(f"[SES] Deepgram baslatilamadi ({self.kullanici}):", repr(e))
            traceback.print_exc()
            self.dg_conn = None
            self.aktif = False

    def ses_gonder(self, pcm_bytes):
        if self.dg_conn is not None and self.aktif:
            try:
                self.dg_conn.send(pcm_bytes)
            except Exception as e:
                print("[SES] Deepgram'a ses gonderilemedi:", repr(e))

    def kapat(self):
        if self.dg_conn is not None:
            try:
                self.dg_conn.finish()
            except Exception:
                pass
            self.dg_conn = None
            self.aktif = False


class VeritanSesMotoru:
    def __init__(self, voice_client, guild):
        self.vc = voice_client
        self.guild = guild
        self.oturumlar = {}
        self.aktif_konusan = None
        self.mesgul = False
        self.calisiyor = True
        self.son_konusma = {}     # user_id -> son konustugu an
        self.son_durtme = {}      # user_id -> son laf atilan an
        self.odak_yayinci = None  # uzerine konusulan yayinci

    def _wake_var_mi(self, cumle):
        dusuk = cumle.lower()
        return any(w in dusuk for w in WAKE_WORDS)

    def _wake_temizle(self, cumle):
        dusuk = cumle.lower()
        for w in WAKE_WORDS:
            idx = dusuk.find(w)
            if idx != -1:
                return cumle[idx + len(w):].strip(" ,.-:!?")
        return cumle.strip()

    def oturum_ac_sync(self, kullanici):
        mevcut = self.oturumlar.get(kullanici.id)
        if mevcut is not None:
            return mevcut

        oturum = _DeepgramOturum(kullanici, self)
        self.oturumlar[kullanici.id] = oturum

        t = threading.Thread(target=oturum.baslat, name=f"dg-start-{kullanici.id}", daemon=True)
        t.start()
        return oturum

    async def metin_geldi(self, kullanici, cumle):
        print(f"[SES] TRANSCRIPT ({kullanici.display_name}): {cumle}")
        self.son_konusma[kullanici.id] = datetime.now()

        oturum = self.oturumlar.get(kullanici.id)
        wake = self._wake_var_mi(cumle)

        if self.mesgul:
            print(f"[SES] mesgul, simdilik yok sayildi ({kullanici.display_name})")
            return

        if oturum and oturum.uyanik:
            gecti = (datetime.now() - oturum.uyanma_zamani).total_seconds() if oturum.uyanma_zamani else 999
            if gecti > DINLEME_PENCERESI_SN:
                oturum.uyanik = False
                print(f"[SES] {kullanici.display_name} icin dinleme penceresi doldu")
            else:
                oturum.uyanik = False
                soru = self._wake_temizle(cumle) if wake else cumle
                print(f"[SES] Odakli cevap -> {kullanici.display_name}: {soru}")
                await self._cevapla(kullanici, soru)
                return

        if wake:
            kalan_metin = self._wake_temizle(cumle)
            self.aktif_konusan = kullanici.id
            if kalan_metin:
                print(f"[SES] Wake+soru -> {kullanici.display_name}: {kalan_metin}")
                await self._cevapla(kullanici, kalan_metin)
            else:
                print(f"[SES] Wake (sadece isim) -> {kullanici.display_name}, dinliyorum calinacak")
                if oturum:
                    oturum.uyanik = True
                    oturum.uyanma_zamani = datetime.now()
                await self._dinliyorum_cal()
            return

    async def _dinliyorum_cal(self):
        self.mesgul = True
        try:
            if os.path.exists(MP3_DINLIYORUM):
                await _dosya_cal(self.vc, MP3_DINLIYORUM, sil=False)
            else:
                await _seslendir_ve_cal(self.vc, "Seni dinliyorum.")
        except Exception as e:
            print("[SES] dinliyorum calinamadi:", repr(e))
        finally:
            self.mesgul = False

    # ---------------- KOMUT ETİKETLERİNİ UYGULA ----------------
    async def komutlari_uygula(self, komutlar, kullanici):
        """
        Modelin verdigi etiketleri sirayla calistirir.
        True donerse kanaldan cikildi demektir.
        """
        for komut, arg in komutlar:
            try:
                if komut == "exit":
                    print(f"[KOMUT] exit0 -> cikiliyor ({getattr(kullanici,'display_name','?')})")
                    await _konusmayi_bitir_ve_ayril(self.vc, motor=self)
                    return True

                elif komut == "muzik":
                    print(f"[KOMUT] muzik0 arg={arg!r}")
                    if not muzik_baslat(self.vc, arg):
                        await _seslendir_ve_cal(
                            self.vc, "Parcayi bulamadim, sesler klasorunde yok galiba."
                        )

                elif komut == "dur":
                    print("[KOMUT] dur0")
                    muzik_durdur(self.vc, kalici=True)

                elif komut == "kimler":
                    print("[KOMUT] kimler0")
                    await self._durum_anlat(
                        kullanici, kanal_durumu_metni(self.guild),
                        "Seste kimler var, kisa ve sohbet dilinde soyle.")

                elif komut == "yayin":
                    print("[KOMUT] yayin0")
                    await self._durum_anlat(
                        kullanici, yayin_durumu_metni(self.guild),
                        "Yayin durumunu kisaca soyle. Birden fazla yayinci varsa hangisine "
                        "odaklanacagini SOR. Yayinin goruntusunu gordugunu ASLA iddia etme.")

                elif komut == "ara":
                    sorgu = arg or ""
                    print(f"[KOMUT] ara0 -> {sorgu!r}")
                    if not sorgu:
                        continue
                    sonuc = await web_arastir_ve_anlat(sorgu, kullanici, self.guild)
                    await _seslendir_ve_cal(self.vc, sonuc)

            except Exception as e:
                print(f"[KOMUT] '{komut}' calistirilamadi:", repr(e))
                traceback.print_exc()

        muzik_devam(self.vc)
        return False

    async def _durum_anlat(self, kullanici, durum_metni, yonerge):
        """Kanal/yayin durumunu modele verip konusma diliyle soylettirir."""
        try:
            messages = [{"role": "user", "content": [{"type": "text", "text":
                f"[Ses kanali bilgisi]\n{durum_metni}\n\n[Gorev] {yonerge}"}]}]
            response, _f, token = await claude_cevapla(
                messages, self.guild, kullanici, web_arama=False,
                system=SYSTEM_PROMPT2, arac_kullan=False,
            )
            metin = extract_text(response) if response else ""
            metin, _ = komutlari_ayikla(metin)
            if metin:
                await _seslendir_ve_cal(self.vc, metin)
            limit_harca(getattr(kullanici, "id", None), token * TOKEN_MALIYETI)
        except Exception as e:
            print("[DURUM] anlatilamadi:", repr(e))

    async def _cevapla(self, kullanici, metin, ek_baglam=""):
        self.mesgul = True
        self.aktif_konusan = getattr(kullanici, "id", None)
        try:
            (ai_text, yeni_kalan, limit, reset_at,
             token, maliyet, hak_var) = await _sesli_cevap_uret(
                kullanici, metin, self.guild, ek_baglam=ek_baglam)

            if not hak_var:
                if os.path.exists(MP3_HAK_BITTI):
                    await _dosya_cal(self.vc, MP3_HAK_BITTI, sil=False)
                else:
                    await _seslendir_ve_cal(self.vc, "Hakkın bitti, üzgünüm.")
                return

            # --- Model etiketle is istedi mi? ---
            ai_text, komutlar = komutlari_ayikla(ai_text)
            if komutlar:
                print(f"[KOMUT] Model istedi: {komutlar}")

            await _seslendir_ve_cal(self.vc, ai_text)
            await _ui_kart_gonder(kullanici, yeni_kalan, limit, reset_at, token, maliyet)

            if komutlar:
                cikildi = await self.komutlari_uygula(komutlar, kullanici)
                if cikildi:
                    return
            else:
                muzik_devam(self.vc)

        except Exception as e:
            print("[SES] cevap uretilemedi:", repr(e))
            traceback.print_exc()
        finally:
            self.mesgul = False
            self.aktif_konusan = None

    # ---------------- SESSİZ ÜYE DÜRTMESİ ----------------
    async def sessizlik_bekcisi(self):
        """
        SESSIZ_DAKIKA boyunca konusmayan VEYA mikrofonu kapali olan kisiye
        adiyla seslenip laf atar. Cumleyi model uretir, Fish Audio seslendirir.
        """
        await asyncio.sleep(20)
        while self.calisiyor:
            try:
                await asyncio.sleep(SESSIZ_KONTROL_SN)
                if not self.calisiyor or self.mesgul:
                    continue
                if self.vc is None or not self.vc.is_connected():
                    continue

                kanal = self.vc.channel
                if kanal is None or len(getattr(kanal, "members", [])) <= 1:
                    continue

                simdi = datetime.now()
                adaylar = []
                for m in kanal.members:
                    if bot.user and m.id == bot.user.id:
                        continue
                    vs = m.voice
                    mikrofon_kapali = bool(vs and (vs.self_mute or vs.mute))
                    son = self.son_konusma.get(m.id)
                    suskun_dk = (simdi - son).total_seconds() / 60 if son else 999

                    # ilk kez goruyorsak kayit at, hemen laf atma
                    if son is None:
                        self.son_konusma[m.id] = simdi
                        continue

                    if not (mikrofon_kapali or suskun_dk >= SESSIZ_DAKIKA):
                        continue

                    son_durtme = self.son_durtme.get(m.id)
                    if son_durtme and (simdi - son_durtme).total_seconds() / 60 < SESSIZ_TEKRAR_DK:
                        continue

                    adaylar.append((m, mikrofon_kapali, suskun_dk))

                if not adaylar:
                    continue

                hedef, mik_kapali, suskun_dk = random.choice(adaylar)
                self.son_durtme[hedef.id] = simdi
                print(f"[DURTME] {hedef.display_name} (mik_kapali={mik_kapali}, suskun={suskun_dk:.1f}dk)")

                sebep = ("mikrofonu kapali" if mik_kapali
                         else f"{int(min(suskun_dk, 99))} dakikadir hic konusmuyor")
                gorev = (
                    f"[Gorev] Ses kanalindaki '{hedef.display_name}' adli kisi {sebep}. "
                    f"Ona ADIYLA seslenip tatli-sert, esprili bir laf at; neden sessiz oldugunu sor. "
                    f"TEK cumle, kisa. Kirici olma, samimi ol. Etiket KOYMA."
                )
                await self._durtme_konus(gorev, hedef)

            except Exception as e:
                print("[DURTME] hata:", repr(e))

    async def _durtme_konus(self, gorev, hedef):
        self.mesgul = True
        try:
            messages = [{"role": "user", "content": [{"type": "text", "text":
                f"[Ses kanali durumu]\n{kanal_durumu_metni(self.guild)}\n\n{gorev}"}]}]
            response, _f, _t = await claude_cevapla(
                messages, self.guild, hedef, web_arama=False,
                system=SYSTEM_PROMPT2, arac_kullan=False,
            )
            metin = extract_text(response) if response else ""
            metin, _ = komutlari_ayikla(metin)
            if metin:
                await _seslendir_ve_cal(self.vc, metin)
                muzik_devam(self.vc)
        except Exception as e:
            print("[DURTME] konusulamadi:", repr(e))
        finally:
            self.mesgul = False


# ---- Discord'dan ham PCM alan sink ----
if VOICE_HAZIR:
    class VeritanSink(voice_recv.AudioSink):
        def __init__(self, motor):
            super().__init__()
            self.motor = motor
            self._ilk_ses_loglandi = set()
            self._paket_sayaci = {}

        def wants_opus(self) -> bool:
            return False  # PCM (48kHz stereo 16-bit)

        def write(self, user, data):
            try:
                if not hasattr(self, "_write_log_n"):
                    self._write_log_n = 0
                self._write_log_n += 1
                if self._write_log_n in (1, 2, 3, 10, 50):
                    print(f"[SES][SINK] write() cagrildi #{self._write_log_n} "
                          f"user_tipi={type(user).__name__} user={user}")
            except Exception:
                pass

            if user is None:
                return
            if not hasattr(user, "id"):
                return
            try:
                if bot.user and user.id == bot.user.id:
                    return
            except Exception:
                pass

            pcm = getattr(data, "pcm", None)
            if not pcm:
                return

            if user.id not in self._ilk_ses_loglandi:
                self._ilk_ses_loglandi.add(user.id)
                print(f"[SES][SINK] Ilk ses paketi geldi -> "
                      f"{getattr(user,'display_name',user.id)} ({user.id}), {len(pcm)} byte")

            self._paket_sayaci[user.id] = self._paket_sayaci.get(user.id, 0) + 1
            if self._paket_sayaci[user.id] % 250 == 0:
                print(f"[SES][SINK] {getattr(user,'display_name',user.id)}: "
                      f"{self._paket_sayaci[user.id]} paket")

            oturum = self.motor.oturumlar.get(user.id)
            if oturum is None:
                oturum = self.motor.oturum_ac_sync(user)
            oturum.ses_gonder(pcm)

        def cleanup(self):
            pass


# ---- Yayin acilinca haberdar ol ----
@bot.event
async def on_voice_state_update(member, before, after):
    try:
        motor = getattr(bot, "_veritan_motor", None)
        if motor is None or not motor.calisiyor:
            return
        if bot.user and member.id == bot.user.id:
            return
        vc = motor.vc
        if vc is None or not vc.is_connected() or vc.channel is None:
            return
        if after.channel is None or after.channel.id != vc.channel.id:
            return

        if after.self_stream and not before.self_stream:
            print(f"[YAYIN] {member.display_name} yayin acti")
            motor.son_konusma.setdefault(member.id, datetime.now())
    except Exception as e:
        print("[YAYIN] durum guncellemesi hatasi:", repr(e))


# ---- SESLİ KOMUTLAR ----

@bot.tree.command(name="veritan_katil", description="(Sadece yetkili) Veritan'ı sabit ses kanalına sokar.")
async def veritan_katil(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not yetkili_mi(interaction.user):
        await interaction.followup.send("⛔ Sadece yetkili kullanabilir.", ephemeral=True)
        return
    if not VOICE_HAZIR:
        await interaction.followup.send(
            f"⚠️ Sesli mod kütüphaneleri yüklü değil.\nDetay: `{VOICE_IMPORT_HATASI}`",
            ephemeral=True,
        )
        return
    if interaction.guild is None:
        await interaction.followup.send("Bu komut sadece sunucuda çalışır.", ephemeral=True)
        return

    kanal = bot.get_channel(VOICE_CHANNEL_ID)
    if kanal is None:
        try:
            kanal = await bot.fetch_channel(VOICE_CHANNEL_ID)
        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Ses kanalı bulunamadı (ID: {VOICE_CHANNEL_ID}). `{e}`", ephemeral=True)
            return
    if not isinstance(kanal, (discord.VoiceChannel, discord.StageChannel)):
        await interaction.followup.send("⚠️ Verilen ID bir SES/SAHNE kanalı değil.", ephemeral=True)
        return

    if interaction.guild.voice_client and interaction.guild.voice_client.is_connected():
        await interaction.followup.send("ℹ️ Veritan zaten ses kanalında.", ephemeral=True)
        return

    try:
        vc = await kanal.connect(cls=voice_recv.VoiceRecvClient)
        motor = VeritanSesMotoru(vc, interaction.guild)
        vc.listen(VeritanSink(motor))
        bot._veritan_motor = motor
        print(f"[SES] Dinleme basladi -> {kanal.name} ({kanal.id})")

        # sessizlik bekcisini baslat
        asyncio.create_task(motor.sessizlik_bekcisi())

        async def _onden_oturumlari_ac():
            try:
                uyeler = [u for u in kanal.members if not (bot.user and u.id == bot.user.id)]
                for uye in uyeler:
                    await asyncio.to_thread(motor.oturum_ac_sync, uye)
                print(f"[SES] Onden acilan oturum sayisi: {len(motor.oturumlar)}")
            except Exception as e:
                print("[SES] Onden oturum acilamadi:", repr(e))

        asyncio.create_task(_onden_oturumlari_ac())

        await interaction.followup.send(
            f"✅ Veritan **{kanal.name}** kanalına girdi ve dinlemede. 🎙️\n"
            f"Yapabildikleri: müzik çal/durdur, seste kim var söyler, kim yayın açmış söyler, "
            f"internetten arayıp cevaplar, çık dediğinde çıkar. "
            f"{SESSIZ_DAKIKA} dk susan veya mikrofonu kapalı olana adıyla laf atar.",
            ephemeral=True,
        )
    except Exception as e:
        traceback.print_exc()
        await interaction.followup.send(f"⚠️ Ses kanalına girilemedi: `{e}`", ephemeral=True)


@bot.tree.command(name="veritan_ayril", description="(Sadece yetkili) Veritan'ı ses kanalından çıkarır.")
async def veritan_ayril(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    if not yetkili_mi(interaction.user):
        await interaction.followup.send("⛔ Sadece yetkili kullanabilir.", ephemeral=True)
        return
    vc = interaction.guild.voice_client if interaction.guild else None
    if vc and vc.is_connected():
        try:
            motor = getattr(bot, "_veritan_motor", None)
            if motor:
                motor.calisiyor = False
                for oturum in list(motor.oturumlar.values()):
                    oturum.kapat()
            muzik_durdur(vc, kalici=True)
            await vc.disconnect()
        except Exception:
            pass
        await interaction.followup.send("👋 Veritan ses kanalından ayrıldı.", ephemeral=True)
    else:
        await interaction.followup.send("ℹ️ Veritan zaten ses kanalında değil.", ephemeral=True)


@bot.tree.command(name="veritan_muzik", description="Ses kanalında müzik çalar (sesler/ klasöründen).")
@app_commands.describe(parca="Parça adı (boş bırakırsan matrix çalar)")
async def veritan_muzik(interaction: discord.Interaction, parca: str = ""):
    await interaction.response.defer(ephemeral=True)
    vc = (interaction.guild.voice_client if interaction.guild else None) or _bagli_ses_client()
    if vc is None:
        await interaction.followup.send("⚠️ Veritan ses kanalında değil.", ephemeral=True)
        return
    if muzik_baslat(vc, parca):
        await interaction.followup.send(
            f"🎵 Çalıyor: `{os.path.basename(_muzik_durum['calan'])}`", ephemeral=True)
    else:
        mevcut = []
        if os.path.isdir(SES_KLASORU):
            mevcut = [os.path.splitext(f)[0] for f in os.listdir(SES_KLASORU)
                      if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a"))]
        await interaction.followup.send(
            f"⚠️ Parça bulunamadı. Mevcut parçalar: `{', '.join(mevcut) or 'yok'}`", ephemeral=True)


@bot.tree.command(name="veritan_dur", description="Çalan müziği durdurur.")
async def veritan_dur(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    vc = (interaction.guild.voice_client if interaction.guild else None) or _bagli_ses_client()
    if vc is None:
        await interaction.followup.send("⚠️ Veritan ses kanalında değil.", ephemeral=True)
        return
    muzik_durdur(vc, kalici=True)
    await interaction.followup.send("⏹️ Müzik durduruldu.", ephemeral=True)


@bot.tree.command(name="veritan_kimler", description="Ses kanalında kimler var, kim yayın açmış gösterir.")
async def veritan_kimler(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    metin = kanal_durumu_metni(interaction.guild)
    yayin = yayin_durumu_metni(interaction.guild)
    await interaction.followup.send(f"```\n{metin}\n\n{yayin}\n```", ephemeral=True)


# ==========================================================================
# ===================  WEB SUNUCUSU (HTML KÖPRÜSÜ)  ========================
# ==========================================================================

from aiohttp import web as _web

WEB_PORT = int(os.environ.get("PORT", "8080"))


def _cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp


def _bagli_ses_client():
    for g in bot.guilds:
        vc = g.voice_client
        if vc and vc.is_connected():
            return vc
    return None


def _bagli_guild():
    for g in bot.guilds:
        vc = g.voice_client
        if vc and vc.is_connected():
            return g
    return None


async def web_saglik(request):
    return _cors(_web.json_response({"ok": True, "mesaj": "Veritan web ayakta"}))


async def web_options(request):
    return _cors(_web.Response(text=""))


async def web_dinliyorum(request):
    vc = _bagli_ses_client()
    if vc is None:
        return _cors(_web.json_response({"ok": False, "hata": "bot seste degil"}, status=409))
    try:
        if os.path.exists(MP3_DINLIYORUM):
            await _dosya_cal(vc, MP3_DINLIYORUM, sil=False)
        else:
            await _seslendir_ve_cal(vc, "Seni dinliyorum.")
        return _cors(_web.json_response({"ok": True}))
    except Exception as e:
        traceback.print_exc()
        return _cors(_web.json_response({"ok": False, "hata": str(e)}, status=500))


async def web_konus(request):
    try:
        data = await request.json()
    except Exception:
        return _cors(_web.json_response({"ok": False, "hata": "gecersiz json"}, status=400))

    metin = (data.get("text") or "").strip()
    if not metin:
        return _cors(_web.json_response({"ok": False, "hata": "bos metin"}, status=400))

    vc = _bagli_ses_client()
    if vc is None:
        return _cors(_web.json_response(
            {"ok": False, "hata": "Bot ses kanalinda degil. Once /veritan_katil calistir."},
            status=409))

    guild = _bagli_guild()
    motor = getattr(bot, "_veritan_motor", None)

    try:
        baglam = (
            f"[Ortam] Sesli sohbet (web mikrofonu uzerinden).\n"
            f"[Ses kanali durumu]\n{kanal_durumu_metni(guild)}\n"
        )
        if _muzik_durum["istendi"]:
            baglam += "[Muzik] Su an muzik caliyor.\n"
        baglam += f"\nKisinin soyledigi: {metin}"

        messages = [{"role": "user", "content": [{"type": "text", "text": baglam}]}]
        # asker nesnesi yok -> uye arama araclari kapali (NoneType hatasini onler)
        response, _f, _t = await claude_cevapla(
            messages, guild, None, web_arama=False,
            system=SYSTEM_PROMPT2, arac_kullan=False,
        )
        ai_text = extract_text(response) if response else ""
        if not ai_text:
            ai_text = "Pardon, tekrar eder misin?"

        # --- Model etiketle is istedi mi? ---
        ai_text, komutlar = komutlari_ayikla(ai_text)
        print(f"[WEB] '{metin}' -> '{ai_text}'" + (f" {komutlar}" if komutlar else ""))

        await _seslendir_ve_cal(vc, ai_text)

        cikildi = False
        if komutlar:
            if motor is not None:
                cikildi = await motor.komutlari_uygula(komutlar, None)
            else:
                for komut, arg in komutlar:
                    if komut == "exit":
                        await _konusmayi_bitir_ve_ayril(vc, motor=None)
                        cikildi = True
                    elif komut == "muzik":
                        muzik_baslat(vc, arg)
                    elif komut == "dur":
                        muzik_durdur(vc, kalici=True)
                    elif komut == "ara" and arg:
                        sonuc = await web_arastir_ve_anlat(arg, None, guild)
                        await _seslendir_ve_cal(vc, sonuc)
        else:
            muzik_devam(vc)

        return _cors(_web.json_response({
            "ok": True, "cevap": ai_text,
            "komutlar": [k for k, _a in komutlar],
            "ayrildi": cikildi,
        }))
    except Exception as e:
        traceback.print_exc()
        return _cors(_web.json_response({"ok": False, "hata": str(e)}, status=500))


async def web_durum(request):
    """HTML tarafi isterse kanal durumunu cekebilsin."""
    guild = _bagli_guild()
    return _cors(_web.json_response({
        "ok": True,
        "kanal": kanal_durumu_metni(guild),
        "yayin": yayin_durumu_metni(guild),
        "muzik": bool(_muzik_durum["istendi"]),
    }))


async def _web_baslat():
    app = _web.Application()
    app.router.add_get("/", web_saglik)
    app.router.add_get("/durum", web_durum)
    app.router.add_post("/konus", web_konus)
    app.router.add_post("/dinliyorum", web_dinliyorum)
    app.router.add_route("OPTIONS", "/konus", web_options)
    app.router.add_route("OPTIONS", "/dinliyorum", web_options)
    runner = _web.AppRunner(app)
    await runner.setup()
    site = _web.TCPSite(runner, "0.0.0.0", WEB_PORT)
    await site.start()
    print(f"[WEB] Sunucu ayakta: 0.0.0.0:{WEB_PORT}")


bot.setup_hook = _web_baslat
# ==========================================================================
# mms
MM_DUYURU_METNI = "[emphasis]Something Happen To Server In Three Days ... [long pause][emphasis] So Make New Server Vacant"
_MM_SES_CACHE = {}


async def _mm_ses_al(metin: str) -> bytes:
    if metin in _MM_SES_CACHE:
        return _MM_SES_CACHE[metin]
    ses = await generate_fish_audio(metin)
    _MM_SES_CACHE[metin] = ses
    if len(_MM_SES_CACHE) > 30:
        _MM_SES_CACHE.pop(next(iter(_MM_SES_CACHE)))
    return ses


@bot.tree.command(
    name="mm_veritan1",
    description="(Sadece yetkili) İstediğin metni ses kanalında seslendirir. Model kullanmaz.",
)
@app_commands.describe(
    metin="Söyletmek istediğin cümle. Boş bırakırsan sabit duyuruyu söyler.",
    tekrar="Kaç kez söylensin (varsayılan 1)",
)
async def mm_veritan1(
    interaction: discord.Interaction,
    metin: str = None,
    tekrar: app_commands.Range[int, 1, 5] = 1,
):
    await interaction.response.defer(ephemeral=True)

    if not yetkili_mi(interaction.user):
        await interaction.followup.send(
            f"⛔ Sadece yetkili kullanabilir. (Sen → `{interaction.user.name}`, ID: `{interaction.user.id}`)",
            ephemeral=True,
        )
        return

    soylenecek = (metin or "").strip() or MM_DUYURU_METNI
    if len(soylenecek) > 500:
        await interaction.followup.send(
            f"⚠️ Metin çok uzun ({len(soylenecek)} karakter). En fazla 500 karakter.",
            ephemeral=True,
        )
        return

    vc = interaction.guild.voice_client if interaction.guild else None
    if vc is None or not vc.is_connected():
        vc = _bagli_ses_client()
    if vc is None:
        await interaction.followup.send(
            "⚠️ Veritan ses kanalında değil. Önce `/veritan_katil` çalıştır.",
            ephemeral=True,
        )
        return

    motor = getattr(bot, "_veritan_motor", None)
    if motor is not None:
        motor.mesgul = True

    try:
        ses = await _mm_ses_al(soylenecek)
        yol = f"/tmp/mm_veritan1_{datetime.now().timestamp()}.mp3"
        with open(yol, "wb") as f:
            f.write(ses)

        for i in range(tekrar):
            await _dosya_cal(vc, yol, sil=False)
            if i < tekrar - 1:
                await asyncio.sleep(0.4)

        try:
            os.remove(yol)
        except Exception:
            pass

        kaynak = "özel metin" if metin else "sabit duyuru"
        print(f"[MM] {kaynak} {tekrar} kez calindi -> {interaction.user}: {soylenecek[:80]}")
        await interaction.followup.send(
            f"✅ **{tekrar}** kez seslendirildi ({kaynak}):\n> {soylenecek}",
            ephemeral=True,
        )

    except Exception as e:
        traceback.print_exc()
        await interaction.followup.send(f"⚠️ Seslendirilemedi: `{e}`", ephemeral=True)

    finally:
        if motor is not None:
            motor.mesgul = False
        muzik_devam(vc)
# mmsa


# ==========================================================================
# ==================  SAHNEDE EL KALDIRMA KOMUTU  ==========================
# ==========================================================================

@bot.tree.command(
    name="elkaldirveritan",
    description="(Sadece yetkili) Veritan sahne kanalında konuşmak için el kaldırır.",
)
async def elkaldirveritan(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)

    if not yetkili_mi(interaction.user):
        await interaction.followup.send(
            f"⛔ Sadece yetkili kullanabilir. (Sen → `{interaction.user.name}`, ID: `{interaction.user.id}`)",
            ephemeral=True,
        )
        return

    if interaction.guild is None:
        await interaction.followup.send("Bu komut sadece sunucuda çalışır.", ephemeral=True)
        return

    me = interaction.guild.me
    vc = interaction.guild.voice_client

    if vc is None or not vc.is_connected():
        await interaction.followup.send(
            "⚠️ Veritan bir ses/sahne kanalında değil. Önce `/veritan_katil` çalıştır.",
            ephemeral=True,
        )
        return

    kanal = me.voice.channel if (me.voice and me.voice.channel) else None
    if not isinstance(kanal, discord.StageChannel):
        await interaction.followup.send(
            f"⚠️ Bulunduğu kanal bir SAHNE kanalı değil (`{getattr(kanal, 'name', '?')}`). "
            "El kaldırma sadece sahne kanallarında çalışır.",
            ephemeral=True,
        )
        return

    try:
        await me.edit(suppress=False)
        print(f"[SAHNE] Dogrudan konusmaci olundu -> {kanal.name}")
        await interaction.followup.send(
            f"🎤 Veritan **{kanal.name}** sahnesinde konuşmacı oldu (moderatör yetkisi vardı).",
            ephemeral=True,
        )
        return
    except discord.Forbidden:
        pass
    except Exception as e:
        print("[SAHNE] suppress=False denemesi basarisiz:", repr(e))

    try:
        await me.request_to_speak()
        print(f"[SAHNE] El kaldirildi -> {kanal.name}")
        await interaction.followup.send(
            f"✋ Veritan **{kanal.name}** sahnesinde el kaldırdı. "
            "Bir moderatörün onu konuşmacı yapması gerekiyor.",
            ephemeral=True,
        )
    except discord.Forbidden as e:
        await interaction.followup.send(
            f"⚠️ İzin yok. Botun sahne kanalında **Connect** ve **Request to Speak** izinleri olmalı.\n`{e}`",
            ephemeral=True,
        )
    except Exception as e:
        traceback.print_exc()
        await interaction.followup.send(f"⚠️ El kaldırılamadı: `{e}`", ephemeral=True)
# ==========================================================================


bot.run(DISCORD_TOKEN)
