---
description: Şablondan gelen belgeleri bu projeye göre doldurur (ürün tanımı, mimari, veri, tasarım, CLAUDE.md)
argument-hint: [proje hakkında ek bilgi]
---

# Şablonu doldur: $ARGUMENTS

Bu proje `Proje-sablonu`ndan oluşturuldu ya da ona dönüştürülüyor. Görev: `CLAUDE.md` ve `.claude/docs/proje/*`
içindeki `{{...}}` yer tutucularını ve `<!-- ... -->` açıklamalarını **bu projenin gerçek bilgileriyle** değiştirmek.

1. Kaynakları topla: mevcut kod ve README (varsa), `git log`, kullanıcının verdiği bilgi (`$ARGUMENTS`).
   Bilmediğin şeyi uydurma; boş kalan ama gerekli bilgiler için kullanıcıya **tek seferde** kısa sorular sor.
2. Sırayla doldur: `URUN.md` → `MIMARI.md` → `VERI.md` → `TASARIM.md` → `PERFORMANS.md` → `CLAUDE.md`
   (özet, durum, teknoloji tablosu, ürün kuralları). Projeye uymayan bölümü sil (ör. arayüzü yoksa TASARIM.md'yi
   "arayüz yok" diye kısalt), uymayan kuralı CLAUDE.md'den çıkar.
3. Kodda belgeyle çelişen bir şey görürsen düzeltme; `KARARLAR.md`'ye "açık soru" olarak yaz ve kullanıcıya bildir.
4. Python dışı bir proje ise (QML, kabuk betiği) `python-gelistirme` becerisini o dile uyarla ya da yeniden adlandır.
5. Sonunda: hangi belgeyi neyle doldurduğunu ve kullanıcıya sorduğun açık noktaları kısaca bildir.
