# CLAUDE.md

Bu depoda çalışırken Claude Code için yönergeler. Her oturumun başında okunur.

## Proje özeti

**Laptop Control Center (`lcc`)**: Linux dizüstüleri için donanımı tanıyan kontrol merkezi. Performans modları
(işlemci + ekran kartı güç ve saat sınırları, fan eğrisi), fan, LED klavye, şarj sınırı, pil tasarrufu kademeleri,
canlı izleme, sistem optimizasyonu (`lcc tune`) ve Omarchy çubuk eklentisi. Görünüm Monster/Clevo Control
Center'dan esinlenmiştir. **Depo herkese açıktır** (GPL-3.0-or-later).

Kapsam ve özellikler: [.claude/docs/proje/URUN.md](.claude/docs/proje/URUN.md).

**Durum (2026-10-12):** Clevo/TUXEDO (tccd) ve genel (power-profiles-daemon) arka uçları çalışıyor; Monster Tulpar
T6 V3.7'de günlük kullanımda. Otomatik test yok (yalnızca gizlilik denetimi); yeni kod testle gelir.

## Çalışma anlaşması

- Kullanıcı Türkçe yazar → **Türkçe cevap ver**. Kod yorumları, commit mesajları ve belgeler Türkçe; kod
  tanımlayıcıları İngilizce. Arayüz metinleri **iki dilli** (`lcc/i18n.py`, tr + en); README iki dilli.
- Önemsiz olmayan işte önce plan yap; donanıma yazan bir değişikliği gerçek cihazda dene ve sonucu ölçerek bildir.
- Kullanıcıya komut verme, kendin çalıştır. Root gereken işlem `lcc-helper` üzerinden; yetki kuralları yerel
  `SISTEM.md`'de (git'e girmez).
- Belgeler kodla aynı değişiklikte güncellenir: özellik → `URUN.md` + README (iki dil), karar → `KARARLAR.md`.
- **Gizlilik:** depo açık. Kullanıcı adı, gerçek ad/e-posta, ev klasörü yolu, makine envanteri, gizli depo adları
  commit'e girmez. Commit öncesi `.githooks` denetimi çalışır; atlama. Yeni görsel `privacy-assets.json` onayı ister.
- Commit yazarı `kaan4kbulut <52260768+kaan4kbulut@users.noreply.github.com>`.

## Teknoloji

| | |
|---|---|
| Dil | Python **3.10+** (`requires-python`); geliştirme ortamı 3.14 |
| Arayüz | PySide6 + QML (`lcc/gui/`), Quickshell çubuk eklentisi (`data/omarchy/`) |
| Donanım | tccd DBus (PyGObject), sysfs, `nvidia-smi`, `iw`, `brightnessctl`, logind |
| Root işlemleri | `data/helper/lcc-helper` (pkexec + polkit kuralı, sabit komut listesi, `VERSION`) |
| Servis | `lcc-daemon` systemd kullanıcı servisi |
| Test | pytest (yeni testler `tests/` altında); `python3 tools/privacy_check.py` |

## Kurulum, çalıştırma, test

```bash
./install.sh --dev          # depodan çalıştırır (geliştirme); --dry-run önce ne yapacağını gösterir
lcc status | lcc gui | lcc tune
systemctl --user restart lcc-daemon     # daemon kodu değişince
python3 tools/privacy_check.py          # commit öncesi gizlilik taraması
```

## Mimari (özet; ayrıntı MIMARI.md)

```
cli.py · gui/ (QML + bridge.py) · data/omarchy (çubuk)      ← arayüzler
        │
controller.py (mod/fan seçimi, güç kaynağına göre hatırlama) · power.py (pil tasarrufu) · tune.py (optimizasyon)
        │
backends/ (tccd | generic) · gpu.py · sensors.py · hardware.py · helper.py (→ lcc-helper, root)
        │
daemon.py: fiş tak/çek, açılış modu, pil tasarrufu kademesi
```

- **Arka uç** `backends/base.Backend`'i uygular; `probe()` ile en uygun olanı seçilir. Yeni üretici = yeni arka uç.
- **Root** gereken her şey `helper.run(komut, …)` → `lcc-helper`; betik yalnızca bilinen komutları kabul eder.
  Helper değişince `VERSION` artırılır ve çağıran modülde `HELPER_MIN` güncellenir.

## Değişmez kurallar

### Donanım ve güvenlik
- `lcc-helper`'a serbest komut ya da yol geçmez; her yeni komut sabit listeye eklenir ve argümanı doğrulanır.
- Donanıma yazan kod önce mevcut değeri okur; geri dönüş (fiş takılınca, mod değişince) her zaman mümkün olmalı.
- NVIDIA kartını uyandırma: izleme dışında `lspci`/`nvidia-smi` çağırma (önbellek: `hardware.py`, `gpu.py`).

### Python
- Tür ipuçları; `pathlib`; ayar yazımı atomik (`config.save`); çıplak `except` yok.
- `subprocess` liste argümanla ve zaman aşımıyla.

### Arayüz
- Ölçümler ayrı iş parçacığında (`gui/bridge.py`); QML yalnızca gösterir.
- Görünüm projenin kendi teması (`gui/qml/Theme.qml`: koyu zemin, camgöbeği/mor vurgular, Exo 2 + Rajdhani);
  Omarchy temasına bağlı değil. Tasarım taslakları `docs/design/*.dc.html`.
- Her metin `i18n.t("anahtar")` ile; tr ve en birlikte eklenir.

### Test
- Yeni ya da değişen mantık (controller, power, tune denetimleri, config) için başarılı ve başarısız durum testi;
  arka uç sahte nesneyle, sysfs `tmp_path` altında taklit edilir. Testler donanıma ve root'a dokunmaz.

## Ürün kuralları (kısa)

- Modlar: `performance` (Performans) · `balanced` (Eğlence) · `quiet` (Sessiz) · `powersave` (Pil Tasarrufu).
- Seçim güç kaynağına göre hatırlanır (`ac` / `battery`); açılışta `boot_mode` uygulanır (prizde Eğlence, pilde Sessiz).
- Eğlence: turbo açık, işlemci tavanı en yüksek frekansın %85'i; Sessiz: turbo kapalı. Ekran kartı saat/güç sınırı
  moda göre (`gpu_limit`). Boştayken bütün modlar düşük güçte kalır.
- "Uyku" ayarı açıksa bilgisayar kapak kapansa da uyumaz (ekran kapanabilir).

## Başvuru belgeleri

| Dosya | İçerik |
|---|---|
| `.claude/docs/proje/URUN.md` | Özellikler, desteklenen donanım, aşamalar |
| `.claude/docs/proje/MIMARI.md` | Modüller, arka uç arayüzü, helper, daemon, arayüz köprüsü |
| `.claude/docs/proje/VERI.md` | config.json anahtarları, durum ve önbellek dosyaları, tccd profilleri |
| `.claude/docs/proje/TASARIM.md` | Pencere sayfaları, tema, çubuk eklentisi, iki dillilik |
| `.claude/docs/proje/PERFORMANS.md` | Mod ölçümleri, güç ve yoklama sıklığı |
| `.claude/docs/proje/KARARLAR.md` | Tarihli kararlar |
| `.claude/docs/kaynaklar/SISTEM.md` | (yerel, git'e girmez) bu bilgisayarın bilgileri |
| `README.md`, `PRIVACY.md` | Kullanıcı belgesi (iki dil), yayımlama gizliliği |
