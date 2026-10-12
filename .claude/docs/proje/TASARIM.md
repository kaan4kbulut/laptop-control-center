# Tasarım

## 1. Pencere (PySide6 + QML)

- Sayfalar: Sistem İzleme (`MonitorPage`), LED Klavye (`LedPage`), Pil Tasarrufu (`PowerPage`), Yapılandırma
  (`SettingsPage`), Optimizasyon (`TunePage`), Fan Eğrisi (`FanCurvePage`). Ctrl+1…4 sayfa, Esc kapatır.
- Bileşenler: `ArcRing`, `Readout`, `Pill`, `RadioOption`, `LineSlider`, `Section`, `Glow`, `Waves`.
- Sahne 1280×760; ölçeklenir.

## 2. Tema

- Kendi teması (`gui/qml/Theme.qml`): zemin `#050608`, camgöbeği `#22b8ff`, mor `#8b3dff`, kırmızı `#ff2d55`;
  yazı tipleri Exo 2 (metin) ve Rajdhani (rakamlar), `gui/fonts/` (SIL OFL). Omarchy temasını izlemez (bilinçli
  karar; Monster/Clevo görünümü).
- Tasarım taslakları: `docs/design/*.dc.html` (Main, Ayarlar, Led, BarPanel, Osd); ekran görüntüleri `docs/screenshots/`.

## 3. Çubuk eklentisi ve ekran göstergesi

- Omarchy çubuğunda mod simgesi; sol tık panel, sağ tık mod adını gizle/göster, tekerlek mod değiştirir.
  Panel açıkken saniyede bir güncellenir; kapalıyken GPU sorgulanmaz.
- Super+F5 mod değiştirir ve ekran göstergesi çıkar.

## 4. Metinler

- Her metin `i18n.t()` anahtarıyla, tr + en birlikte. Türkçe yazım doğru (ç, ğ, ı, İ, ö, ş, ü).
