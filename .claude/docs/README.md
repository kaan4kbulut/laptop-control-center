# Belge dizini

```
.claude/
├── settings.json                        ← izinler (dar liste; sudo, rm -rf, force push yasak)
├── skills/python-gelistirme/SKILL.md    ← bu projede nasıl kod yazılır (kendiliğinden yüklenir)
├── commands/
│   ├── ozellik-ekle.md                  ← /ozellik-ekle <açıklama>
│   ├── inceleme.md                      ← /inceleme [dosyalar | "son değişiklikler"]
│   └── sablonu-doldur.md                ← /sablonu-doldur: şablon belgelerini bu projeye göre doldurur
└── docs/
    ├── README.md                        ← bu dosya
    ├── proje/                           ← bu projeye özgü (asıl kaynak)
    └── kaynaklar/                       ← bilgisayar, platform ve kütüphane notları
```

## proje/: bu projede iş yaparken okunur

| Dosya | Neyi belirler |
|---|---|
| `URUN.md` | **Ne** yapılıyor: amaç, ilkeler, özellikler, ekranlar ve akışlar, aşamalar, başarı ölçütleri |
| `MIMARI.md` | Katmanlar, klasör yapısı, bağımlılık verme, hata yönetimi, eşzamanlılık, test düzeni |
| `VERI.md` | Veri modeli, dosya ve veritabanı biçimleri, şema değişikliği kuralları, ayarlar |
| `TASARIM.md` | Arayüz düzeni, tema renkleri, bileşenler, metinler, klavye ve erişilebilirlik |
| `PERFORMANS.md` | Açılış ve yanıt hedefleri, ölçüm yöntemi, bellek ve güç tüketimi |
| `KARARLAR.md` | Tarihli kararlar: ne seçildi, neden, alternatifler |

## kaynaklar/: başvuru notları

| Dosya | İçerik |
|---|---|
| `SISTEM.md` | Bu bilgisayar: Omarchy/Hyprland, yönetici yetkisi kuralı, yerel modeller, Python ortamı, yollar. **Diğer belgelerle çelişirse bu kazanır** |

Yeni bir kütüphane ya da platform API'si doğrulanınca buraya kısa bir not dosyası eklenir (`<Kütüphane>.md`).

## Belgeleri sağlıklı tutmak
- Kapsam değişikliği → önce `URUN.md`, sonra kod.
- Mimari karar → `KARARLAR.md`'ye "Karar / Neden / Alternatifler" notu, aynı değişiklikte.
- Belge ile kod çelişirse kod yanlış kabul edilmez; hangisinin doğru olduğu kullanıcıya sorulur ve ikisi eşitlenir.
