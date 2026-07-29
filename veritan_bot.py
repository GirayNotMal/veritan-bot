import io
import re
import base64
import traceback
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

# ARTIK KOMUTA GÖRE ÇALIŞIYOR:
#   /veritan          -> internet KAPALI (hızlı, neredeyse bedava)
#   /veritan_search   -> internet AÇIK (web'de arar, biraz yavaş + az para)

# Sunucudaki HERKESİ isimden aramak istersen ("otto kim" gibi):
#   1) Bunu True yap
#   2) Developer Portal > Bot > "Server Members Intent" AÇMAYI unutma
# KAPALIYKEN bot ASLA çökmez; "ben kimim" ve etiketlenen (@kişi) yine çalışır.
ENABLE_MEMBER_LOOKUP = False
# =================================================

# Discord Bot Kurulumu
intents = discord.Intents.default()
if ENABLE_MEMBER_LOOKUP:
    intents.members = True  # DİKKAT: portalda da açık olmalı, yoksa bot açılmaz
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
    parts.append(f"Hesap açıldı: {m.created_at:%d.%m.%Y}")
    return " | ".join(parts)


async def uye_ara(guild, isim, asker, limit=5):
    """Kişi arar. 'ben' -> soran kişi; @etiket/ID -> o kişi; isim -> arama."""
    isim = (isim or "").strip()
    if isim.lower() in ("ben", "benim", "kendim", "ben kimim", "me", "kendi"):
        return [asker]
    if guild is None:
        return []

    # Mesajda etiket/ID varsa (ör. <@123...> ya da düz ID)
    m_id = re.search(r"\d{15,20}", isim)
    if m_id:
        uid = int(m_id.group())
        member = guild.get_member(uid)
        if member is None:
            try:
                member = await guild.fetch_member(uid)  # privileged intent gerekmez
            except Exception:
                member = None
        return [member] if member else []

    # İsimle arama (bu kısım "Server Members Intent" gerektirir)
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

# Her zaman açık olan araçlar (kişi tanıma + fotoğraf). Bunlar para yemez.
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
            "properties": {
                "isim": {"type": "string", "description": "Aranan kişi. Kendisi için 'ben'."}
            },
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
            "properties": {
                "isim": {"type": "string", "description": "Fotoğrafı istenen kişi. Kendisi için 'ben'."}
            },
            "required": ["isim"],
        },
    },
]

# Sadece /veritan_search kullanınca eklenen internet arama aracı
WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 1,
}


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"Komut senkronize hatası: {e}")
    print(f"Veritan çevrimiçi! ({bot.user.name})")


async def claude_cevapla(messages, guild, asker, web_arama=False):
    """Araç döngüsünü çalıştırır. web_arama=True ise internet aracı da eklenir."""
    tools = list(BASE_TOOLS)
    if web_arama:
        tools = tools + [WEB_SEARCH_TOOL]

    gonderilecek_fotograflar = []
    response = None

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
            # Araçlar/web arama bu modelde sorun çıkarırsa: araçsız dene
            print("API hatasi, araclar olmadan tekrar deneniyor:", repr(api_err))
            response = await anthropic_client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            break

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
                        not_ = f"{m.display_name} profil fotografi gonderilecek."
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

    return response, gonderilecek_fotograflar


async def veritan_calistir(interaction, message, dosya, web_arama):
    """Hem /veritan hem /veritan_search için ortak iş mantığı."""
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

        response, fotograflar = await claude_cevapla(messages, guild, asker, web_arama=web_arama)

        ai_text = extract_text(response) if response else ""
        if not ai_text:
            ai_text = "Üzgünüm, bir cevap üretemedim."

        audio_bytes = await generate_fish_audio(ai_text)

        files = [discord.File(io.BytesIO(audio_bytes), filename="veritan.mp3")]
        for fname, fbytes in fotograflar:
            files.append(discord.File(io.BytesIO(fbytes), filename=fname))

        await interaction.followup.send(files=files)

    except Exception as e:
        traceback.print_exc()  # gerçek hata Railway loglarına yazılır
        try:
            await interaction.followup.send(f"Bir hata oluştu: `{str(e)}`", ephemeral=True)
        except Exception:
            pass


# ---------- KOMUTLAR ----------

# /veritan  -> internet KAPALI (hızlı, bedava)
@bot.tree.command(
    name="veritan",
    description="Veritan ile konuşun (hızlı, internetsiz; yanıt MP3).",
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
    await veritan_calistir(interaction, message, dosya, web_arama=False)


# /veritan_search  -> internet AÇIK (web'de arar)
@bot.tree.command(
    name="veritan_search",
    description="Veritan internette arayarak cevap verir (biraz yavaş; yanıt MP3).",
)
@app_commands.describe(
    message="İnternette aratmak istediğiniz mesaj",
    dosya="(İsteğe bağlı) Bir resim ekleyebilirsin; Veritan görüp yorumlar.",
)
async def veritan_search_command(
    interaction: discord.Interaction,
    message: str,
    dosya: discord.Attachment = None,
):
    await veritan_calistir(interaction, message, dosya, web_arama=True)


bot.run(DISCORD_TOKEN)
