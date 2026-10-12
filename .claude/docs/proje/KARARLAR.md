# Kararlar

Her karar tarihli bir başlık altında: **Karar**, **Neden**, **Alternatifler**. Yeni karar en üste.

## 2026-10-12: Proje şablonu düzenine geçildi
- **Karar:** CLAUDE.md + `.claude/docs`; makineye özgü `SISTEM.md` git'e girmez (`.gitignore`).
- **Neden:** Kullanıcının bütün projeleri aynı düzende; depo açık olduğu için kişisel bilgi dışarıda kalmalı.
- **Alternatifler:** SISTEM.md'yi temizleyip yayımlamak (her güncellemede yeniden denetim gerekirdi).

## 2026-10-12: Eğlence "orta kısım"; ekran kartına da sınır
- **Karar:** Eğlence'de `balance_performance` + turbo açık + %85 frekans tavanı; ekran kartında saat tavanı moda göre.
- **Neden:** Kullanıcı "olabildiğince düşük ama gerektiğinde yükselebilsin" istedi; `balance_power` yükte 2,2 GHz'de kalıyordu.
- **Alternatifler:** Güç sınırı (`-pl`) cihazda desteklenmiyor.

## 2026-10-12: Açılış modu ve Uyku ayarı
- **Karar:** Her açılışta bir kez prizde Eğlence, pilde Sessiz; "Uyku" logind ayarıyla kapakta uyumayı kapatır.
- **Neden:** Kullanıcı işlerin hiç kesilmemesini, ekranın ise kapanabilmesini istedi.
- **Alternatifler:** Koşullu uyku engeli (yalnızca iş sürerken); Cafer'in uyku bekçisi olarak planlandı.

## Önceki: Root işlemleri tek betikte
- **Karar:** `lcc-helper` sabit komut listesi + polkit kuralı (`wheel` parolasız).
- **Neden:** Her ayarda şifre sormadan, ama keyfi root komutuna da izin vermeden.
