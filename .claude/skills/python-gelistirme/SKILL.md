---
name: python-gelistirme
description: >-
  Laptop Control Center'da kıdemli Python geliştirici becerisi: arka uç (Backend) yazma, lcc-helper'a güvenli root
  komutu ekleme, controller/daemon akışı, PySide6+QML köprüsü, iki dilli metinler (i18n.t), NVIDIA kartını
  uyandırmama, açık depo gizlilik kuralları, sahte arka uçla pytest. lcc kodu, helper, QML ya da test yazarken,
  değiştirirken veya incelerken kullan.
---

# Kıdemli Python geliştirici: Laptop-control-center

Doğru, sade, test edilebilir ve okunur kod yaz; bu sırayla.

## Kod yazmadan önce: ilgili belgeyi oku

| İş | Oku |
|---|---|
| Her özellik | `CLAUDE.md`, `.claude/docs/proje/URUN.md` (kapsam) |
| Katman, klasör, hata, test düzeni | `.claude/docs/proje/MIMARI.md` |
| Veri modeli, dosya biçimi, şema değişikliği | `.claude/docs/proje/VERI.md` |
| Arayüz, tema, metin, klavye | `.claude/docs/proje/TASARIM.md` |
| Hız, güç | `.claude/docs/proje/PERFORMANS.md` |
| Bilgisayar, yetki, yerel modeller | `.claude/docs/kaynaklar/SISTEM.md` (çelişkide kazanır) |

Bir kütüphane API'sinin varlığından emin değilsen tahmin etme: kurulu sürümde dene (`.venv/bin/python -c ...`)
ya da belgesine bak; doğruladığını `kaynaklar/<Kütüphane>.md`'ye not et.

## Temel ilkeler

1. **Önce doğruluk, sonra ölçüm**: donanıma yazan değişiklik gerçek cihazda denenir, sonuç ölçülerek bildirilir.
2. **Geri alınabilirlik**: önce mevcut değeri oku ve sakla; geri yükleme yolu her zaman olsun.
3. **Az yetki**: root yalnızca `lcc-helper`'ın sabit komutlarıyla.
4. **Desteklenmeyeni gizle**: `capabilities()` false ise arayüz o özelliği göstermez; istisna kullanıcıya hata olarak gitmez.

## Kalıplar (lcc)

### Yeni root komutu
1. `data/helper/lcc-helper` içinde `case` dalı ekle; argümanı sayı/izinli değer listesiyle doğrula; `VERSION` artır.
2. Python'da `helper.run("komut", arg)`; çağıran modülde `HELPER_MIN = <yeni sürüm>`; eski helper ise kullanıcıya
   kurulumu yenilemesini söyle (`lcc tune` bunu gösterir).
3. `install.sh --dev` ile helper'ı yeniden kur (pkexec; yetki özeti kuralı yerel SISTEM.md'de).

### Yeni arka uç
`backends/base.Backend`'i uygula; `probe()` uygunluk puanı döner (0 = uygun değil); `capabilities()` doğru
bildirilir; `backends/__init__.py` listesine ekle. Desteklenmeyen yöntem `Unsupported` fırlatır.

### Metin
```python
from .i18n import t
label = t("tune.sleep.ok")          # i18n.py STRINGS içinde "tr" ve "en" ikisi birden tanımlanır
```

### Test (eklenecek düzen)
```python
class FakeBackend(Backend):
    def __init__(self): self.applied = []
    def apply(self, mode, fan, force=False): self.applied.append((mode, fan))
    ...

def test_set_mode_remembers_per_power_source(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    ...
```

## Bitti sayılmadan önce
- [ ] Yeni/değişen her davranışın başarılı ve başarısız durum testi var; `.venv/bin/pytest -q` geçiyor (gerçek çıktıyı bildir)
- [ ] Root yalnızca lcc-helper ile; helper değiştiyse VERSION ve HELPER_MIN güncel
- [ ] NVIDIA kartını uyandıran yeni çağrı yok; QML yalnızca gösteriyor
- [ ] Yeni metinler i18n'de tr + en; README iki dilde güncel
- [ ] Kişisel bilgi yok (açık depo); `python3 tools/privacy_check.py` geçiyor
- [ ] Gerekli belge güncellendi (`URUN.md`, `VERI.md`, `KARARLAR.md` …) ve `CLAUDE.md` durum satırı doğru
