---
description: Projeye yeni bir özelliği mimariye ve kurallara uygun biçimde ekler
argument-hint: <özellik açıklaması>
---

# Özellik ekle: $ARGUMENTS

## 0. Kod yazmadan önce
1. `CLAUDE.md` (kurallar) ve `.claude/docs/proje/URUN.md`'nin ilgili bölümünü (kapsam) oku.
   Özellik URUN.md'de yoksa önce oraya ekle ve kullanıcıya göster.
2. `python-gelistirme` becerisini yükle; gösterdiği belgelere bak:
   - `MIMARI.md`: katmanlar, bağımlılık, hatalar
   - `VERI.md`: model, dosya biçimi, şema değişikliği
   - `TASARIM.md`: arayüz, tema, metinler
3. Oluşturulacak/değişecek dosyaları ve yazılacak testleri listele. Kapsam belirsizse kullanıcıya sor.

## 1. Uygulama sırası (içten dışa)
1. **Model**: veri sınıfları; şema değişirse sürüm artır + geçiş adımı (VERI.md).
2. **Depo**: dosya/SQLite/ağ erişimi; hatayı `errors.py` türüne çevirir.
3. **Servis**: iş kuralı; bağımlılığı `__init__` ile alır.
4. **Arayüz**: CLI komutu ya da PySide6 bileşeni; yalnızca servisi çağırır, uzun iş işçi iş parçacığında.
5. **Metinler**: Türkçe, doğru yazım; hata iletisi ne olduğunu ve ne yapılacağını söyler.
6. **Testler**: servis için sahte depoyla, depo için `tmp_path` ile; her yeni davranışa başarılı ve başarısız durum.

## 2. Doğrula
```bash
.venv/bin/pytest -q
```
Arayüz değiştiyse uygulamayı açıp değişen yeri gerçekten dene.

## 3. Bitti demeden önce
- [ ] Testler eklendi ve geçiyor (gerçek sonucu bildir)
- [ ] Katman kuralları korunuyor (arayüzde iş mantığı yok, serviste Qt/G/Ç yok)
- [ ] Metinler Türkçe; gizli bilgi yok
- [ ] `URUN.md` aşama tablosu, gerekirse `VERI.md`/`KARARLAR.md` ve `CLAUDE.md` durum satırı güncel
