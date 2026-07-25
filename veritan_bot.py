import io
import discord
from discord import app_commands
from discord.ext import commands
import anthropic
import httpx

# ================= KONFİGÜRASYON =================
DISCORD_TOKEN = "MTUzMDUyMTYyMDY3MjY3NTkwMg.G_rZRW.fs2sVW8KEkTEgMiAbpQAw49xMHEjJfjw8Z-lhQ"
ANTHROPIC_API_KEY = "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"
FISH_AUDIO_API_KEY = "1fa3d289065241dfa80c4b949041b43d"

# Fish Audio Reference ID (Kendi ses modelinizin ID'sini buraya yazın)
FISH_REFERENCE_ID = "4538ecef264043b8b0e6d8e38606c4a7"

# En ucuz + en hızlı model: Claude Haiku 3.5
# En az kotayı tüketen (mutlak en ucuz) alternatif: "claude-3-haiku-20240307"
ANTHROPIC_MODEL = "claude-3-5-haiku-20241022"

# Kısa yanıt = az token = az para + kısa ses dosyası
MAX_TOKENS = 200
SYSTEM_PROMPT = (
    "Senin adın Veritan. Türkçe, kısa ve net cevap ver. "
    "Cevapların sesli okunacağı için en fazla 2-3 cümle kullan; "
    "madde işareti, emoji, kod bloğu veya başlık kullanma."
)
# =================================================

# Discord Bot Kurulumu (slash komutları için varsayılan intent yeterli)
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Anthropic Async İstemcisi
anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)


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


@bot.event
async def on_ready():
    # Slash komutlarını Discord sunucularına senkronize et
    try:
        synced = await bot.tree.sync()
        print(f"{len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"Komut senkronize hatası: {e}")

    print(f"Veritan çevrimiçi! ({bot.user.name})")


# /veritan Slash Komutu
@bot.tree.command(
    name="veritan",
    description="Veritan ile konuşun (yanıt sadece MP3 ses dosyası olarak iletilir).",
)
@app_commands.describe(message="Veritan'a iletmek istediğiniz mesaj")
async def veritan_command(interaction: discord.Interaction, message: str):
    # API çağrıları vakit alacağı için "işleniyor" sinyali gönderiyoruz (zaman aşımını önler)
    await interaction.response.defer()

    try:
        # 1. Anthropic Haiku'ya mesajı gönder (metin cevabı üretilir)
        response = await anthropic_client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": message}],
        )
        ai_text = extract_text(response)
        if not ai_text:
            ai_text = "Üzgünüm, bir cevap üretemedim."

        # 2. Üretilen metni Fish Audio API'sine gönderip MP3 al
        audio_bytes = await generate_fish_audio(ai_text)

        # 3. Metni kanala yazmadan doğrudan MP3 dosyasını yükle
        audio_file = discord.File(io.BytesIO(audio_bytes), filename="veritan.mp3")
        await interaction.followup.send(file=audio_file)

    except Exception as e:
        # Hata durumunda gizli (ephemeral) uyarı ver
        await interaction.followup.send(f"Bir hata oluştu: `{str(e)}`", ephemeral=True)


bot.run(DISCORD_TOKEN)
