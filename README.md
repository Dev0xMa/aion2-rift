# Aion 2 Bildirim Botu

Discord'a zamanlı Aion 2 hatırlatmaları gönderir (rift, haftalık sıfırlama vb.).

## Yeni hatırlatma eklemek
Sadece `etkinlikler.yaml` dosyasına yeni bir blok ekle ve kaydet. Açıklamalar dosyanın başında.

## Nasıl çalışıyor
- cron-job.org her 5 dakikada bir bu workflow'u tetikler.
- Bot o anın 5 dk sonrasındaki pencereye düşen bildirimleri tam saatinde gönderir.

Secrets: `DISCORD_WEBHOOK`, `DISCORD_ROLE_ID`

Test: Actions → Aion 2 Bildirim Botu → Run workflow (test işaretli).
