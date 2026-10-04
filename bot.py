"""
Aion 2 bildirim botu.

cron-job.org bu workflow'u her 5 dakikada bir tetikler (slot = tetiklenme
anı, 5 dakikaya yuvarlanmış). Her çalışma, zamanı [slot+5dk, slot+10dk)
aralığına düşen bildirimleri gönderir. 5 dakikalık önden başlama sayesinde
GitHub'ın kuyruk gecikmesi bildirimleri geciktirmez ve her bildirim
sadece tek bir çalışmaya düşer (çift mesaj olmaz).

Etkinlikler etkinlikler.yaml dosyasında tanımlıdır.
"""

import json
import os
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import yaml

TR = ZoneInfo("Europe/Istanbul")
SLOT = timedelta(minutes=5)
ONDEN = timedelta(minutes=5)
GUNLER = ["pzt", "sal", "car", "per", "cum", "cmt", "paz"]

# Secret adlari workflow'da env olarak verilir (rol: DISCORD_ROLE_ID gibi).
SECRETS = {k: v for k, v in os.environ.items() if k.startswith("DISCORD_")}
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") or SECRETS.get("DISCORD_WEBHOOK", "")
TEST = os.environ.get("TEST", "false").lower() == "true"


def tetiklenme_zamani():
    """Bu çalışmanın oluşturulma anı (GitHub API). Alınamazsa şu an."""
    repo, run_id, token = (os.environ.get(k) for k in
                           ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_TOKEN"))
    if repo and run_id and token:
        try:
            istek = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/actions/runs/{run_id}",
                headers={"Authorization": f"Bearer {token}",
                         "Accept": "application/vnd.github+json"})
            veri = json.load(urllib.request.urlopen(istek, timeout=10))
            return datetime.fromisoformat(veri["created_at"].replace("Z", "+00:00"))
        except Exception as e:
            print(f"Run zamanı alınamadı, şu an kullanılıyor: {e}")
    return datetime.now(timezone.utc)


def slota_yuvarla(t):
    t = t.replace(second=0, microsecond=0)
    return t - timedelta(minutes=t.minute % 5)


def rol_id(deger):
    if not deger:
        return ""
    deger = str(deger)
    return SECRETS.get(deger, deger).strip()


def renk(hex_):
    return int(str(hex_).lstrip("#"), 16)


def gonder(baslik, aciklama, renk_, rol):
    veri = {
        "username": "Rift Bekçisi",
        "content": (f"<@&{rol}>\n" if rol else "") + f"# {baslik}",
        "embeds": [{"description": aciklama, "color": renk_}],
        "allowed_mentions": {"roles": [rol]} if rol else {"parse": []},
    }
    istek = urllib.request.Request(
        WEBHOOK_URL, data=json.dumps(veri).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Aion2Bot"})
    for deneme in range(3):
        try:
            urllib.request.urlopen(istek, timeout=15)
            print(f"[{datetime.now(TR):%H:%M:%S}] Gönderildi: {baslik}")
            return
        except Exception as e:
            print(f"Gönderilemedi ({deneme + 1}/3): {e}")
            time.sleep(5)


def bildirimleri_hesapla(etkinlikler, bas, son):
    """[bas, son) aralığına düşen bildirimler: (zaman, baslik, aciklama, renk, rol)."""
    sonuc = []
    gun0 = bas.astimezone(TR).date()
    for e in etkinlikler:
        if not e.get("aktif", True):
            continue
        gunler = e.get("gunler")
        sure = timedelta(minutes=e.get("sure_dk", 0))
        for gun_fark in (-1, 0, 1):
            gun = gun0 + timedelta(days=gun_fark)
            if gunler and GUNLER[gun.weekday()] not in gunler:
                continue
            for s in e["saatler"]:
                saat, dk = map(int, s.split(":"))
                olay = datetime(gun.year, gun.month, gun.day, saat, dk, tzinfo=TR)
                for b in e["bildirimler"]:
                    zaman = olay + timedelta(minutes=b["fark"])
                    if bas <= zaman < son:
                        metin = b["aciklama"].format(
                            saat=olay.strftime("%H:%M"),
                            bitis=(olay + sure).strftime("%H:%M"))
                        sonuc.append((zaman, b["baslik"], metin,
                                      renk(b["renk"]), rol_id(e.get("rol"))))
    return sorted(sonuc, key=lambda x: x[0])


def main():
    with open("etkinlikler.yaml", encoding="utf-8") as f:
        etkinlikler = yaml.safe_load(f)["etkinlikler"]

    if not WEBHOOK_URL:
        raise SystemExit("DISCORD_WEBHOOK secret'ı yok.")

    if TEST:
        for e in etkinlikler:
            if not e.get("aktif", True):
                continue
            b = e["bildirimler"][0]
            metin = b["aciklama"].format(saat="00:00", bitis="00:00")
            gonder(f"[TEST] {b['baslik']}", metin, renk(b["renk"]), rol_id(e.get("rol")))
        return

    slot = slota_yuvarla(tetiklenme_zamani())
    bas, son = slot + ONDEN, slot + ONDEN + SLOT
    print(f"Slot {slot.astimezone(TR):%H:%M} TR, pencere "
          f"{bas.astimezone(TR):%H:%M}-{son.astimezone(TR):%H:%M}")

    plan = bildirimleri_hesapla(etkinlikler, bas, son)
    if not plan:
        print("Bu pencerede bildirim yok.")
        return

    for zaman, baslik, metin, renk_, rol in plan:
        kalan = (zaman - datetime.now(timezone.utc)).total_seconds()
        if kalan > 0:
            time.sleep(kalan)
        gonder(baslik, metin, renk_, rol)


if __name__ == "__main__":
    main()
