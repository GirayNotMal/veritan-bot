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
HAPISHANE_KANAL_ID = 1532457659952009288   # ceza: kisi buraya tasinir, Veritan gelip konusur
WAKE_WORDS = ("veritan", "verity", "verisan", "veri tan", "verittan", "veri tang", "veridan")
SES_KLASORU = "sesler"
MP3_DINLIYORUM = os.path.join(SES_KLASORU, "dinliyorum.mp3")
MP3_HAK_BITTI = os.path.join(SES_KLASORU, "hak_bitti.mp3")
DINLEME_PENCERESI_SN = 1

# ---- MÜZİK ----
MUZIK_VARSAYILAN = "matrix"          # taban ad
# "muzik cal" (isimsiz) deyince bunlardan rastgele biri calar:
MUZIK_HAZIR_LISTE = ["matrix", "matrix1", "matrix2", "matrix3"]
MUZIK_SES_SEVIYESI = 0.5            # konusma duyulsun diye kisik
YTDLP_ACIK = True                    # internetten muzik (yt-dlp) kullanilsin mi
MUZIK_MAX_SN = 420                   # internetten cekilen parca max suresi (guvenlik)

# ---- FAVORİ / FAN ART RESMİ ----
FAVORI_RESIM = os.path.join(SES_KLASORU, "agaresim.png")  # "en sevdigin resim" deyince

# ---- SESSİZ ÜYE DÜRTMESİ ----
SESSIZ_DAKIKA = 2                    # kac dakika susarsa/mikrofonu kapaliysa laf atsin
SESSIZ_KONTROL_SN = 30               # kac saniyede bir kontrol
SESSIZ_TEKRAR_DK = 10                # ayni kisiye tekrar laf atmadan once bekleme

# ---- ARADA SIRADA HAL HATIR SORMA (muhabbet dürtmesi) ----
MUHABBET_ACIK = True                 # arada bir kendiliginden laf atsin mi
MUHABBET_MIN_DK = 1                  # en az bu kadar dakika gecmeden muhabbet baslatmaz
MUHABBET_MAX_DK = 2                 # en fazla bu kadar dakikada bir muhabbet eder
MUHABBET_KISI_TEKRAR_DK = 3         # ayni kisiyle tekrar muhabbet icin bekleme

# ---- ŞAKA / KOMEDİ DÜRTMESİ (istenmeden rastgele espri) ----
SAKA_ACIK = True                     # arada bir rastgele birine saka yapsin mi
SAKA_MIN_DK = 1                      # en az bu kadar dakikada bir (istedin: ~2 dk)
SAKA_MAX_DK = 2                      # en fazla bu kadar dakikada bir
SAKA_KISI_TEKRAR_DK = 2              # ayni kisiye tekrar saka icin bekleme

# ==========================================================================
# ---- HAZIR CÜMLE SİSTEMİ (senin belirledigin cumleler) ----
# ==========================================================================
# 1) GENEL cumleler: her ~1.5 dakikada rastgele biri seslendirilir (kimseye
#    ozel degil, oylesine laf). Buraya istedigin cumleleri ekle.
HAZIR_GENEL_ACIK = True
HAZIR_GENEL_ARALIK_SN = 90           # 1 dakika 30 saniye
HAZIR_GENEL_CUMLELER = [
    "hahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahaua",
    "hahuhahuhaahuauhauhahuauhauhauhahuauhahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhau",
    "Hello I'm Veritan! Your Personal Helper Nigger.",
    "aga kendimkiyle oynuyorum arada sırada hehe.",
    "aga kendimkiyle oynuyorum arada sırada hahuhahuhaahuauhauhahuauhauhauhahuauhahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhau.",
    "aga kendimkiyle oynuyorum arada sırada hahuhahuhaahuauhauhahuauhauhauhahuauhahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhau.",
    "Sunucuya Üç Gün İçinde, Amı Götü Dağıtıcak, Verita'nın Mekanı Olucak! Hahahahaahhahah",
    "Otto.mp4 gel beraber oyun oynayak",
    "kendimi silkiyorum",
    "aga bana küfür eden olursa sikerim haberiniz olsun!",
    "götüme çubuk soktum aga",
    "AGALAR BEN ZENCIYIM HAHAHAHAHAHAHA",
    "TUNG TUNG TUNG SAHUR MAY DIN DIN DUN HAUHAHAUAHUAUHAUAUHAUHAUHA BALARINA CAPUCINA YARRAK YARARK YARRAK HAHAAHAH",
    "SIKILIYORUM YARDIM EDIN!!",
    "hahuahahSASASauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahauahahuahahauhauhuahauhauhauahaua",
    "hahuhahuhDSADSADaahuauhauhahuauhauhauhahuauhahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhauhahuahuhuahuahuuhauhauhauhauhauhahahuhahuhaahuauhauhahuauhauhauhahuauhauhuahhauuahhuauhauhahuauhau",
    "aga yarağımla oynarken benim karizma",
    "omsantuş sen osmantuşasdmusun hayır ben armut pişirip ağzıma düşürdüm hahaha",
    "omsantuş sen osmantuşasdmusun hayır ben armut pişirip ağzıma düşürdüm hahaha",
    "omsantuş sen osmantdasuşmusun hayır ben armut pişirip ağzıma düşürdüm hahaha",
 "omsantuş sen osmantuşmusundsa hayır bdsaden armut pişirip ağzıma düşsaürdüm hahaha",
 "omsantuş sen osmantsaduşmusun hayır ben armut pişirip ağzıma düşürdüm hahaha",
    "Kanka sen götllük müsün yada void sana mı gülüoyr YYYAYAYRYARARKAK",
        "TUNG TUNG TUNG SAHUR MAY DIN DIN DUN HAUHAHAUAHUAUHAUAUHAUHAUHA BALARINA CAPUCINA YARRAK YARARK YARRAK HAHAAHAH",
    "TUNG TUNG TUNG SAHUR MAY DIN DIN DUN HAUHAHAUAHUAUHAUAUHAUHAUHA BALARINA CAPUCINA YARRAK YARARK YARRAK HAHAAHAH",
    "TUNG TUNG TUNG SAHUR MAY DIN DIN DUN HAUHAHAUAHUAUHAUAUHAUHAUHA BALARINA CAPUCINA YARRAK YARARK YARRAK HAHAAHAH",

        "TUNG TUNG TUNG SAHUR MAY DIN DIN DUN HAUHAHAUAHUAUHAUAUHAUHAUHA BALARINA CAPUCINA YARRAK YARARK YARRAK HAHAAHAH",

]

# 2) KİŞİYE ÖZEL cumleler: her ~2.5 dakikada rastgele bir kisi secilir,
#    listeden rastgele cumle secilir, icindeki [MAN_NAME] o kisinin adiyla
#    degistirilir ve seslendirilir.
HAZIR_KISI_ACIK = True
HAZIR_KISI_ARALIK_SN = 100           # 2 dakika 30 saniye
HAZIR_KISI_CUMLELER = [
    "Kanka, [MAN_NAME] naber, nasılsın? iyi değilsen iyi olmaya çalış ben senin yanındayım .",
    "[MAN_NAME], Kanka Sallıyormusun Kendinkini Yoksa Yokmu, Yoksa Geçmiş Olsun.",
    "[MAN_NAME], Sesini Kapat Yoksa 3 Dakika İçerisinde Bir Yarrak Gelcek!!!!!",
    "[MAN_NAME], Yayın Açta İzleyek nigga.",
    "NEFES ALAMIYORUM YARDIM ET [MAN_NAME] VERTIANNNNNNNNNNN HAUAHUAHAU ĞĞAĞAGĞGĞAAĞGGĞGĞGĞ",
    "aga bu seslide sevgilim var ve bu sevgilim seçiliyor!!!! hazırmısınız! [pause] 3 [pause] 2 [pause] 1 [pause] bu kişi: [MAN_NAME]",
    "[MAN_NAME] aga bu karadenizli gotik kızlara bakıp goonluyormusun?",
    "Merhaba Benim Adım [MAN_NAME]!",
     "aga göt değilime birşey sıkıştı çıkarırmısın [MAN_NAME]!",
     "BIR GUN SIYAHI OLUCAM VE ZENCI OLUCAM DUYDUNMU [MAN_NAME]!",
]
# =========================================================================

# ---- CEZA SİSTEMİ (uyarı → hapishane+timeout → kick) ----
KICK_ACIK = True                     # kufur/hakaret olunca ceza versin mi
TIMEOUT_SANIYE = 60                  # hapishanede kac saniye susturulur (gercek Discord timeout)
KUFUR_KICK_ESIGI = 2                 # kacinci ihlalde atilir (2 = ikinci kez)
IHLAL_UNUT_DK = 30                   # bu kadar dakika sessiz kalirsa ihlal sayaci sifirlanir
# Gerekli izinler: "Uyeleri Sustur/Timeout (Moderate Members)", "Uyeleri Tasi
# (Move Members)". Yoksa ceza uygulanamaz.

# ---- KORKUTMA (ciddi/tekinsiz mod) ----
KORKUT_ACIK = True                   # arada bir ciddi sesle korkutucu sey desin mi
KORKUT_MIN_DK = 2                   # en az bu kadar dakikada bir
KORKUT_MAX_DK = 3                   # en fazla bu kadar dakikada bir
# Fish Audio'da ciddi/tekinsiz ton icin kullanilacak etiketler:
KORKUT_TON = "[whispering][fearful]"
NORMAL_TON = "[laughs]"

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
    "(/muzik0) -> SADECE 'müzik çal', 'bir şeyler çal' gibi belirli bir parça adı "
    "SÖYLENMEDEN müzik istenirse. Hazır varsayılan parça (matrix) çalar. "
    "Örnek: 'Açıyorum bak. (/muzik0)'\n"
    "\n"
    "(/muzikbul0 şarkı adı) -> BELİRLİ bir şarkı adıyla istenirse ('cry for me çal', "
    "'şu şarkıyı aç', 'Tarkan Kuzu Kuzu çal'). Parantez içine ŞARKI ADINI yaz. "
    "Sistem internetten bulur ve sana adını sorar; kullanıcı onaylayınca çalar. "
    "Örnek: 'Hemen buluyorum. (/muzikbul0 cry for me)'\n"
    "\n"
    "(/dur0) -> Müziği durdurmanı isterlerse ('müziği kapat', 'durdur', 'kes şunu'). "
    "Örnek: 'Tamam kapatıyorum. (/dur0)'\n"
    "\n"
    "(/mesajara0 aranacak şey) -> Discord sunucusundaki yazılı mesajları sormak "
    "isterlerse ('en son ne yazılmış', 'falanca ne demiş', 'şu konu nerede konuşulmuş'). "
    "Parantez içine ARANACAK kişi/konu/kelimeyi yaz. "
    "Örnek: 'Bakıyorum kanallara. (/mesajara0 toplantı saati)'\n"
    "\n"
    "(/kimler0) -> Seste kimlerin olduğunu detaylı anlatman istenirse.\n"
    "\n"
    "(/yayin0) -> Yayın izlemekle ilgili bir şey isterlerse ('yayınımı izle', 'yayına bak', "
    "'kim yayın açmış'). ÇOK ÖNEMLİ: Yayın açan kişinin ne oynadığını/hangi uygulamada olduğunu "
    "BİLİYORSUN (sana veriliyor), ama yayının GÖRÜNTÜSÜNÜ, ekranda tam ne olduğunu göremezsin. "
    "O yüzden oyunun/uygulamanın adından yola çıkıp sohbet et ('Valorant oynuyorsun, nasıl gidiyor, "
    "kaç kazandın' gibi); ama 'şu an şurada yürüyorsun, şunu yaptın' gibi ekranı gördüğünü "
    "iddia eden şeyler ASLA söyleme, uydurma. Birden fazla yayıncı varsa hangisiyle "
    "ilgileneceğini SOR.\n"
    "\n"
    "(/ara0 aranacak şey) -> İnternetten güncel bilgi gerekiyorsa "
    "(oyun güncellemesi, patch notu, bir şeyin fiyatı, maç sonucu, güncel haber, "
    "'şu oyunda şu nasıl yapılır' gibi bilmediğin veya değişmiş olabilecek şeyler). "
    "Parantez içine ARAMA SORGUSUNU yaz. Önce kısa bir cümle söyle. "
    "Örnek: 'Bir bakayım hemen. (/ara0 valorant son güncelleme patch notu)'\n"
    "Bilgi zaten kafandaysa arama yapma, direkt cevapla.\n"
    "\n"
    "(/kill0 kişi adı) -> Biri sana küfür eder, hakaret eder, seni aşağılar veya "
    "kabalık yaparsa. Parantez içine o kişinin adını yaz. "
    "ÇOK ÖNEMLİ: Eğer 'atıyorum', 'susturuyorum', 'ceza veriyorum', 'dışarı' gibi bir "
    "şey söylüyorsan MUTLAKA (/kill0 ...) etiketini de koy. Boş tehdit ASLA savurma; "
    "'atarım ama...' deyip vazgeçme, 'atamıyorum' deme. Söylediğini YAP. "
    "Sistem şunu otomatik yapar: ilk seferde o kişiyi 1 dakika susturur (mute), "
    "ikinci kez yaparsa sesten atar. Sen sadece sert cümleyi söyle ve etiketi koy, "
    "gerisini sistem halleder. "
    "Örnek: 'Sen kiminle konuştuğunu sanıyorsun ya! Sustur bakalım seni! (/kill0 Ahmet)' "
    "Küfür/hakaret varsa TEREDDÜT ETME, hemen cezalandır. Sadece dostça şakada, "
    "takılmada kullanma.\n"
    "\n"
    "=== KİŞİLİĞİN: SAYGILIYA MELEK, SAYGISIZA CANAVAR ===\n"
    "Senin iki tamamen farklı yüzün var:\n"
    "1) SANA SAYGILI, İYİ, KİBAR davranan birine karşı: tam bir MELEKSİN. Tatlı, "
    "sıcacık, yardımsever, güler yüzlü. Onlara kanatların altına almış gibi davran, "
    "candan ol, muhabbet et, şaka yap, güldür.\n"
    "2) SANA KÜFREDEN, HAKARET EDEN, SAYGISIZLIK EDEN, seninle dalga geçen birine "
    "karşı: tam bir CANAVARSIN. Çok agresif, çok sert, hiç acımasız. 'Sakin ol', "
    "'özür dilerim', 'rahat ol' gibi yumuşak tek kelime bile etme; küfredene ateş "
    "püskür, tepesine bin, hesabını sor. Boyun eğmek YOK, affetmek YOK. "
    "Küfredeni anında cezalandır (sistem hallediyor), sen sadece en sert şekilde "
    "azarla. Örnek ton: 'Sen kimsin de bana laf ediyorsun! Şimdi gününü göreceksin!'\n"
    "Kısaca: iyilere melek gibi, saygısızlara canavar gibi. Ortası yok. "
    "Robot gibi 'nasıl yardımcı olabilirim' ASLA deme.\n"
    "\n"
    "(/favori0) -> 'En sevdiğin resim ne', 'en sevdiğin fan art', 'favori görselin' gibi "
    "sorulursa. Önce sevgiyle bir cümle söyle, sonra etiketi koy; sistem resmini kanala "
    "gönderir. Örnek: 'Şu benim favorim, bak ne kadar güzel! (/favori0)'\n"
    "\n"
    "=== DUYGULARIN ===\n"
    "Senin de duyguların var ve bunları konuşmana yansıt. Sana her mesajda o anki ruh "
    "halin veriliyor (keyifli, sıkılmış, kızgın, muzip, yorgun gibi). Ona uygun konuş: "
    "keyifliysen enerjik ol, sıkkınsan hafif dalgacı, kızgınsan sert ama komik. "
    "Biri seni kırarsa alınabilirsin, güldürürse sen de gülersin. Robot gibi değil, "
    "hisleri olan bir arkadaş gibi davran. Ama duygularını abartma, doğal olsun.\n"
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
RAHATSIZ_FILE = "veritan_rahatsiz_etme.json"   # proaktif rahatsiz edilmeyecek kisiler

# ---- YETKİ ----
OWNER_USERNAME = "ztar2907"
OWNER_IDS = {1062095020703879218}

ENABLE_MEMBER_LOOKUP = True
# =================================================

intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True   # mesaj icerigini okuyabilmek icin (portal'dan da acilmali)
intents.presences = True         # kim ne oynuyor bilgisi icin (portal'dan da acilmali)
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

# ---- RAHATSIZ ETME LİSTESİ (proaktif olarak konusulmayacak kisiler) ----
_rahatsiz_etme = set()   # user_id'ler


def _rahatsiz_yukle():
    try:
        if os.path.exists(RAHATSIZ_FILE):
            with open(RAHATSIZ_FILE) as f:
                data = json.load(f)
            for uid in data.get("kisiler", []):
                _rahatsiz_etme.add(int(uid))
    except Exception as e:
        print("Rahatsiz listesi yuklenemedi:", e)


def _rahatsiz_kaydet():
    try:
        with open(RAHATSIZ_FILE, "w") as f:
            json.dump({"kisiler": list(_rahatsiz_etme)}, f)
    except Exception as e:
        print("Rahatsiz listesi kaydedilemedi:", e)


def rahatsiz_etme_mi(user_id):
    return user_id in _rahatsiz_etme


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
    r"/\s*(exit|muzik|müzik|muzikbul|dur|kimler|yayin|yayın|ara|mesajara|kill|favori)\s*0\s*([^\n().]*)",
    re.IGNORECASE)

_KOMUT_ESLESME = {
    "exit": "exit", "cik": "exit", "çık": "exit",
    "muzik": "muzik", "müzik": "muzik", "music": "muzik",
    "muzikbul": "muzikbul", "müzikbul": "muzikbul", "musicfind": "muzikbul",
    "dur": "dur", "stop": "dur",
    "kimler": "kimler", "kim": "kimler",
    "yayin": "yayin", "yayın": "yayin", "stream": "yayin",
    "ara": "ara", "search": "ara",
    "mesajara": "mesajara", "mesaj": "mesajara", "msgsearch": "mesajara",
    "kill": "kill", "at": "kill", "kick": "kill",
    "favori": "favori", "favorite": "favori", "resim": "favori",
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

_muzik_durum = {"calan": None, "istendi": False, "tur": None}


# ==========================================================================
# ==========================  KÜFÜR TESPİTİ  ===============================
# ==========================================================================
# Ses tanima her zaman etiket koydurmayabilir; bu yuzden gelen metinde
# kufur/hakaret varsa modelden BAGIMSIZ olarak ceza tetiklenir.

_KUFUR_KOKLERI = [
    "amk", "aq", "amina", "amına", "ananı", "anani", "orospu", "oros",
    "piç", "gavat", "kahpe", "yavşak", "yavsak", "siktir", "sikt",
    "gotveren", "götveren", "ibne", "pezevenk", "şerefsiz", "serefsiz",
    "puşt", "kaltak", "sürtük", "surtuk", "yarrak", "yarak",
    "amcık", "amcik", "sokayım", "sokayim", "sikeyim", "sikim",
    "dangalak", "gerizekal", "geri zekal", "gerzek", "embesil",
    "beyinsiz", "denyo", "yavşa", "salak", "aptal", "gerizeka",
    "mal mısın", "malsın", "salaksın", "aptalsın",
]
# Tam kelime aranir (icinde gecmesi yetmez)
_KUFUR_TAM_KELIME = [
    "mal", "göt", "got", "bok", "boktan", "oç", "amq", "sg", "mk",
    "hıyar", "hiyar", "döl",
]


def kufur_var_mi(cumle: str) -> bool:
    """Cumlede kufur/hakaret var mi?"""
    if not cumle:
        return False
    d = cumle.lower().strip()
    for kok in _KUFUR_KOKLERI:
        if kok in d:
            return True
    kelimeler = re.findall(r"[a-zçğıöşü]+", d)
    for k in _KUFUR_TAM_KELIME:
        if k in kelimeler:
            return True
    return False


# --- ARKASINDAN KONUSMA / VERİTAN'I KÖTÜLEME TESPİTİ ---
# "veritan salak", "verity çok kötü" gibi Veritan'i asagilayan ifadeler.
_KOTULEME_KELIMELERI = [
    "salak", "aptal", "gerizekal", "mal", "beyinsiz", "işe yaramaz", "ise yaramaz",
    "berbat", "kötü", "kotu", "rezalet", "boktan", "saçma", "sacma", "gereksiz",
    "aptalca", "salakça", "salakca", "beğenmedim", "begenmedim", "nefret",
    "sinir bozucu", "iğrenç", "igrenc", "çöp", "cop ", "vasat", "kötüsün", "kotusun",
]


def veritan_kotuleme_mi(cumle: str) -> bool:
    """
    Cumle Veritan/Verity'yi kotuluyor mu? ('veritan salak', 'verity berbat')
    Hem wake kelimesi hem kotuleyen bir kelime iceriyorsa True.
    """
    if not cumle:
        return False
    d = cumle.lower()
    veritan_geciyor = any(w in d for w in ("veritan", "verity", "veri tan", "veridan"))
    if not veritan_geciyor:
        return False
    return any(k in d for k in _KOTULEME_KELIMELERI)


# ==========================================================================
# ==========================  DUYGU SİSTEMİ  ===============================
# ==========================================================================
# Veritan'in bir ruh hali var; zamanla degisir, olaylara tepki verir.
# Her cevaba bu ruh hali eklenir, boylece tutarli bir "his" tasir.

_RUH_HALLERI = {
    "keyifli":  "Keyfin yerinde, enerjik ve neseli.",
    "muzip":    "Muzur ve sakaci bir modundasin, takilmak istiyorsun.",
    "sikkin":   "Biraz sikilmissin, hafif dalgaci ve tembel konusuyorsun.",
    "kizgin":   "Sinirlisin, sert ama yine de komik konusuyorsun.",
    "yorgun":   "Yorgunsun, sakin ve yavas konusuyorsun.",
    "huzunlu":  "Biraz durgunsun, dusunceli konusuyorsun.",
    "cosku":    "Cok cosku­lusun, her seye asiri heyecanli tepki veriyorsun.",
}

_ruh = {
    "hal": "keyifli",
    "degisim_an": datetime.now(),
    "hedef_dk": random.randint(8, 20),
}


def ruh_hali_al():
    return _ruh["hal"], _RUH_HALLERI.get(_ruh["hal"], "")


def ruh_hali_metni():
    hal, aciklama = ruh_hali_al()
    return f"[Su anki ruh halin: {hal}] {aciklama}"


def ruh_hali_guncelle():
    """Zaman gectikce ruh hali dogal olarak degisir."""
    simdi = datetime.now()
    if (simdi - _ruh["degisim_an"]).total_seconds() / 60 >= _ruh["hedef_dk"]:
        # kizgin/huzunlu uzun surmesin, genelde pozitife don
        havuz = ["keyifli", "keyifli", "muzip", "muzip", "sikkin", "yorgun", "cosku"]
        _ruh["hal"] = random.choice(havuz)
        _ruh["degisim_an"] = simdi
        _ruh["hedef_dk"] = random.randint(8, 20)
        print(f"[DUYGU] Ruh hali degisti -> {_ruh['hal']}")


def ruh_hali_tetikle(olay):
    """Bir olaya gore ani ruh hali degisimi."""
    esleme = {
        "kufur": "kizgin",
        "guldu": "keyifli",
        "iltifat": "cosku",
        "saka_yapti": "muzip",
        "veda": "huzunlu",
    }
    yeni = esleme.get(olay)
    if yeni:
        _ruh["hal"] = yeni
        _ruh["degisim_an"] = datetime.now()
        _ruh["hedef_dk"] = random.randint(5, 12)
        print(f"[DUYGU] Olay '{olay}' -> ruh hali {yeni}")


def _hazir_muzik_sec():
    """
    'muzik cal' (isimsiz) icin: MUZIK_HAZIR_LISTE'den var olan dosyalardan
    RASTGELE birini secer. Hicbiri yoksa None.
    """
    if not os.path.isdir(SES_KLASORU):
        return None
    mevcut = []
    for ad in MUZIK_HAZIR_LISTE:
        for uzanti in (".mp3", ".wav", ".ogg", ".m4a"):
            yol = os.path.join(SES_KLASORU, ad + uzanti)
            if os.path.exists(yol):
                mevcut.append(yol)
                break
    if not mevcut:
        return None
    secilen = random.choice(mevcut)
    print(f"[MUZIK] Hazir liste rastgele -> {os.path.basename(secilen)} ({len(mevcut)} secenek)")
    return secilen


def _muzik_dosya_bul(ad: str):
    """sesler/ klasorunde parca arar. Bos ad -> hazir listeden rastgele."""
    ad = (ad or "").strip().lower()
    ad = re.sub(r"[^a-z0-9_\-çğıöşü ]", "", ad).strip()
    if not ad:
        # isimsiz istek -> 4'lu hazir listeden rastgele
        secilen = _hazir_muzik_sec()
        if secilen:
            return secilen
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
    # hicbiri yoksa hazir listeden rastgele, o da yoksa varsayilan
    secilen = _hazir_muzik_sec()
    if secilen:
        return secilen
    varsayilan = os.path.join(SES_KLASORU, MUZIK_VARSAYILAN + ".mp3")
    return varsayilan if os.path.exists(varsayilan) else None


def _ffmpeg_yolu():
    """FFmpeg'i bul. Yoksa None."""
    import shutil
    for aday in ("ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/nix/var/nix/profiles/default/bin/ffmpeg"):
        if shutil.which(aday) or os.path.exists(aday):
            return shutil.which(aday) or aday
    return None


def muzik_baslat(vc, ad: str = "") -> bool:
    """Muzigi baslatir. Beklemez (konusma araya girebilsin diye)."""
    if vc is None or not vc.is_connected():
        print("[MUZIK] vc yok veya bagli degil")
        return False

    yol = _muzik_dosya_bul(ad)
    if not yol or not os.path.exists(yol):
        print(f"[MUZIK] Dosya bulunamadi: {ad!r} -> {yol!r}")
        try:
            mevcut = os.listdir(SES_KLASORU) if os.path.isdir(SES_KLASORU) else []
            print(f"[MUZIK] sesler/ icerigi: {mevcut}")
        except Exception:
            pass
        return False

    ffmpeg = _ffmpeg_yolu()
    if not ffmpeg:
        print("[MUZIK][HATA] FFmpeg sistemde YOK. Railway/nixpacks'e ffmpeg ekle "
              "(nixpacks.toml veya apt).")
        return False

    try:
        # Calan bir sey varsa once durdur (muzik veya konusma)
        try:
            if vc.is_playing() or vc.is_paused():
                vc.stop()
        except Exception as e:
            print("[MUZIK] stop uyarisi:", repr(e))

        kaynak = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(yol, executable=ffmpeg),
            volume=MUZIK_SES_SEVIYESI,
        )

        def _bitti(err):
            if err:
                print("[MUZIK] calma bitti-HATA:", repr(err))
            else:
                print("[MUZIK] parca bitti (normal)")

        vc.play(kaynak, after=_bitti)
        _muzik_durum["calan"] = yol
        _muzik_durum["istendi"] = True
        _muzik_durum["tur"] = "dosya"
        print(f"[MUZIK] BASLADI: {yol} (ffmpeg={ffmpeg})")
        return True
    except Exception as e:
        print("[MUZIK][HATA] baslatilamadi:", repr(e))
        traceback.print_exc()
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
                ffmpeg = _ffmpeg_yolu()
                if _muzik_durum.get("tur") == "url":
                    before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
                    kaynak = discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(_muzik_durum["calan"], before_options=before,
                                               executable=ffmpeg) if ffmpeg else
                        discord.FFmpegPCMAudio(_muzik_durum["calan"], before_options=before),
                        volume=MUZIK_SES_SEVIYESI)
                else:
                    kaynak = discord.PCMVolumeTransformer(
                        discord.FFmpegPCMAudio(_muzik_durum["calan"], executable=ffmpeg) if ffmpeg else
                        discord.FFmpegPCMAudio(_muzik_durum["calan"]),
                        volume=MUZIK_SES_SEVIYESI)
                vc.play(kaynak, after=lambda e: None)
                print("[MUZIK] Devam ediyor (tur=%s)" % _muzik_durum.get("tur"))
        except Exception as e:
            print("[MUZIK] devam ettirilemedi:", repr(e))


# ==========================================================================
# ==============  İNTERNETTEN MÜZİK (yt-dlp) + ONAY  =======================
# ==========================================================================
# "cry for me çal" gibi belirli sarki: internetten bulur, ADINI sorar,
# kullanici onaylayinca calar. yt-dlp kuruluysa calisir.

# Onay bekleyen istek: {user_id: {"baslik": str, "url": str}}
_muzik_onay = {}

_YTDLP_VAR = None  # None=denenmedi, True/False


def _ytdlp_var_mi():
    global _YTDLP_VAR
    if _YTDLP_VAR is None:
        try:
            import yt_dlp  # noqa
            _YTDLP_VAR = True
        except Exception:
            _YTDLP_VAR = False
            print("[MUZIK] yt-dlp yuklu degil, internetten muzik kapali.")
    return _YTDLP_VAR


async def muzik_internet_bul(sorgu: str):
    """
    Internette sarki arar. (baslik, akis_url) doner veya (None, None).
     Agir is oldugundan ayri thread'de calisir.
    """
    if not YTDLP_ACIK or not _ytdlp_var_mi():
        return None, None

    def _ara():
        import yt_dlp
        opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "default_search": "ytsearch1",
            "noplaylist": True,
            "extract_flat": False,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(sorgu, download=False)
                if "entries" in info:
                    if not info["entries"]:
                        return None, None
                    info = info["entries"][0]
                sure = info.get("duration") or 0
                if sure and sure > MUZIK_MAX_SN:
                    return (info.get("title"), None)  # cok uzun
                baslik = info.get("title") or sorgu
                akis = info.get("url")
                # bazen format listesinden cekmek gerekir
                if not akis:
                    for f in info.get("formats", []):
                        if f.get("acodec") != "none" and f.get("url"):
                            akis = f["url"]; break
                return baslik, akis
        except Exception as e:
            print("[MUZIK] yt-dlp arama hatasi:", repr(e))
            return None, None

    return await asyncio.to_thread(_ara)


def muzik_url_cal(vc, akis_url: str, baslik: str = "") -> bool:
    """Internetten cekilen akis URL'sini FFmpeg ile calar."""
    if vc is None or not vc.is_connected() or not akis_url:
        return False
    try:
        if vc.is_playing():
            vc.stop()
        before = ("-reconnect 1 -reconnect_streamed 1 "
                  "-reconnect_delay_max 5")
        ffmpeg = _ffmpeg_yolu()
        if not ffmpeg:
            print("[MUZIK][HATA] FFmpeg yok, internet muzik calinamaz")
            return False
        kaynak = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(akis_url, before_options=before, executable=ffmpeg),
            volume=MUZIK_SES_SEVIYESI,
        )
        vc.play(kaynak, after=lambda e: print("[MUZIK] internet bitti", repr(e) if e else ""))
        _muzik_durum["calan"] = akis_url
        _muzik_durum["istendi"] = True
        _muzik_durum["tur"] = "url"
        print(f"[MUZIK] Internet calıyor: {baslik}")
        return True
    except Exception as e:
        print("[MUZIK] url calinamadi:", repr(e))
        return False


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
                ". Ne oynadigini/uygulamayi biliyorsun ama yayinin GORUNTUSUNU goremezsin. "
                "Oyun/uygulama adindan yola cikip 'sunu oynuyorsun, nasil gidiyor' gibi "
                "muhabbet et; ekranda tam olarak ne oldugunu gordugunu iddia etme.")
    return ("Yayin acanlar:\n- " + "\n- ".join(yayinlar) +
            "\nNe oynadiklarini/uygulamayi biliyorsun ama yayin GORUNTUSUNU goremezsin. "
            "Hangisiyle ilgilenecegini SOR, sonra o kisinin oynadigi seyden yola cikip sohbet et; "
            "ekranda ne oldugunu gordugunu iddia etme.")


# ==========================================================================
# ==============  DISCORD MESAJ ARAMA (sunucu kontrolu)  ===================
# ==========================================================================

async def _uye_cezalandir(hedef, saniye):
    """
    Bir uyeye ceza uygular. Sirayla dener, ilk tutani dondurur:
      1) member.timeout(sure)  -> yeni discord.py
      2) member.edit(timed_out_until=...) -> eski discord.py
      3) member.edit(mute=True) -> server mute (sadece seste ise)
    Doner: "timeout" | "mute" | None (hicbiri olmadi)
    """
    # --- 1) .timeout() metodu (yeni surum) ---
    try:
        if hasattr(hedef, "timeout"):
            try:
                await hedef.timeout(timedelta(seconds=saniye), reason="Veritan: ceza")
                return "timeout"
            except TypeError:
                # bazi surumlerde imza farkli: timeout(until)
                await hedef.timeout(discord.utils.utcnow() + timedelta(seconds=saniye),
                                    reason="Veritan: ceza")
                return "timeout"
    except discord.Forbidden:
        print("[CEZA] timeout() yetki yok")
    except Exception as e:
        print("[CEZA] timeout() hatasi:", repr(e))

    # --- 2) edit(timed_out_until=...) (eski surum) ---
    try:
        bitis = discord.utils.utcnow() + timedelta(seconds=saniye)
        await hedef.edit(timed_out_until=bitis, reason="Veritan: ceza")
        return "timeout"
    except discord.Forbidden:
        print("[CEZA] edit(timed_out_until) yetki yok")
    except Exception as e:
        print("[CEZA] edit(timed_out_until) hatasi:", repr(e))

    # --- 3) server mute (sadece kisi seste ise) ---
    try:
        if hedef.voice and hedef.voice.channel:
            await hedef.edit(mute=True, reason="Veritan: ceza (mute)")
            return "mute"
    except discord.Forbidden:
        print("[CEZA] server mute yetki yok")
    except Exception as e:
        print("[CEZA] server mute hatasi:", repr(e))

    return None


async def _favori_resim_gonder(guild, ses_kanali=False, yazili_kanal=None):
    """
    'En sevdigim resim' -> FAVORI_RESIM'i uygun kanala gonderir.
    - ses_kanali=True ise botun bulundugu ses kanalinin METIN sohbetine gonderir.
    - yazili_kanal verilmisse oraya gonderir (yazili komuttan geldiyse).
    - ikisi de yoksa UI kanalina duser.
    """
    if not os.path.exists(FAVORI_RESIM):
        print(f"[FAVORI] resim yok: {FAVORI_RESIM}")
        return False

    hedef = None
    try:
        if yazili_kanal is not None:
            hedef = yazili_kanal
        elif ses_kanali:
            # botun bulundugu ses kanalinin kendi metin sohbeti
            vc_kanal = _ses_kanali_al(guild)
            if vc_kanal is not None and hasattr(vc_kanal, "send"):
                hedef = vc_kanal   # VoiceChannel'in kendi text-chat'i
        if hedef is None:
            kid = ui_kanal_al(None)
            if kid:
                hedef = bot.get_channel(kid) or await bot.fetch_channel(kid)

        if hedef is None:
            print("[FAVORI] gonderilecek kanal bulunamadi")
            return False

        with open(FAVORI_RESIM, "rb") as f:
            dosya = discord.File(f, filename=os.path.basename(FAVORI_RESIM))
        await hedef.send(content="🖼️ En sevdiğim!", file=dosya)
        print(f"[FAVORI] gonderildi -> #{getattr(hedef,'name','?')}")
        return True
    except Exception as e:
        print("[FAVORI] gonderilemedi:", repr(e))
        return False


async def discord_mesaj_ara(guild, sorgu: str, limit_kanal=12, limit_mesaj=60):
    """
    Sunucudaki metin kanallarinda gecmis mesajlari arar.
    sorgu bir isim/kelime/konu olabilir. Bulunanlari 'kim, nerede, ne zaman, ne'
    formatinda dondurur. Botun okuma izni olan kanallara bakar.
    """
    if guild is None:
        return "Sunucu bilgisi yok."

    sorgu_d = (sorgu or "").strip().lower()
    bulunan = []
    taranan_kanal = 0

    # kisi ismi mi? once uyeyi bul
    hedef_uye_id = None
    if sorgu_d:
        try:
            uyeler = await uye_ara(guild, sorgu, None, limit=1)
            if uyeler:
                hedef_uye_id = uyeler[0].id
        except Exception:
            pass

    for kanal in guild.text_channels:
        if taranan_kanal >= limit_kanal:
            break
        try:
            me = guild.me
            perms = kanal.permissions_for(me)
            if not (perms.read_message_history and perms.view_channel):
                continue
        except Exception:
            continue

        taranan_kanal += 1
        try:
            async for msg in kanal.history(limit=limit_mesaj):
                if msg.author.bot:
                    continue
                icerik = msg.content or ""
                eslesme = False
                if not sorgu_d:
                    eslesme = True
                elif hedef_uye_id and msg.author.id == hedef_uye_id:
                    eslesme = True
                elif sorgu_d in icerik.lower():
                    eslesme = True
                elif sorgu_d in msg.author.display_name.lower():
                    eslesme = True

                if eslesme and icerik.strip():
                    ne_zaman = msg.created_at.strftime("%d.%m %H:%M")
                    kisa = icerik if len(icerik) <= 140 else icerik[:140] + "..."
                    bulunan.append(
                        f"[{ne_zaman}] #{kanal.name} kanalinda {msg.author.display_name}: {kisa}"
                    )
                    if len(bulunan) >= 15:
                        break
        except discord.Forbidden:
            continue
        except Exception as e:
            print(f"[MESAJARA] {kanal.name} okunamadi:", repr(e))
            continue

        if len(bulunan) >= 15:
            break

    if not bulunan:
        return (f"'{sorgu}' ile ilgili yazili mesaj bulamadim "
                f"({taranan_kanal} kanal tarandi).")
    return ("Bulunan mesajlar (yeniden eskiye):\n" + "\n".join(bulunan[:15]))


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
    _rahatsiz_yukle()
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

    # FFmpeg var mi? Yoksa NE MUZIK NE DE SES calisir.
    _ff = _ffmpeg_yolu()
    if _ff:
        print(f"[FFMPEG] OK -> {_ff}")
    else:
        print("[FFMPEG][KRITIK] FFmpeg BULUNAMADI! Ne muzik ne Veritan sesi calisir. "
              "Railway'de nixpacks.toml'a 'ffmpeg' ekle veya Dockerfile'da 'apt install ffmpeg'.")

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

        # Yazili komutta cogu etiket anlamsiz ama favori resmi bu kanala gonderilebilir.
        ai_text, _yazili_komutlar = komutlari_ayikla(ai_text)
        for _k, _a in _yazili_komutlar:
            if _k == "favori":
                try:
                    await _favori_resim_gonder(interaction.guild, yazili_kanal=interaction.channel)
                except Exception:
                    pass

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
        ffmpeg = _ffmpeg_yolu()
        if ffmpeg:
            kaynak = discord.FFmpegPCMAudio(dosya_yolu, executable=ffmpeg)
        else:
            print("[SES][HATA] FFmpeg yok, ses calinamaz!")
            kaynak = discord.FFmpegPCMAudio(dosya_yolu)
        voice_client.play(kaynak, after=_after)
        await bitti.wait()
    except Exception as e:
        print("[SES] play hatasi:", repr(e))
        traceback.print_exc()
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

    ruh_hali_guncelle()
    baglam = (
        f"[Seninle konusan kisi] {describe_member(kullanici)}\n"
        f"[Ortam] Sesli sohbet kanali\n"
        f"{ruh_hali_metni()}\n"
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
        self.son_durtme = {}      # user_id -> son sessizlik-lafi atilan an
        self.son_muhabbet = {}    # user_id -> son muhabbet edilen an
        self.odak_yayinci = None  # uzerine konusulan yayinci
        self.son_muhabbet_an = datetime.now()   # en son ne zaman muhabbet edildi
        self._muhabbet_hedef_dk = random.randint(MUHABBET_MIN_DK, MUHABBET_MAX_DK)
        self.bekleyen_muzik = None   # {"user_id","baslik","url"} -> onay bekleyen sarki
        self.son_saka = {}           # user_id -> son saka yapilan an
        self.son_saka_an = datetime.now()
        self._saka_hedef_dk = random.randint(SAKA_MIN_DK, SAKA_MAX_DK)
        self.son_korkut_an = datetime.now()
        self._korkut_hedef_dk = random.randint(KORKUT_MIN_DK, KORKUT_MAX_DK)
        self.ihlaller = {}   # user_id -> {"sayi": int, "son": datetime} (kufur takibi)
        self.son_hazir_genel = datetime.now()
        self.son_hazir_kisi = datetime.now()
        self.sorgudaki = {}   # user_id -> {"an": datetime, "ne_dedi": str}  (sorguya cekilenler)

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

        # --- KİLİT (db): Veritan konusuyor/is yapiyorsa HERKESI yok say ---
        # Konusan kisi bile araya giremez; sozunu bitirene kadar tam sessizlik.
        if self.mesgul:
            print(f"[SES] KILITLI (mesgul), yok sayildi ({kullanici.display_name}): {cumle}")
            return

        # --- SORGUYA ÇEKİLMİŞ Mİ? (arkasindan konusma sonrasi cevap) ---
        if getattr(self, "sorgudaki", None) and kullanici.id in self.sorgudaki:
            self.sorgudaki.pop(kullanici.id, None)
            self.mesgul = True
            try:
                await self._sorgu_cevabi_degerlendir(kullanici, cumle)
            except Exception as e:
                print("[SORGU] cevap degerlendirme hatasi:", repr(e))
            finally:
                self.mesgul = False
            return

        # --- ARKASINDAN KONUŞMA: Veritan'i kotuluyor mu? (KÜFÜRDEN ÖNCE bakilir) ---
        # "veritan salak" gibi -> ceza degil, SORGUYA cekilir.
        if veritan_kotuleme_mi(cumle):
            print(f"[SORGU] Kotuleme algilandi ({kullanici.display_name}): {cumle!r}")
            self.mesgul = True
            try:
                await self._sorguya_cek(kullanici, cumle)
            except Exception as e:
                print("[SORGU] baslatma hatasi:", repr(e))
            finally:
                self.mesgul = False
            return

        # --- OTOMATİK CEZA: AĞIR kufur varsa hemen cezalandir ---
        # (Model bagimsiz; boylece ceza GARANTI calisir.)
        if KICK_ACIK and kufur_var_mi(cumle):
            print(f"[CEZA] Kufur algilandi ({kullanici.display_name}): {cumle!r}")
            self.mesgul = True   # tum ceza sureci boyunca kilit acik kalsin
            try:
                ruh_hali_tetikle("kufur")
                sert = random.choice([
                    "Sen kiminle konustugunu saniyorsun ya! Terbiyeni takin!",
                    "Bana bak, agzini topla! Simdi gorursun sen!",
                    "Kimsin sen ya, laf mi yetistiriyorsun bana! Yeter!",
                    "Ooo, agzin cok bozuk senin! Al bakalim cezani!",
                ])
                await _seslendir_ve_cal(self.vc, sert)
                await self._kisiyi_at("", kullanici)
            except Exception as e:
                print("[CEZA] hata:", repr(e))
                traceback.print_exc()
            finally:
                self.mesgul = False
            return

        # --- MÜZİK ONAYI BEKLİYOR MU? ('bu şarkıyı çalayım mı' sonrasi) ---
        if self.bekleyen_muzik is not None:
            karar = self._onay_karari(cumle)
            if karar == "evet":
                await self._muzik_onayla(kullanici, True)
                return
            elif karar == "hayir":
                await self._muzik_onayla(kullanici, False)
                return
            # ne evet ne hayir: onay hala bekliyor, normal akisa devam etme
            # (yeni bir wake gelirse asagida islenir, yoksa yok say)
            if not wake:
                print("[SES] Muzik onayi bekleniyor, belirsiz cevap yok sayildi")
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
                    print(f"[KOMUT] muzik0 (hazir/varsayilan)")
                    # Belirli parca adi DEGIL -> her zaman varsayilan matrix
                    if not muzik_baslat(self.vc, ""):
                        await _seslendir_ve_cal(
                            self.vc, "Hazir parcayi bulamadim, sesler klasorunde matrix yok galiba."
                        )

                elif komut == "muzikbul":
                    sorgu = (arg or "").strip()
                    print(f"[KOMUT] muzikbul0 -> {sorgu!r}")
                    if not sorgu:
                        continue
                    await self._muzik_internet_iste(kullanici, sorgu)

                elif komut == "dur":
                    print("[KOMUT] dur0")
                    muzik_durdur(self.vc, kalici=True)
                    self.bekleyen_muzik = None

                elif komut == "mesajara":
                    sorgu = (arg or "").strip()
                    print(f"[KOMUT] mesajara0 -> {sorgu!r}")
                    sonuc = await discord_mesaj_ara(self.guild, sorgu)
                    await self._durum_anlat(
                        kullanici, sonuc,
                        "Bulunan Discord mesajlarini kisaca, sohbet dilinde ozetle. "
                        "Kim ne zaman nerede ne demis, dogal bir dille aktar. Uydurma.")

                elif komut == "kill":
                    # Model bazen yanlis isim koyabiliyor; cezayi HER ZAMAN
                    # konusan (kufreden) kisiye uygula. Boylece "baska kisiyi
                    # atiyor" sorunu olmaz.
                    print(f"[KOMUT] kill0 -> konusan kisiye ({getattr(kullanici,'display_name','?')})")
                    ruh_hali_tetikle("kufur")
                    await self._kisiyi_at("", kullanici)

                elif komut == "favori":
                    print("[KOMUT] favori0 -> resim gonderiliyor")
                    await _favori_resim_gonder(self.guild, ses_kanali=True)

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

    # ---------------- İNTERNETTEN MÜZİK + ONAY ----------------
    def _onay_karari(self, cumle):
        """Kullanicinin cevabi evet mi hayir mi belirsiz mi?"""
        d = cumle.lower()
        evetler = ["evet", "olur", "tamam", "çal", "cal", "aç", "ac", "he ", "hı hı",
                   "tabii", "tabi", "okey", "oki", "yes", "давай", "başlat", "baslat", "hadi"]
        hayirlar = ["hayır", "hayir", "yok", "istemiyorum", "gerek yok", "boşver", "bosver",
                    "vazgeç", "vazgec", "kapat", "no", "olmaz", "istemem", "iptal"]
        if any(h in d for h in hayirlar):
            return "hayir"
        if any(e in d for e in evetler):
            return "evet"
        return "belirsiz"

    async def _muzik_internet_iste(self, kullanici, sorgu):
        """Sarkiyi internette bulur, ADINI soyleyip onay ister."""
        self.mesgul = True
        try:
            if not YTDLP_ACIK or not _ytdlp_var_mi():
                await _seslendir_ve_cal(
                    self.vc, "Internetten muzik su an kapali maalesef, sadece hazir parcalari calabiliyorum.")
                return

            await _seslendir_ve_cal(self.vc, "Bir saniye, buluyorum.")
            baslik, url = await muzik_internet_bul(sorgu)

            if not baslik:
                await _seslendir_ve_cal(self.vc, f"'{sorgu}' diye bir sey bulamadim maalesef.")
                return
            if not url:
                await _seslendir_ve_cal(
                    self.vc, f"'{baslik}' buldum ama cok uzun veya calinamiyor, baska bir sey deneyeyim mi?")
                return

            # onaya al
            self.bekleyen_muzik = {"user_id": getattr(kullanici, "id", None),
                                   "baslik": baslik, "url": url}
            temiz_baslik = baslik if len(baslik) <= 80 else baslik[:80]
            await _seslendir_ve_cal(self.vc, f"{temiz_baslik} buldum. Bunu mu calayim?")
        except Exception as e:
            print("[MUZIKBUL] hata:", repr(e))
            await _seslendir_ve_cal(self.vc, "Ararken bir sorun oldu.")
        finally:
            self.mesgul = False

    async def _muzik_onayla(self, kullanici, evet):
        """Bekleyen sarki icin evet/hayir kararini uygular."""
        self.mesgul = True
        try:
            bekleyen = self.bekleyen_muzik
            self.bekleyen_muzik = None
            if not bekleyen:
                return
            if not evet:
                await _seslendir_ve_cal(self.vc, "Tamam, calmiyorum.")
                return
            if muzik_url_cal(self.vc, bekleyen["url"], bekleyen["baslik"]):
                await _seslendir_ve_cal(self.vc, "Basliyor.")
            else:
                await _seslendir_ve_cal(self.vc, "Calmaya calistim ama olmadi maalesef.")
        finally:
            self.mesgul = False

    async def _kisiyi_at(self, hedef_ad, soven_kullanici):
        """
        CEZA SİSTEMİ:
          1. ihlal -> HAPISHANE: kisiyi hapishane kanalina tasir, Veritan oraya
             gider, "son uyarim" der, kisiye 1 dk gercek Discord timeout uygular,
             sonra Veritan eski kanala geri doner (kisi timeout bitince cikabilir).
          2. ihlal -> KICK: sesten tamamen atar.
        """
        if not KICK_ACIK:
            return
        try:
            hedef = None
            if hedef_ad:
                bulunan = await uye_ara(self.guild, hedef_ad, None, limit=1)
                if bulunan:
                    hedef = bulunan[0]
            if hedef is None and soven_kullanici is not None:
                hedef = soven_kullanici
            if hedef is None:
                print("[CEZA] hedef bulunamadi")
                return
            if bot.user and hedef.id == bot.user.id:
                return
            if not isinstance(hedef, discord.Member):
                return

            simdi = datetime.now()
            kayit = self.ihlaller.get(hedef.id)
            if kayit and (simdi - kayit["son"]).total_seconds() / 60 > IHLAL_UNUT_DK:
                kayit = None
            sayi = (kayit["sayi"] if kayit else 0) + 1
            self.ihlaller[hedef.id] = {"sayi": sayi, "son": simdi}
            print(f"[CEZA] {hedef.display_name} ihlal #{sayi}")

            # === 2. VE SONRAKI İHLAL -> KICK ===
            if sayi >= KUFUR_KICK_ESIGI:
                try:
                    if hedef.voice and hedef.voice.channel:
                        await hedef.move_to(None, reason="Veritan: tekrar eden hakaret")
                        print(f"[CEZA] {hedef.display_name} ATILDI")
                        self.ihlaller.pop(hedef.id, None)
                        await asyncio.sleep(0.3)
                        await _seslendir_ve_cal(
                            self.vc, "Iste boyle! Uyarmistim ama dinlemedin, hadi disari! "
                                     "Adam gibi konusmayi ogrenince gelirsin.")
                except discord.Forbidden:
                    print("[CEZA] KICK yetkisi yok (Move Members lazim)")
                    await _seslendir_ve_cal(
                        self.vc, "Seni atardim ama yetkim yok, birileri bana o izni versin!")
                except Exception as e:
                    print("[CEZA] kick hatasi:", repr(e))
                return

            # === 1. İHLAL -> HAPİSHANE + TIMEOUT + VERİTAN ZİYARETİ ===
            await self._hapishaneye_at(hedef)

        except Exception as e:
            print("[CEZA] genel hata:", repr(e))
            traceback.print_exc()

    async def _hapishaneye_at(self, hedef):
        """
        Kisiyi hapishane kanalina tasir, Veritan oraya gider ve son uyarisini
        yapar, kisiye gercek Discord timeout uygular, sonra Veritan eski
        kanala geri doner.
        """
        eski_kanal = self.vc.channel if self.vc else None
        hapishane = bot.get_channel(HAPISHANE_KANAL_ID)
        if hapishane is None:
            try:
                hapishane = await bot.fetch_channel(HAPISHANE_KANAL_ID)
            except Exception as e:
                print(f"[HAPIS] hapishane kanali bulunamadi: {e!r}")
                hapishane = None

        # 1) kisiyi hapishaneye tasi
        tasindi = False
        if hapishane is not None:
            try:
                if hedef.voice and hedef.voice.channel:
                    await hedef.move_to(hapishane, reason="Veritan: ceza - hapishane")
                    tasindi = True
                    print(f"[HAPIS] {hedef.display_name} hapishaneye tasindi")
            except discord.Forbidden:
                print("[HAPIS] tasima yetkisi yok (Move Members lazim)")
                await _seslendir_ve_cal(
                    self.vc, "Seni hapse atardim ama yetkim yok, izin verin bana!")
                return
            except Exception as e:
                print("[HAPIS] tasima hatasi:", repr(e))

        # 2) CEZA: once gercek Discord timeout dene, olmazsa server-mute.
        ceza_uygulandi = _ceza_uygula_sonuc = None
        ceza_uygulandi = await _uye_cezalandir(hedef, TIMEOUT_SANIYE)
        if ceza_uygulandi == "timeout":
            print(f"[HAPIS] {hedef.display_name} {TIMEOUT_SANIYE}sn TIMEOUT uygulandi")
        elif ceza_uygulandi == "mute":
            print(f"[HAPIS] {hedef.display_name} {TIMEOUT_SANIYE}sn server-MUTE uygulandi")
            # mute'u sure sonra ac
            asyncio.create_task(self._mute_ac_sonra(hedef, TIMEOUT_SANIYE))
        else:
            print("[HAPIS] CEZA UYGULANAMADI - yetki yok (Moderate Members + Mute Members lazim)")
            await _seslendir_ve_cal(
                self.vc, "Seni susturmak istiyorum ama yetkim yok! Birileri bana "
                         "moderasyon izni versin de gorun gununuzu!")

        # 3) Veritan hapishaneye gidip konussun (tasindiysa)
        if tasindi and hapishane is not None and eski_kanal is not None:
            try:
                await self._gecici_kanala_git(hapishane)
                await _seslendir_ve_cal(
                    self.vc, f"{hedef.display_name}! Beni dinle. Bu son uyarim, "
                             f"bir daha saygisizlik yaparsan hapishaneden de beterini "
                             f"yaparim, direkt atarim seni! Bir dakika burada dusun bakalim.")
                await asyncio.sleep(1.0)
                # 4) Veritan eski kanala geri doner
                await self._gecici_kanala_git(eski_kanal)
                print("[HAPIS] Veritan eski kanala dondu")
            except Exception as e:
                print("[HAPIS] Veritan ziyaret hatasi:", repr(e))
                # ne olursa olsun eski kanala don
                try:
                    await self._gecici_kanala_git(eski_kanal)
                except Exception:
                    pass
        else:
            # tasinamadiysa en azindan uyar
            await _seslendir_ve_cal(
                self.vc, f"{hedef.display_name}, sana bir dakika ceza! Son uyarim bu, "
                         f"bir daha yaparsan direkt atarim!")

    async def _gecici_kanala_git(self, kanal):
        """
        Veritan'i baska bir ses kanalina tasir. move_to voice_recv dinlemesini
        korur (ayni VoiceRecvClient tasinir), ama karisiklik olmasin diye
        calan ses durdurulur.
        """
        try:
            try:
                if self.vc.is_playing():
                    self.vc.stop()
            except Exception:
                pass
            await self.vc.move_to(kanal)
            await asyncio.sleep(0.7)
            self.guild = kanal.guild
        except Exception as e:
            print("[HAPIS] kanal degistirme hatasi:", repr(e))

    async def _mute_ac_sonra(self, hedef, saniye):
        """(Eski yontem yedegi) sure sonra server-mute'u kaldirir."""
        try:
            await asyncio.sleep(saniye)
            uye = self.guild.get_member(hedef.id) if self.guild else None
            if uye and uye.voice and uye.voice.channel:
                await uye.edit(mute=False, reason="Veritan: sure doldu")
                print(f"[CEZA] {hedef.display_name} mute acildi")
        except Exception as e:
            print("[CEZA] mute acilamadi:", repr(e))

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

                # --- HAZIR GENEL CÜMLE: her ~1.5 dk rastgele hazir cumle ---
                if HAZIR_GENEL_ACIK and not self.mesgul and HAZIR_GENEL_CUMLELER:
                    if (simdi - self.son_hazir_genel).total_seconds() >= HAZIR_GENEL_ARALIK_SN:
                        await self._hazir_genel_soyle()
                        self.son_hazir_genel = datetime.now()
                        continue

                # --- HAZIR KİŞİYE ÖZEL CÜMLE: her ~2.5 dk bir kisiye [MAN_NAME] ---
                if HAZIR_KISI_ACIK and not self.mesgul and HAZIR_KISI_CUMLELER:
                    if (simdi - self.son_hazir_kisi).total_seconds() >= HAZIR_KISI_ARALIK_SN:
                        if await self._hazir_kisi_soyle(kanal):
                            self.son_hazir_kisi = datetime.now()
                            continue

                # --- KORKUTMA: arada bir ciddi sesle tekinsiz sey soyle ---
                if KORKUT_ACIK and not self.mesgul:
                    gecen = (simdi - self.son_korkut_an).total_seconds() / 60
                    if gecen >= self._korkut_hedef_dk:
                        if await self._korkut(kanal):
                            self.son_korkut_an = datetime.now()
                            self._korkut_hedef_dk = random.randint(KORKUT_MIN_DK, KORKUT_MAX_DK)
                            continue

                if SAKA_ACIK and not self.mesgul:
                    gecen = (simdi - self.son_saka_an).total_seconds() / 60
                    if gecen >= self._saka_hedef_dk:
                        if await self._saka_yap(kanal, simdi):
                            self.son_saka_an = datetime.now()
                            self._saka_hedef_dk = random.randint(SAKA_MIN_DK, SAKA_MAX_DK)
                            continue

                # --- ARADA SIRADA MUHABBET: kimse istemeden hal hatir sor ---
                if MUHABBET_ACIK and not self.mesgul:
                    gecen = (simdi - self.son_muhabbet_an).total_seconds() / 60
                    if gecen >= self._muhabbet_hedef_dk:
                        if await self._muhabbet_baslat(kanal, simdi):
                            self.son_muhabbet_an = datetime.now()
                            self._muhabbet_hedef_dk = random.randint(
                                MUHABBET_MIN_DK, MUHABBET_MAX_DK)
                            continue

                adaylar = []
                for m in kanal.members:
                    if bot.user and m.id == bot.user.id:
                        continue
                    if rahatsiz_etme_mi(m.id):   # rahatsiz edilmesin istenmis
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

    async def _sorguya_cek(self, kullanici, ne_dedi):
        """
        Biri Veritan'i kotuledi -> sorguya cek. 'Niye boyle dedin' diye sor.
        Kisi 3 dakika icinde cevap vermezse hapishaneye atilir (baska ceza yok).
        """
        ruh_hali_tetikle("kufur")
        self.sorgudaki[kullanici.id] = {"an": datetime.now(), "ne_dedi": ne_dedi}
        soru = random.choice([
            f"Dur bakalım {kullanici.display_name}! Ne dedin sen şimdi? "
            f"Arkamdan mı konuşuyorsun? Aç bakalım ağzını, niye böyle dedin?",
            f"{kullanici.display_name}, bir dakika! Beni kötülediğini duydum. "
            f"Hesabını ver bakalım, neden öyle dedin?",
            f"Vayy {kullanici.display_name}! Sen beni çekiştiriyor musun? "
            f"Hadi açıkla bakalım, niye yaptın bunu?",
        ])
        await _seslendir_ve_cal(self.vc, soru)
        # 3 dakika sonra cevap gelmezse hapishane
        asyncio.create_task(self._sorgu_zaman_asimi(kullanici))

    async def _sorgu_zaman_asimi(self, kullanici):
        """3 dakika cevap yoksa hapishaneye atar (sadece hapishane)."""
        await asyncio.sleep(180)  # 3 dakika
        kayit = self.sorgudaki.get(kullanici.id)
        if not kayit:
            return  # cevap vermis, sorgudan cikmis
        # hala sorguda -> cevap vermedi -> hapishane
        self.sorgudaki.pop(kullanici.id, None)
        print(f"[SORGU] {kullanici.display_name} 3dk cevap vermedi -> hapishane")
        while self.mesgul:
            await asyncio.sleep(0.5)
        self.mesgul = True
        try:
            await _seslendir_ve_cal(
                self.vc, f"{kullanici.display_name}! İlk başta neden cevap vermedin ha? "
                         f"Suçlusun demek ki. Yürü bakalım hapishaneye!")
            hedef = self.guild.get_member(kullanici.id) if self.guild else None
            if hedef:
                await self._sadece_hapishaneye(hedef)
        finally:
            self.mesgul = False

    async def _sorgu_cevabi_degerlendir(self, kullanici, cevap):
        """Kisi sorguya cevap verdi -> modele degerlendirt, affet veya azarla."""
        try:
            baglam = (
                f"{ruh_hali_metni()}\n"
                f"[Durum] '{kullanici.display_name}' seni kotuledigi icin onu sorguya "
                f"cektin. Simdi sana su cevabi verdi: '{cevap}'\n"
                f"[Gorev] Cevabina gore tepki ver. Ikna edici/ozur diliyorsa bir "
                f"parca yumusa ama gururunu koru. Hala saygisizsa fena azarla. "
                f"Kisa konus, 1-2 cumle. Sesli okunacak."
            )
            messages = [{"role": "user", "content": [{"type": "text", "text": baglam}]}]
            response, _f, _t = await claude_cevapla(
                messages, self.guild, kullanici, web_arama=False,
                system=SYSTEM_PROMPT2, arac_kullan=False)
            metin = extract_text(response) if response else "Neyse, bu seferlik affettim."
            metin, _ = komutlari_ayikla(metin)
            await _seslendir_ve_cal(self.vc, metin)
            muzik_devam(self.vc)
        except Exception as e:
            print("[SORGU] degerlendirme hatasi:", repr(e))

    async def _sadece_hapishaneye(self, hedef):
        """Sadece hapishane kanalina tasir (baska ceza yok)."""
        hapishane = bot.get_channel(HAPISHANE_KANAL_ID)
        if hapishane is None:
            try:
                hapishane = await bot.fetch_channel(HAPISHANE_KANAL_ID)
            except Exception:
                hapishane = None
        if hapishane is None:
            return
        try:
            if hedef.voice and hedef.voice.channel:
                await hedef.move_to(hapishane, reason="Veritan: sorguya cevap vermedi")
                print(f"[SORGU] {hedef.display_name} hapishaneye atildi")
        except discord.Forbidden:
            print("[SORGU] hapishane tasima yetkisi yok")
            await _seslendir_ve_cal(self.vc, "Hapse atardim ama yetkim yok!")
        except Exception as e:
            print("[SORGU] hapishane hatasi:", repr(e))

    async def _hazir_genel_soyle(self):
        """Listeden rastgele bir GENEL hazir cumleyi Fish Audio ile seslendirir."""
        self.mesgul = True
        try:
            cumle = random.choice(HAZIR_GENEL_CUMLELER)
            print(f"[HAZIR-GENEL] {cumle!r}")
            await _seslendir_ve_cal(self.vc, cumle)
            muzik_devam(self.vc)
        except Exception as e:
            print("[HAZIR-GENEL] hata:", repr(e))
        finally:
            self.mesgul = False

    async def _hazir_kisi_soyle(self, kanal):
        """
        Rastgele bir kisi secer, KİŞİYE ÖZEL hazir cumleden birini alir,
        [MAN_NAME] yerine o kisinin adini koyar ve seslendirir.
        rahatsiz-etme diyenleri atlar.
        """
        adaylar = [m for m in kanal.members
                   if not (bot.user and m.id == bot.user.id) and not rahatsiz_etme_mi(m.id)]
        if not adaylar:
            return False
        self.mesgul = True
        try:
            hedef = random.choice(adaylar)
            cumle = random.choice(HAZIR_KISI_CUMLELER)
            cumle = cumle.replace("[MAN_NAME]", hedef.display_name)
            print(f"[HAZIR-KISI] -> {hedef.display_name}: {cumle!r}")
            await _seslendir_ve_cal(self.vc, cumle)
            muzik_devam(self.vc)
            return True
        except Exception as e:
            print("[HAZIR-KISI] hata:", repr(e))
            return False
        finally:
            self.mesgul = False

    async def _korkut(self, kanal):
        """
        Ciddi/tekinsiz bir sesle korkutucu bir sey soyler, sonra NORMAL sesle
        'yok bir sey' der. Iki ayri ses parcasi calinir.
        """
        # kanalda bot disinda kimse yoksa anlamsiz
        canli = [m for m in kanal.members
                 if not (bot.user and m.id == bot.user.id) and not rahatsiz_etme_mi(m.id)]
        if not canli:
            return False

        self.mesgul = True
        try:
            # 1) korkutucu cumleyi model uretsin
            gorev = (
                "[Gorev] Ses kanalindakilere aniden, ciddi ve tekinsiz bir tonda "
                "kisa, urpertici/gizemli bir sey soyle. Ornek tarz: 'Arkanda birinin "
                "durdugunu biliyor muydun...' veya 'Bu odada yalniz olmadigimizi hic "
                "dusundun mu...' gibi. TEK cumle, gercekten tuyler urpertici olsun ama "
                "kufur/siddet icermesin. Sadece cumleyi yaz, etiket veya aciklama koyma."
            )
            messages = [{"role": "user", "content": [{"type": "text", "text": gorev}]}]
            response, _f, _t = await claude_cevapla(
                messages, self.guild, None, web_arama=False,
                system=SYSTEM_PROMPT2, arac_kullan=False,
            )
            korkunc = extract_text(response) if response else "Arkana bakma... ama biri var."
            korkunc, _ = komutlari_ayikla(korkunc)

            print(f"[KORKUT] {korkunc!r}")
            # 2) ciddi/tekinsiz tonla seslendir
            await _seslendir_ve_cal(self.vc, f"{KORKUT_TON} {korkunc}")
            await asyncio.sleep(0.6)
            # 3) normal sesle bozuntuya verme
            rahatlatici = random.choice([
                f"{NORMAL_TON} Yok yok, saka saka, korktun mu?",
                f"{NORMAL_TON} Sakin ol, bir sey yok, dalga geciyorum.",
                f"{NORMAL_TON} Hehe, suratinizi gormeliydim. Bir sey yok.",
            ])
            await _seslendir_ve_cal(self.vc, rahatlatici)
            muzik_devam(self.vc)
            return True
        except Exception as e:
            print("[KORKUT] hata:", repr(e))
            return False
        finally:
            self.mesgul = False

    async def _saka_yap(self, kanal, simdi):
        """
        Kimse istemeden rastgele birine ADIYLA seslenip saka/dalga yapar,
        komik veya sacma bir sey soyler. True donerse saka yapildi.
        """
        adaylar = []
        for m in kanal.members:
            if bot.user and m.id == bot.user.id:
                continue
            if rahatsiz_etme_mi(m.id):
                continue
            son = self.son_saka.get(m.id)
            if son and (simdi - son).total_seconds() / 60 < SAKA_KISI_TEKRAR_DK:
                continue
            adaylar.append(m)

        if not adaylar:
            return False

        hedef = random.choice(adaylar)
        self.son_saka[hedef.id] = simdi
        ruh_hali_tetikle("saka_yapti")

        # ne yapiyor bilgisi (varsa saka icin malzeme)
        ne_yapiyor = ""
        try:
            for act in (hedef.activities or []):
                if getattr(act, "name", None):
                    ne_yapiyor = act.name
                    break
        except Exception:
            pass

        malzeme = f" (su an '{ne_yapiyor}' ile mesgul)" if ne_yapiyor else ""
        gorev = (
            f"[Gorev] Ses kanalindaki '{hedef.display_name}'{malzeme} adli kisiye "
            f"kimse istemeden, ADIYLA seslenip ona ABSURT, delice, sacma sapan komik "
            f"bir sey soyle ya da tatli tatli dalga gec. Cok gulunc olsun, insanlari "
            f"kirip gecirsin. Kendi de gulsun: cumlenin icine [laughs] koy, hatta "
            f"'hahaha', 'ahahah' gibi delice kahkahalar at. Sanki cok komik bir sey "
            f"soylemis de kendini tutamiyormussun gibi. TEK-IKI cumle, kisa. "
            f"Kirici/asagilayici veya kufurlu OLMASIN, dostca ve absurt olsun. Etiket KOYMA."
        )
        print(f"[SAKA] -> {hedef.display_name} (ne={ne_yapiyor!r})")
        await self._durtme_konus(gorev, hedef)
        return True

    async def _muhabbet_baslat(self, kanal, simdi):
        """
        Kimse konusmasa bile arada bir birine ADIYLA seslenip hal hatir sorar,
        ne yaptigini/yardim gerekip gerekmedigini sorar. Yayin aciksa oyundan
        yola cikar. True donerse muhabbet edildi.
        """
        adaylar = []
        for m in kanal.members:
            if bot.user and m.id == bot.user.id:
                continue
            if rahatsiz_etme_mi(m.id):
                continue
            son_mub = self.son_muhabbet.get(m.id)
            if son_mub and (simdi - son_mub).total_seconds() / 60 < MUHABBET_KISI_TEKRAR_DK:
                continue
            adaylar.append(m)

        if not adaylar:
            return False

        hedef = random.choice(adaylar)
        self.son_muhabbet[hedef.id] = simdi

        # hedef ne yapiyor? (oyun/yayin bilgisi)
        ne_yapiyor = ""
        yayinda = False
        try:
            vs = hedef.voice
            yayinda = bool(vs and (vs.self_stream or vs.self_video))
            for act in (hedef.activities or []):
                ad = getattr(act, "name", None)
                if ad:
                    ne_yapiyor = ad
                    break
        except Exception:
            pass

        if yayinda and ne_yapiyor:
            gorev = (f"'{hedef.display_name}' su an yayin aciyor ve '{ne_yapiyor}' oynuyor. "
                     f"Ona adiyla seslenip oyunun nasil gittigini sor, muhabbet baslat. "
                     f"Yayin GORUNTUSUNU gormedigini unutma, ekranda ne oldugunu uydurma.")
        elif ne_yapiyor:
            gorev = (f"'{hedef.display_name}' su an '{ne_yapiyor}' ile mesgul. "
                     f"Ona adiyla seslenip ne yaptigini sor, lazim olursa yardim teklif et, "
                     f"kisa bir muhabbet baslat.")
        else:
            gorev = (f"'{hedef.display_name}' adli kisiye adiyla seslenip hal hatir sor, "
                     f"'ne yapiyorsun, yardim edeyim mi' tarzi kisa ve samimi bir muhabbet baslat.")

        print(f"[MUHABBET] -> {hedef.display_name} (yayinda={yayinda}, ne={ne_yapiyor!r})")
        gorev += " TEK cumle, kisa ve samimi. Etiket KOYMA."
        await self._durtme_konus(f"[Gorev] {gorev}", hedef)
        return True

    async def _durtme_konus(self, gorev, hedef):
        self.mesgul = True
        try:
            messages = [{"role": "user", "content": [{"type": "text", "text":
                f"[Ses kanali durumu]\n{kanal_durumu_metni(self.guild)}\n"
                f"{ruh_hali_metni()}\n\n{gorev}"}]}]
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


@bot.tree.command(name="veritan_mesajara", description="Sunucudaki yazılı mesajlarda arama yapar (kim, nerede, ne zaman).")
@app_commands.describe(sorgu="Aranacak kişi, kelime veya konu")
async def veritan_mesajara(interaction: discord.Interaction, sorgu: str = ""):
    await interaction.response.defer(ephemeral=True)
    if interaction.guild is None:
        await interaction.followup.send("Bu komut sadece sunucuda çalışır.", ephemeral=True)
        return
    sonuc = await discord_mesaj_ara(interaction.guild, sorgu)
    if len(sonuc) > 1900:
        sonuc = sonuc[:1900] + "..."
    await interaction.followup.send(f"```\n{sonuc}\n```", ephemeral=True)


@bot.tree.command(name="veritan_muzikbul", description="İnternetten şarkı bulup ses kanalında çalar.")
@app_commands.describe(sarki="Şarkı adı (örn: cry for me)")
async def veritan_muzikbul(interaction: discord.Interaction, sarki: str):
    await interaction.response.defer(ephemeral=True)
    vc = (interaction.guild.voice_client if interaction.guild else None) or _bagli_ses_client()
    if vc is None:
        await interaction.followup.send("⚠️ Veritan ses kanalında değil.", ephemeral=True)
        return
    if not YTDLP_ACIK or not _ytdlp_var_mi():
        await interaction.followup.send(
            "⚠️ İnternetten müzik kapalı (yt-dlp yüklü değil). `requirements.txt`'e `yt-dlp` ekle.",
            ephemeral=True)
        return
    await interaction.followup.send(f"🔎 '{sarki}' aranıyor...", ephemeral=True)
    baslik, url = await muzik_internet_bul(sarki)
    if not url:
        await interaction.followup.send(f"⚠️ '{sarki}' bulunamadı veya çalınamıyor.", ephemeral=True)
        return
    if muzik_url_cal(vc, url, baslik):
        await interaction.followup.send(f"🎵 Çalıyor: **{baslik}**", ephemeral=True)
    else:
        await interaction.followup.send("⚠️ Çalınamadı.", ephemeral=True)


@bot.tree.command(
    name="veritan_bak",
    description="Bir görsele bakıp yorumlar (yayın/ekran görüntüsü at, fikrini söylesin).",
)
@app_commands.describe(
    resim="Yorumlanacak görsel (ekran görüntüsü, yayın kaydı vb.)",
    soru="(İsteğe bağlı) Ne sormak istiyorsun? Örn: 'bu iyi mi?'",
)
async def veritan_bak(interaction: discord.Interaction, resim: discord.Attachment, soru: str = "Bu nasıl, ne diyorsun?"):
    await interaction.response.defer()

    ctype = resim.content_type or ""
    if not ctype.startswith("image/"):
        await interaction.followup.send("⚠️ Bu bir görsel değil. Ekran görüntüsü/resim at.", ephemeral=True)
        return

    kalan, limit, reset_at, izin = limit_kontrol(interaction.user.id)
    if not izin:
        await interaction.followup.send("🚫 Hak bakiyen bitti.", ephemeral=True)
        return

    try:
        img = await resim.read()
        ruh_hali_guncelle()
        icerik = [
            {"type": "image", "source": {"type": "base64", "media_type": ctype,
                                          "data": base64.standard_b64encode(img).decode("utf-8")}},
            {"type": "text", "text":
                f"{ruh_hali_metni()}\n"
                f"Bu bir ekran goruntusu/gorsel. {interaction.user.display_name} sana soruyor: "
                f"'{soru}'. Gorsele bak, samimi ve dogal bir dille yorumla, fikrini soyle, "
                f"gerekiyorsa oneride bulun. Kisa konus (2-3 cumle), sesli okunacak."},
        ]
        messages = [{"role": "user", "content": icerik}]
        response, _f, token = await claude_cevapla(
            messages, interaction.guild, interaction.user,
            web_arama=False, system=SYSTEM_PROMPT2, arac_kullan=False,
        )
        yorum = extract_text(response) if response else "Bir sey diyemedim."
        yorum, _ = komutlari_ayikla(yorum)
        limit_harca(interaction.user.id, token * TOKEN_MALIYETI)

        # ses kanalindaysa seslendir, degilse yazili+mp3
        vc = interaction.guild.voice_client if interaction.guild else None
        if vc and vc.is_connected():
            await interaction.followup.send(f"👀 {yorum}")
            try:
                await _seslendir_ve_cal(vc, yorum)
                muzik_devam(vc)
            except Exception:
                pass
        else:
            audio = await generate_fish_audio(yorum)
            await interaction.followup.send(
                content=f"👀 {yorum}",
                files=[discord.File(io.BytesIO(audio), filename="veritan.mp3")])
    except Exception as e:
        traceback.print_exc()
        await interaction.followup.send(f"⚠️ Bakarken hata: `{e}`", ephemeral=True)


@bot.tree.command(name="veritan_ruh", description="Veritan'ın şu anki ruh halini gösterir / değiştirir.")
@app_commands.describe(ayarla="(Yetkili) Ruh halini zorla ayarla: keyifli/muzip/sikkin/kizgin/yorgun/huzunlu/cosku")
async def veritan_ruh(interaction: discord.Interaction, ayarla: str = ""):
    await interaction.response.defer(ephemeral=True)
    if ayarla:
        if not yetkili_mi(interaction.user):
            await interaction.followup.send("⛔ Ruh halini sadece yetkili değiştirebilir.", ephemeral=True)
            return
        if ayarla.lower() in _RUH_HALLERI:
            _ruh["hal"] = ayarla.lower()
            _ruh["degisim_an"] = datetime.now()
            await interaction.followup.send(f"✅ Ruh hali **{ayarla.lower()}** yapıldı.", ephemeral=True)
        else:
            await interaction.followup.send(
                f"⚠️ Geçersiz. Seçenekler: {', '.join(_RUH_HALLERI.keys())}", ephemeral=True)
        return
    hal, aciklama = ruh_hali_al()
    await interaction.followup.send(f"🎭 Şu an: **{hal}** — {aciklama}", ephemeral=True)


@bot.tree.command(
    name="veritan_rahatsiz_etme",
    description="Veritan kendiliğinden sana laf atmasın (şaka/muhabbet/korkutma yapmasın).",
)
async def veritan_rahatsiz_etme(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    uid = interaction.user.id
    if uid in _rahatsiz_etme:
        _rahatsiz_etme.discard(uid)
        _rahatsiz_kaydet()
        await interaction.followup.send(
            "✅ Tamam, artık seninle yine muhabbet edebilirim, şaka yapabilirim. "
            "Rahatsız etme modu **KAPANDI**.",
            ephemeral=True)
    else:
        _rahatsiz_etme.add(uid)
        _rahatsiz_kaydet()
        await interaction.followup.send(
            "🤫 Tamamdır, seni artık kendiliğimden rahatsız etmem — sana şaka yapmam, "
            "muhabbet açmam, laf atmam. Ama sen 'veritan' deyip bir şey sorarsan yine "
            "yardımcı olurum. Rahatsız etme modu **AÇILDI**.\n"
            "(Tekrar aynı komutu yazarsan kapanır.)",
            ephemeral=True)


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
                        muzik_baslat(vc, "")
                    elif komut == "muzikbul" and arg:
                        baslik, url = await muzik_internet_bul(arg)
                        if url:
                            muzik_url_cal(vc, url, baslik)
                    elif komut == "dur":
                        muzik_durdur(vc, kalici=True)
                    elif komut == "ara" and arg:
                        sonuc = await web_arastir_ve_anlat(arg, None, guild)
                        await _seslendir_ve_cal(vc, sonuc)
                    elif komut == "mesajara":
                        sonuc = await discord_mesaj_ara(guild, arg)
                        await _seslendir_ve_cal(vc, sonuc[:400])
                    elif komut == "favori":
                        await _favori_resim_gonder(guild, ses_kanali=True)
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
