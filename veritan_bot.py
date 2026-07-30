import io
import re
import os
import json
import base64
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

ANTHROPIC_MODEL = "claude-haiku-4-5"

# Kısa yanıt = az token = az para + kısa ses dosyası + daha hızlı
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

# ---- LİMİT AYARLARI (TOKEN BAZLI) ----
# Hak artık tam sayı "soru" değil, ONDALIKLI bir bakiye.
# Üretilen her token TOKEN_MALIYETI kadar hak yer. (Düşünme/reasoning tokenları da dahil.)
# Cevap ne kadar uzunsa o kadar çok hak düşer.
DAILY_LIMIT = 10.0        # Kişi başına günlük hak bakiyesi
TOKEN_MALIYETI = 0.01     # 1 token = 0.01 hak (yani ~100 token = 1 hak)
RESET_SAAT = 24           # Kaç saatte bir yenilenir
OWNER_USERNAME = "ztar2907"  # Sadece bu username limit sıfırlayabilir
LIMIT_FILE = "veritan_limits.json"

# ARTIK KOMUTA GÖRE ÇALIŞIYOR:
#   /veritan          -> internet KAPALI (hızlı, neredeyse bedava)
#   /veritan_search   -> internet AÇIK (web'de arar, biraz yavaş + az para)

# Sunucudaki HERKESİ isimden aramak istersen ("otto kim" gibi):
#   1) Bunu True yap
#   2) Developer Portal > Bot > "Server Members Intent" AÇMAYI unutma
ENABLE_MEMBER_LOOKUP = False
# =================================================

# Discord Bot Kurulumu
intents = discord.Intents.default()
if ENABLE_MEMBER_LOOKUP:
    intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Anthropic Async İstemcisi
anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


# ================= LİMİT SİSTEMİ =================
_limits = {}  # user_id -> {"limit": float, "kalan": float, "reset_at": datetime}


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
    """Kaydı getirir; süresi dolduysa yeniler."""
    now = datetime.now(timezone.utc)
    rec = _limits.get(user_id)
    if rec is None or now >= rec["reset_at"]:
        rec = {"limit": DAILY_LIMIT, "kalan": DAILY_LIMIT, "reset_at": now + timedelta(hours=RESET_SAAT)}
        _limits[user_id] = rec
    return rec


def limit_kontrol(user_id):
    """Bakiyeyi getirir (düşürmez). (kalan, limit, reset_at, izin_var_mi)."""
    rec = _kayit_al(user_id)
    return rec["kalan"], rec["limit"], rec["reset_at"], rec["kalan"] > 0


def limit_harca(user_id, miktar):
    """Cevap sonrası token maliyetini bakiyeden düşer. Yeni kalanı döndürür."""
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


def limit_embed(user, kalan, limit, reset_at, son_token=None, son_hak=None):
    """Kullanıcının hak bakiyesini gösteren bar'lı UI kartı."""
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
    """Bir yanıttan üretilen (output + varsa reasoning) token sayısını alır."""
    try:
        u = response.usage
        toplam = getattr(u, "output_tokens", 0) or 0
        # bazı modellerde ayrı reasoning/thinking sayacı olabilir
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


@bot.event
async def on_ready():
    _limit_yukle()
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"Komut senkronize hatası: {e}")
    print(f"Veritan çevrimiçi! ({bot.user.name})")


async def claude_cevapla(messages, guild, asker, web_arama=False):
    """Araç döngüsü. (response, fotograflar, uretilen_token) döndürür."""
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
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
        except Exception as api_err:
            print("API hatasi, araclar olmadan tekrar deneniyor:", repr(api_err))
            response = await anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
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
                    metin = f"'{isim}' bulunamadi (isimle arama icin Server Members Intent gerekir)."
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
    """Hem /veritan hem /veritan_search için ortak iş mantığı."""
    await interaction.response.defer()
    asker = interaction.user

    # ----- BAKİYE KONTROLÜ (API çağrısından ÖNCE) -----
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

        # Dosya eklendiyse
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

        # ----- TOKEN BAZLI MALİYET: cevap uzadıkça hak azalır -----
        maliyet = uretilen_token * TOKEN_MALIYETI
        yeni_kalan = limit_harca(asker.id, maliyet)

        audio_bytes = await generate_fish_audio(ai_text)

        # 1) MP3 (+ varsa profil fotoğrafları)
        files = [discord.File(io.BytesIO(audio_bytes), filename="veritan.mp3")]
        for fname, fbytes in fotograflar:
            files.append(discord.File(io.BytesIO(fbytes), filename=fname))
        await interaction.followup.send(files=files)

        # 2) MP3'ten sonra: harcanan token + kalan bakiye kartı
        await interaction.followup.send(
            embed=limit_embed(asker, yeni_kalan, limit, reset_at, son_token=uretilen_token, son_hak=maliyet)
        )

    except Exception as e:
        # Hata olduysa henüz düşüş yapılmadı (düşüş cevaptan sonra), iade gerekmez
        traceback.print_exc()
        try:
            await interaction.followup.send(f"Bir hata oluştu: `{str(e)}`", ephemeral=True)
        except Exception:
            pass


# ---------- KOMUTLAR ----------

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


@bot.tree.command(
    name="limitresetveritan",
    description="(Sadece yetkili) Bir kullanıcının hak bakiyesini sıfırlar/belirler.",
)
@app_commands.describe(
    kullanici="Bakiyesi ayarlanacak kişi",
    limit="Verilecek hak (ör. 10)",
)
async def limitreset_command(interaction: discord.Interaction, kullanici: discord.Member, limit: int):
    if interaction.user.name != OWNER_USERNAME:
        await interaction.response.send_message("⛔ Bu komutu sadece yetkili kullanabilir.", ephemeral=True)
        return

    if limit < 0:
        limit = 0

    rec = limit_resetle(kullanici.id, limit)
    await interaction.response.send_message(
        content=f"✅ {kullanici.display_name} için hak bakiyesi **{float(limit):.2f}** olarak ayarlandı.",
        embed=limit_embed(kullanici, rec["kalan"], rec["limit"], rec["reset_at"]),
    )


bot.run(DISCORD_TOKEN)
