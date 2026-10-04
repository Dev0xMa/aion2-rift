"""
Aion 2 Rift uyarıcı.

Her rift için 4 bildirim:
  R-10 dk  : 10 dk sonra açılıyor
  R-5  dk  : 5 dk sonra açılıyor
  R        : Açıldı, girişin kapanmasına 10 dk
  R+5  dk  : Girişin kapanmasına son 5 dk

Rift'ler UTC 00,03,06,...,21'de açılır (TR 03,06,...,00).
GitHub zamanlayıcısı gecikebildiği için iş rift'ten ~25 dk önce başlar
ve bildirimleri tam saatinde atmak için kendi içinde bekler.
"""

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

WEBHOOK_URL = os.environ["WEBHOOK_URL"]
ROLE_ID = os.environ.get("ROLE_ID", "").strip()
TEST = os.environ.get("TEST", "false").lower() == "true"

TR = timezone(timedelta(hours=3))
PORTAL_DK = 10
GEC_KALMA_TOLERANSI = timedelta(seconds=90)

# (rift'e göre fark, renk, başlık, açıklama)
ADIMLAR = [
    (timedelta(minutes=-10), 0xF1C40F, "⏳ RIFT 10 DAKİKA SONRA AÇILIYOR",
     "Hazırlanın, portal **{saat}**'te açılacak."),
    (timedelta(minutes=-5), 0xE67E22, "⚠️ RIFT 5 DAKİKA SONRA AÇILIYOR",
     "Portal **{saat}**'te açılıyor. Karakterinizi hazırlayın!"),
    (timedelta(minutes=0), 0x2ECC71, "🌀 RIFT AÇILDI! GİRİŞE SON 10 DAKİKA",
     "Portal açık, giriş **{kapanis}**'te kapanıyor. Hemen girin!"),
    (timedelta(minutes=5), 0xE74C3C, "🚨 RIFT GİRİŞİ 5 DAKİKA SONRA KAPANIYOR",
     "Son şans! Giriş **{kapanis}**'te kapanıyor."),
]


def hedef_rift(simdi):
    """Girişi hâlâ açık olan ya da sıradaki ilk rift (UTC)."""
    t = simdi.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    while True:
        if t.hour % 3 == 0 and simdi < t + timedelta(minutes=PORTAL_DK):
            return t
        t += timedelta(hours=1)


def gonder(baslik, aciklama, renk):
    etiket = f"<@&{ROLE_ID}>\n" if ROLE_ID else ""
    veri = {
        "username": "Rift Bekçisi",
        "content": f"{etiket}# {baslik}",
        "embeds": [{"description": aciklama, "color": renk}],
        "allowed_mentions": {"roles": [ROLE_ID]} if ROLE_ID else {"parse": []},
    }
    istek = urllib.request.Request(
        WEBHOOK_URL,
        data=json.dumps(veri).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Aion2RiftBot"},
    )
    for deneme in range(3):
        try:
            urllib.request.urlopen(istek, timeout=15)
            print(f"[{datetime.now(TR):%H:%M:%S}] Gönderildi: {baslik}")
            return
        except Exception as e:
            print(f"Gönderilemedi ({deneme + 1}/3): {e}")
            time.sleep(5)


def main():
    simdi = datetime.now(timezone.utc)
    rift = hedef_rift(simdi)
    saat = rift.astimezone(TR).strftime("%H:%M")
    kapanis = (rift + timedelta(minutes=PORTAL_DK)).astimezone(TR).strftime("%H:%M")
    print(f"Hedef rift: {saat} TR")

    for fark, renk, baslik, aciklama in ADIMLAR:
        metin = aciklama.format(saat=saat, kapanis=kapanis)
        if TEST:
            gonder(f"[TEST] {baslik}", metin, renk)
            time.sleep(2)
            continue

        zaman = rift + fark
        kalan = (zaman - datetime.now(timezone.utc)).total_seconds()
        if kalan < -GEC_KALMA_TOLERANSI.total_seconds():
            print(f"Atlandı (geç kalındı): {baslik}")
            continue
        if kalan > 0:
            time.sleep(kalan)
        gonder(baslik, metin, renk)


if __name__ == "__main__":
    sys.exit(main())
