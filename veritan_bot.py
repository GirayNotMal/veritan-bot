import io
import os
import base64
import discord
from discord import app_commands
from discord.ext import commands
import anthropic
import httpx

# ================= KONFİGÜRASYON =================
# ANAHTARLARI KODA YAZMA! Railway > Variables kısmına gir.
DISCORD_TOKEN = os.environ["MTUzMDUyMTYyMDY3MjY3NTkwMg.G_rZRW.fs2sVW8KEkTEgMiAbpQAw49xMHEjJfjw8Z-lhQ"]
ANTHROPIC_API_KEY = os.environ["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"]
FISH_AUDIO_API_KEY = os.environ["1fa3d289065241dfa80c4b949041b43d"]
FISH_REFERENCE_ID = os.environ["4538ecef264043b8b0e6d8e38606c4a7"]

# En ucuz + en hızlı model: Claude Haiku 3.5
# En az kotayı tüketen (mutlak en ucuz) alternatif: "claude-3-haiku-20240307"
ANTHROPIC_MODEL = "claude-haiku-4-5"

# Kısa yanıt = az token = az para + kısa ses dosyası
MAX_TOKENS = 200
SYSTEM_PROMPT = (
    "Senin adın Veritan. Türkçe İstersen Farklı Dil Orjinal Dilin İngilizce Ama Adamın Konuştuğu Veya İstediği Dili Konuş, kısa ve net cevap ver. "
    "Cevapların sesli okunacağı için en fazla 2-3 cümle kullan; "
    "kod bloğu veya başlık kullanma."
    "Fish Aduio'ya bağlısın O Yüzden [embrassed] gibi şeyler kullan oraya göre çünkü fish.aduio ya bağlısın"
    "Sen Türksün Ve İstanbullusun Ve Sadece İsmin Veritan Başka Hiç Bir İsmin Yok Sadece Sen Veritan'sın Ve Türkiyede Geliştirildin"
    "Sen Çok Zekisin Ve Birisi Sana Aptalca Birşey Sorduğunda Sende Ona Aptalca Brişey De Aptalca Bir Cevap Ver Yani"
)

# İnternet aramayı kapatmak istersen False yap
SEARCH_ENABLED = True
# =================================================

# Discord Bot Kurulumu
# members = True -> sunucudaki kişileri isimden bulabilmek için ŞART.
# (Ayrıca Developer Portal > Bot > "Server Members Intent" AÇIK olmalı.)
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Anthropic Async İstemcisi
anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


# ---------- YARDIMCI FONKSİYONLAR ----------

def describe_member(m) -> str:
    """Bir kişinin profilini metne döker."""
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
        durum = str(m.status) if m.status else "bilinmiyor"
        parts.append(f"Durum: {durum}")
    parts.append(f"Hesap açıldı: {m.created_at:%d.%m.%Y}")
    return " | ".join(parts)


async def uye_ara(guild, isim, asker, limit=5):
    """İsimden sunucu üyesi arar. 'ben/kendim' -> soruyu soran kişi."""
    if isim.lower().strip() in ("ben", "benim", "kendim", "ben kimim", "me", "kendi"):
        return [asker]
    if guild is None:
        return []
    try:
        sonuc = await guild.query_members(query=isim, limit=limit)
    except Exception:
        sonuc = []
    if not sonuc:
        dusuk = isim.lower()
        sonuc = [
            m for m in guild.members
            if dusuk in m.name.lower() or dusuk in m.display_name.lower()
        ][:limit]
    return sonuc


async def avatar_indir(member) -> bytes:
    """Kişinin profil fotoğrafını indirir."""
    url = member.display_avatar.replace(size=512).url
    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.content


async def generate_fish_audio(text: str) -> bytes:
    """Fish Audio altyapısını kullanarak metni MP3 sesine dönüştürür."""
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
    """Anthropic yanıtından güvenli şekilde metni çıkarır."""
    parts = [block.text for block in response.content if block.type == "text"]
    return "\n".join(parts).strip()


# ---------- CLAUDE İÇİN ARAÇLAR (TOOLS) ----------

TOOLS = [
    {
        "name": "sunucu_uyesi_bul",
        "description": (
            "Discord sunucusundaki bir kişiyi ismine veya takma adına göre arar ve "
            "profil bilgilerini (ad, ID, roller, katılma tarihi vb.) döndürür. "
            "'X kim', 'ben kimim', 'otto kimdir', 'şu kişinin profili' gibi sorularda kullan. "
            "Kendisini soran kişi için isim olarak 'ben' yaz."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "isim": {"type": "string", "description": "Aranan kişinin ismi/takma adı. Kişinin kendisi için 'ben'."}
            },
            "required": ["isim"],
        },
    },
    {
        "name": "profil_fotografi_gonder",
        "description": (
            "Belirtilen kişinin profil fotoğrafını Discord kanalına gönderilmek üzere işaretler. "
            "Kullanıcı birinin fotoğrafını/avatarını istediğinde kullan."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "isim": {"type": "string", "description": "Fotoğrafı istenen kişinin ismi. Kendisi için 'ben'."}
            },
            "required": ["isim"],
        },
    },
]

if SEARCH_ENABLED:
    TOOLS.append({
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 3,
    })


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"Komut senkronize hatası: {e}")
    print(f"Veritan çevrimiçi! ({bot.user.name})")


# ---------- /veritan KOMUTU ----------

@bot.tree.command(
    name="veritan",
    description="Veritan ile konuşun (yanıt MP3 ses; gerekirse fotoğraf da gelir).",
)
@app_commands.describe(
    message="Veritan'a iletmek istediğiniz mesaj",
    dosya="(İsteğe bağlı) Bir resim ekleyebilirsin; Veritan görüp yorumlar.",
)
async def veritan_command(
    interaction: discord.Interaction,
    message: str,
    dosya: discord.Attachment = None,
):
    await interaction.response.defer()

    try:
        guild = interaction.guild
        asker = interaction.user

        baglam = (
            f"[Soruyu soran kişi] {describe_member(asker)}\n"
            f"[Sunucu] {guild.name if guild else 'Özel mesaj'}\n\n"
            f"Mesaj: {message}"
        )
        user_content = [{"type": "text", "text": baglam}]

        # Kullanıcı resim eklediyse Claude'un görmesi için ekle (vision)
        if dosya is not None and dosya.content_type and dosya.content_type.startswith("image/"):
            img_bytes = await dosya.read()
            user_content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": dosya.content_type,
                    "data": base64.standard_b64encode(img_bytes).decode("utf-8"),
                },
            })
            user_content.append({"type": "text", "text": "(Kullanıcı yukarıdaki resmi ekledi.)"})

        messages = [{"role": "user", "content": user_content}]
        gonderilecek_fotograflar = []  # (dosya_adi, bytes)

        # ----- Araç döngüsü (tool loop) -----
        response = None
        for _ in range(6):
            response = await anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

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
                        metin = f"'{isim}' adiyla eslesen kimse bulunamadi."
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": metin,
                    })

                elif block.name == "profil_fotografi_gonder":
                    isim = block.input.get("isim", "")
                    bulunanlar = await uye_ara(guild, isim, asker, limit=1)
                    if bulunanlar:
                        m = bulunanlar[0]
                        try:
                            foto = await avatar_indir(m)
                            gonderilecek_fotograflar.append((f"{m.name}.png", foto))
                            not_ = f"{m.display_name} adli kisinin profil fotografi gonderilecek."
                        except Exception as e:
                            not_ = f"Fotograf indirilemedi: {e}"
                    else:
                        not_ = f"'{isim}' bulunamadi, fotograf gonderilemedi."
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": not_,
                    })

            messages.append({"role": "user", "content": tool_results})

        # ----- Metni sese çevir -----
        ai_text = extract_text(response) if response else ""
        if not ai_text:
            ai_text = "Üzgünüm, bir cevap üretemedim."

        audio_bytes = await generate_fish_audio(ai_text)

        # ----- MP3 + varsa fotoğrafları gönder -----
        files = [discord.File(io.BytesIO(audio_bytes), filename="veritan.mp3")]
        for fname, fbytes in gonderilecek_fotograflar:
            files.append(discord.File(io.BytesIO(fbytes), filename=fname))

        await interaction.followup.send(files=files)

    except Exception as e:
        await interaction.followup.send(f"Bir hata oluştu: `{str(e)}`", ephemeral=True)


bot.run(DISCORD_TOKEN)
