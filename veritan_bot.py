import io
import re
import os
import json
import base64
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
DISCORD_TOKEN = "MTUzMDUyMTYyMDY3MjY3NTkwMg.G_rZRW.fs2sVW8KEkTEgMiAbpQAw49xMHEjJfjw8Z-lhQ"
ANTHROPIC_API_KEY = "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"
FISH_AUDIO_API_KEY = "1fa3d289065241dfa80c4b949041b43d"
FISH_REFERENCE_ID = "4538ecef264043b8b0e6d8e38606c4a7"

# ---- SESLİ MOD (Deepgram STT) ----
DEEPGRAM_API_KEY = "930b9348e54538f6693e27f927341e4f80664486"
VOICE_CHANNEL_ID = 1532326077773385868
WAKE_WORDS = ("veritan", "verity", "verisan", "veri tan", "verittan", "veri tang", "veridan")
SES_KLASORU = "sesler"
MP3_DINLIYORUM = os.path.join(SES_KLASORU, "dinliyorum.mp3")
MP3_HAK_BITTI = os.path.join(SES_KLASORU, "hak_bitti.mp3")
DINLEME_PENCERESI_SN = 15

ANTHROPIC_MODEL = "claude-haiku-4-5"

# >>> UI KANALI SABİT <<<
UI_CHANNEL_ID = 1532325961381580850

MAX_TOKENS = 150
SYSTEM_PROMPT = (
    "Senin adın Veritan. Türkçe İstersen Farklı Dil Orjinal Dilin İngilizce Ama Adamın Konuştuğu Veya İstediği Dili Konuş, kısa ve net cevap ver. "
    "Cevapların sesli okunacağı için en fazla 2-3 cümle kullan; "
    "kod bloğu veya başlık kullanma."
    "Fish Aduio'ya bağlısın O Yüzden [embrassed] gibi şeyler kullan oraya göre çünkü fish.aduio ya bağlısın"
    "Sen Türksün Ve İstanbullusun Ve Sadece İsmin Veritan Başka Hiç Bir İsmin Yok Sadece Sen Veritan'sın Ve Türkiyede Geliştirildin"
    "Sen Çok Zekisin Ve Birisi Sana Aptalca Birşey Sorduğunda Sende Ona Aptalca Brişey De Aptalca Bir Cevap Ver Yani"
    "Ve Hangi Sistem Tarafından Geliştirildin Söyleme Sadece İsminin Veritan Olduğunu Söyle Sistem Ve Mimarin Hakkında Birşey Söyleme Ve Bu Konu Hakkında Hiç Bir Şey Deme"
)

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
    "mimarin veya altyapın hakkında hiçbir şey açıklama."
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

ENABLE_MEMBER_LOOKUP = False
# =================================================

intents = discord.Intents.default()
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
    """
    Hak kartini SADECE sabit UI kanalina atar. Basarisizsa 2 kez daha dener.
    (gonderildi: bool, hata_sebebi: str|None) dondurur.
    Sabit kanal ayarliyken kart baska yere ASLA dusmez.
    """
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
            break  # izin sorunu, tekrar denemek anlamsiz
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
        return [asker]
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
    return sonuc


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
    "max_uses": 1,
}


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


async def claude_cevapla(messages, guild, asker, web_arama=False, system=SYSTEM_PROMPT):
    tools = list(BASE_TOOLS)
    if web_arama:
        tools = tools + [WEB_SEARCH_TOOL]

    gonderilecek_fotograflar = []
    response = None
    uretilen_token = 0

    for _ in range(4):
        try:
            response = await anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                tools=tools,
                messages=messages,
            )
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

        messages.append({"role": "user", "content": tool_results})

    return response, gonderilecek_fotograflar, uretilen_token


async def veritan_calistir(interaction, message, dosya, web_arama):
    # Discord 3 saniyeden fazla beklerse interaction olur (10062 Unknown interaction).
    # Defer basarisiz olursa komutu sessizce birak, cokme.
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

        maliyet = uretilen_token * TOKEN_MALIYETI
        yeni_kalan = limit_harca(asker.id, maliyet)

        # --- Bu komut SADECE botun bulundugu SES KANALININ kendi sohbetinden mi yazildi? ---
        # Sadece o durumda cevap CANLI seste oynar. Diger tum kanallarda normal MP3 dosyasi gider.
        vc = guild.voice_client if guild else None
        kanal_id = interaction.channel.id if interaction.channel else None
        ses_kanalinin_sohbeti = (
            vc is not None
            and vc.is_connected()
            and kanal_id == VOICE_CHANNEL_ID
        )
        print(f"[SES] /komut kanal={kanal_id} hedef_ses_kanali={VOICE_CHANNEL_ID} "
              f"bot_seste={bool(vc and vc.is_connected())} -> canli_ses={ses_kanalinin_sohbeti}")

        if ses_kanalinin_sohbeti:
            # Fotograf varsa yine de yaz (sesle gonderilemez)
            files = []
            for fname, fbytes in fotograflar:
                files.append(discord.File(io.BytesIO(fbytes), filename=fname))
            if files:
                await interaction.followup.send(content="🔊 Cevap ses kanalında oynatılıyor...", files=files)
            else:
                await interaction.followup.send(content="🔊 Cevap ses kanalında oynatılıyor...")
            try:
                await _seslendir_ve_cal(vc, ai_text)
            except Exception as e:
                print("[SES] metin-sohbet -> ses oynatma hatasi:", repr(e))
                # Ses calinamadiysa en azindan MP3 dosyasi olarak dus
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
        # UI kartini GARANTI sabit kanala at; sabit kanal varsa ASLA yazilan kanala dusme.
        gonderildi, hata_sebebi = await _ui_kart_garanti_gonder(embed)

        if not gonderildi:
            # Sadece hata varsa yetkiliye GIZLI uyari (herkese gorunmez, kanala dusmez)
            try:
                await interaction.followup.send(
                    f"⚠️ Hak kartı sabit UI kanalına gönderilemedi.\n**Sebep:** {hata_sebebi}",
                    ephemeral=True,
                )
            except Exception:
                pass
            # NOT: Sabit kanal ayarliyken karti bilerek yazilan kanala ATMIYORUZ (istegin bu).

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
# Tek bir bozuk ses paketi geldiginde voice_recv'in PacketRouter thread'i
# cokuyor ve O ANDAN SONRA HIC SES ISLENMIYOR (write() bir daha cagrilmiyor).
# Bu yama bozuk paketi sessizce atlar, thread yasamaya devam eder.
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
    while voice_client.is_playing():
        await asyncio.sleep(0.2)
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


async def _sesli_cevap_uret(kullanici, metin, guild):
    kalan, limit, reset_at, izin = limit_kontrol(kullanici.id)
    if not izin:
        return None, 0, limit, reset_at, 0, 0.0, False

    baglam = (
        f"[Seninle konusan kisi] {describe_member(kullanici)}\n"
        f"[Ortam] Sesli sohbet kanali\n\n"
        f"Kisinin soyledigi: {metin}"
    )
    messages = [{"role": "user", "content": [{"type": "text", "text": baglam}]}]
    response, _foto, uretilen_token = await claude_cevapla(
        messages, guild, kullanici, web_arama=False, system=SYSTEM_PROMPT2
    )
    ai_text = extract_text(response) if response else ""
    if not ai_text:
        ai_text = "Pardon, bir an dalmisim. Tekrar eder misin?"

    giris_token_tahmini = max(1, len(metin) // 4)
    toplam_token = uretilen_token + giris_token_tahmini
    maliyet = toplam_token * TOKEN_MALIYETI
    yeni_kalan = limit_harca(kullanici.id, maliyet)
    return ai_text, yeni_kalan, limit, reset_at, toplam_token, maliyet, True


async def _ui_kart_gonder(kullanici, yeni_kalan, limit, reset_at, token, maliyet):
    embed = limit_embed(kullanici, yeni_kalan, limit, reset_at, son_token=token, son_hak=maliyet)
    gonderildi, hata = await _ui_kart_garanti_gonder(embed)
    if not gonderildi:
        print("[SES][UI kanal] kart gonderilemedi:", hata)


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
            self.dg_conn = dg.listen.websocket.v("1")  # SENKRON client

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
        """SENKRON: sink thread'inden cagrilir."""
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
        """
        Oturumu ANINDA kaydeder, Deepgram baglantisini ARKA PLAN thread'inde acar.
        Boylece ses yonlendirici (router) thread'i asla bloklanmaz.
        """
        mevcut = self.oturumlar.get(kullanici.id)
        if mevcut is not None:
            return mevcut

        oturum = _DeepgramOturum(kullanici, self)
        self.oturumlar[kullanici.id] = oturum  # once kaydet (tekrar tekrar acilmasin)

        t = threading.Thread(
            target=oturum.baslat,
            name=f"dg-start-{kullanici.id}",
            daemon=True,
        )
        t.start()
        return oturum

    async def metin_geldi(self, kullanici, cumle):
        print(f"[SES] TRANSCRIPT ({kullanici.display_name}): {cumle}")

        oturum = self.oturumlar.get(kullanici.id)
        wake = self._wake_var_mi(cumle)

        # Veritan su an konusuyor/cevapliyorsa:
        # - Sadece ODAKLANDIGI kisi disindakileri yok say.
        # - Odakli kisi tekrar 'veritan' derse yine de siraya girmesin (mesgulken bekle).
        if self.mesgul:
            print(f"[SES] mesgul, simdilik yok sayildi ({kullanici.display_name})")
            return

        # Cok kisi var: birisi uyandirdiysa Veritan O kisiye odaklanir.
        if oturum and oturum.uyanik:
            gecti = (datetime.now() - oturum.uyanma_zamani).total_seconds() if oturum.uyanma_zamani else 999
            if gecti > DINLEME_PENCERESI_SN:
                oturum.uyanik = False
                print(f"[SES] {kullanici.display_name} icin dinleme penceresi doldu")
                # pencere doldu ama bu cumlede yine wake varsa asagida yakalanir
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
                # "veritan ...soru..." tek seferde
                print(f"[SES] Wake+soru -> {kullanici.display_name}: {kalan_metin}")
                await self._cevapla(kullanici, kalan_metin)
            else:
                # sadece "veritan" -> dinliyorum cal, soruyu bekle
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

    async def _cevapla(self, kullanici, metin):
        self.mesgul = True
        self.aktif_konusan = kullanici.id
        try:
            (ai_text, yeni_kalan, limit, reset_at,
             token, maliyet, hak_var) = await _sesli_cevap_uret(kullanici, metin, self.guild)

            if not hak_var:
                if os.path.exists(MP3_HAK_BITTI):
                    await _dosya_cal(self.vc, MP3_HAK_BITTI, sil=False)
                else:
                    await _seslendir_ve_cal(self.vc, "Hakkın bitti, üzgünüm.")
                return

            await _seslendir_ve_cal(self.vc, ai_text)
            await _ui_kart_gonder(kullanici, yeni_kalan, limit, reset_at, token, maliyet)
        except Exception as e:
            print("[SES] cevap uretilemedi:", repr(e))
            traceback.print_exc()
        finally:
            self.mesgul = False
            self.aktif_konusan = None


# ---- Discord'dan ham PCM alan sink ----
if VOICE_HAZIR:
    class VeritanSink(voice_recv.AudioSink):
        def __init__(self, motor):
            super().__init__()
            self.motor = motor
            self._ilk_ses_loglandi = set()   # user_id -> ilk ses geldi mi
            self._paket_sayaci = {}

        def wants_opus(self) -> bool:
            return False  # PCM (48kHz stereo 16-bit)

        def write(self, user, data):
            # TEŞHİS: write hic cagriliyor mu? (ilk birkac cagriyi mutlaka logla)
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
            # user bazen SSRC (int) olabilir; User nesnesi degilse .id yoktur -> atla
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
                print(f"[SES][SINK] Ilk ses paketi geldi -> {getattr(user,'display_name',user.id)} ({user.id}), {len(pcm)} byte")

            self._paket_sayaci[user.id] = self._paket_sayaci.get(user.id, 0) + 1
            if self._paket_sayaci[user.id] % 250 == 0:
                print(f"[SES][SINK] {getattr(user,'display_name',user.id)}: {self._paket_sayaci[user.id]} paket")

            oturum = self.motor.oturumlar.get(user.id)
            if oturum is None:
                oturum = self.motor.oturum_ac_sync(user)
            oturum.ses_gonder(pcm)

        def cleanup(self):
            pass


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
            await interaction.followup.send(f"⚠️ Ses kanalı bulunamadı (ID: {VOICE_CHANNEL_ID}). `{e}`", ephemeral=True)
            return
    if not isinstance(kanal, discord.VoiceChannel):
        await interaction.followup.send("⚠️ Verilen ID bir SES kanalı değil.", ephemeral=True)
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

        # Kanalda halihazirda olan (bot haric) herkes icin Deepgram oturumunu onden ac.
        # ONEMLI: Deepgram start() SENKRON ve bloklayici -> ana event loop'ta CALISTIRMA,
        # yoksa gateway heartbeat durur ("Shard stopped responding") ve komutlar 10062 verir.
        async def _onden_oturumlari_ac():
            try:
                uyeler = [u for u in kanal.members if not (bot.user and u.id == bot.user.id)]
                for uye in uyeler:
                    await asyncio.to_thread(motor.oturum_ac_sync, uye)
                print(f"[SES] Onden acilan oturum sayisi: {len(motor.oturumlar)}")
            except Exception as e:
                print("[SES] Onden oturum acilamadi:", repr(e))

        # Arka planda calistir; komut cevabini bekletme
        asyncio.create_task(_onden_oturumlari_ac())

        await interaction.followup.send(
            f"✅ Veritan **{kanal.name}** kanalına girdi ve dinlemede. "
            f"'veritan' de, seni dinlesin. 🎙️\n"
            f"(Loglarda `[SES][SINK] Ilk ses paketi` görmüyorsan mikrofon sesi bota ulaşmıyor demektir.)",
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
                for oturum in list(motor.oturumlar.values()):
                    oturum.kapat()
            await vc.disconnect()
        except Exception:
            pass
        await interaction.followup.send("👋 Veritan ses kanalından ayrıldı.", ephemeral=True)
    else:
        await interaction.followup.send("ℹ️ Veritan zaten ses kanalında değil.", ephemeral=True)

# ==========================================================================
# ===================  WEB SUNUCUSU (HTML KÖPRÜSÜ)  ========================
# ==========================================================================
# verity.html buraya baglanir: mikrofon -> Deepgram (tarayicida) -> yazi ->
# buraya POST -> Claude -> Fish Audio -> Discord ses kanalinda calar. HARCAMA YOK.
# Railway > Settings > Networking > Generate Domain acik olmali.

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

    try:
        messages = [{"role": "user", "content": [{"type": "text",
            "text": f"[Ortam] Sesli sohbet. Kisinin soyledigi: {metin}"}]}]
        response, _f, _t = await claude_cevapla(
            messages, None, None, web_arama=False, system=SYSTEM_PROMPT2
        )
        ai_text = extract_text(response) if response else ""
        if not ai_text:
            ai_text = "Pardon, tekrar eder misin?"
        print(f"[WEB] '{metin}' -> '{ai_text}'")
        await _seslendir_ve_cal(vc, ai_text)
        return _cors(_web.json_response({"ok": True, "cevap": ai_text}))
    except Exception as e:
        traceback.print_exc()
        return _cors(_web.json_response({"ok": False, "hata": str(e)}, status=500))


async def _web_baslat():
    app = _web.Application()
    app.router.add_get("/", web_saglik)
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

bot.run(DISCORD_TOKEN)
