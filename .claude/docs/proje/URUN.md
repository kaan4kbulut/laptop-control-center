# Laptop Control Center: Ürün tanımı

> **Ne** yapıldığının asıl kaynağı. Özellik değişince bu dosya ve README (iki dil) birlikte güncellenir.

## 1. Amaç

Linux dizüstülerinde üreticinin Windows'taki kontrol merkezinin yaptığını tek yerden yapmak: performans modları,
fan, klavye ışığı, şarj ve pil tasarrufu, canlı izleme. Omarchy ile bütünleşik ama genel Linux'ta da çalışır.

**İlkeler**
1. **Donanımı tanı:** uygun arka ucu kendisi seçer; desteklenmeyen özellik gizlenir, hata vermez.
2. **Geri alınabilir:** her ayar geri döner (fiş takılınca, mod değişince, kaldırınca).
3. **Az yetki:** root yalnızca sabit komut listeli `lcc-helper` ile.
4. **Boşta sessiz ve serin:** bütün modlar boşta düşük güçte; gerektiğinde yükselir.

## 2. Kavramlar

| Kavram | Açıklama |
|---|---|
| Mod | performance (Performans) · balanced (Eğlence) · quiet (Sessiz) · powersave (Pil Tasarrufu) |
| Fan | auto · silent · max · custom (sürüklenebilir eğri) |
| Güç kaynağı | `ac` / `battery`; her biri için son seçim ayrı hatırlanır |
| Pil tasarrufu kademesi | saver (otomatik) · ultra (elle) · headless (pilde kapak kapalı, harici ekran yok) |
| Arka uç | tccd (Clevo/TUXEDO) · generic (power-profiles-daemon) |

## 3. Özellikler

- **Modlar:** işlemci güç sınırı ve enerji tercihi, turbo, işlemci frekans tavanı (`cpu_limit`), ekran kartı saat
  tavanı ve güç sınırı (`gpu_limit`), Otomatik fan eğrisi birlikte değişir.
- **Açılış modu:** her açılışta bir kez güç kaynağına göre (`boot_mode`; varsayılan prizde Eğlence, pilde Sessiz).
- **Fan:** dört seçenek; Özel eğri pencereden düzenlenir.
- **Canlı izleme:** işlemci, ekran kartı (yalnızca izleme açıkken sorgulanır), fanlar, bellek, disk, pil.
- **LED klavye**, **şarj sınırı**, **Fn kilidi**, kamera, touchpad, mikrofon, uçak modu, ses, parlaklık, gece ışığı.
- **Pil tasarrufu kademeleri:** her kademenin açacağı özellikler seçilebilir (60 Hz, parlaklık sınırı, Wi-Fi güç
  tasarrufu, ASPM, servisleri durdurma, Bluetooth, klavye ışığı, E çekirdekleri, ekransızda uygulama dondurma).
- **Optimizasyon (`lcc tune`):** 11 denetim (turbo, prizdeki mod, uyku, TRIM, TCP BBR, DNS, Wi-Fi, fan, servisler,
  disk, bellek); `lcc tune fix` tek tıkla düzeltir; DNS testi ve internet hız testi.
- **Uyku:** açıkken kapak kapansa da bilgisayar uyumaz, işler sürer (ekran kapanabilir).
- **Omarchy:** çubukta mod simgesi + canlı panel, Super+F5 ile mod değiştirme ve ekran göstergesi; power-profiles
  seçimiyle eşitleme.

## 4. Aşamalar

| Aşama | İçerik | Durum |
|---|---|---|
| 1 | tccd + generic arka uç, modlar, fan, klavye, izleme, pencere | bitti |
| 2 | Pil tasarrufu kademeleri, optimizasyon, Omarchy çubuğu | bitti |
| 3 | Açılış modu, Uyku ayarı, ekran kartı sınırları, boşta NVIDIA kartın tam kapanması | bitti (2026-10-12) |
| 4 | Otomatik testler (controller, power, tune, config) | bekliyor |
| 5 | Yeni arka uçlar (ASUS, Lenovo) | fikir |

## 5. İşlevsel olmayan gereksinimler

- Pencere açılışı ≤ 1 sn; arayüz ölçüm sırasında takılmaz.
- Daemon boşta ~%0 CPU; NVIDIA kartını uyandırmaz.
- Kurulum betiği her root adımından önce sorar, `--dry-run` hiçbir şeyi değiştirmez, tekrar çalıştırmak güvenli.

## 6. Kapsam dışı

- Üreticiye özel Windows yazılımı taklidi (yalnızca görünüm esinlenmesi), BIOS ayarları, aşırı hız aşırtma.
