---
description: Kodu proje kurallarına göre inceler (mimari, Python, güvenlik, arayüz, test, belgeler)
argument-hint: [dosyalar, klasör ya da "son değişiklikler"]
---

# İnceleme: $ARGUMENTS

Verilen dosyaları (verilmediyse `git diff` ile son değişiklikleri) `CLAUDE.md` ve `.claude/docs/proje/*`'ye göre
incele. Her sorunu `dosya:satır`, neden önemli olduğu ve somut düzeltmesiyle bildir. Önce hatalar, sonra öneriler.
Değişiklik yapma; yalnızca raporla (kullanıcı isterse düzelt).

## Mimari
- [ ] Arayüzde iş mantığı yok; arayüz yalnızca servisi çağırıyor
- [ ] Serviste Qt, `print`, doğrudan dosya/ağ/alt süreç yok
- [ ] Bağımlılıklar `__init__` ile veriliyor; modül düzeyinde tekil nesne yok
- [ ] Düşük düzey hatalar depoda proje hata türüne çevriliyor

## Python
- [ ] Tür ipuçları; `pathlib`; çıplak `except` yok; hatalar yutulmuyor
- [ ] Dosya yazımı atomik; XDG yolları kullanılıyor, proje klasörüne çalışma verisi yazılmıyor
- [ ] `subprocess` liste argümanla, zaman aşımıyla; `shell=True` yok

## Güvenlik
- [ ] Gizli bilgi kodda/testte/belgede yok
- [ ] Dış girdi (kullanıcı, model, ağ) doğrulanıyor: yol sınırı, URL'de yerel ağ engeli, boyut sınırı
- [ ] Yıkıcı işlem (silme, üzerine yazma) geri alınabilir ya da onaylı

## Arayüz (varsa)
- [ ] Uzun iş arayüz iş parçacığında değil
- [ ] Renkler Omarchy temasından; sabit renk yok
- [ ] Metinler Türkçe ve doğru yazımlı; klavyeyle kullanılabilir

## Güç
- [ ] Boşta yoklama yok ya da seyrek; NVIDIA kartını uyandıran çağrı (`lspci`, `nvidia-smi`, GPU'da çizim) yok

## Test ve belgeler
- [ ] Yeni davranışların başarılı ve başarısız durum testleri var; testler ağa çıkmıyor, ev klasörüne yazmıyor
- [ ] Belgeler kodla uyumlu (URUN, VERI, KARARLAR, CLAUDE.md durum satırı)
