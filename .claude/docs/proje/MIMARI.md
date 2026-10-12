# Mimari

## 1. Modüller

| Modül | Sorumluluk |
|---|---|
| `cli.py` | Komutlar: status, mode, fan, kbd, charge, fnlock, power, monitor, tune, setup, gui, bar, daemon |
| `controller.py` | Mod/fan seçimi; güç kaynağına göre hatırlama; `reapply()`; `gpu.apply(mode)` çağrısı |
| `backends/base.py` | `Backend` arayüzü (`probe`, `capabilities`, `current`, `apply`, `setup`, klavye, şarj, Fn kilidi) |
| `backends/tccd.py` | Clevo/TUXEDO: tccd DBus'a `lcc-<mod>-<fan>` profilleri yazar ve geçici profil seçer; CPU tablosu |
| `backends/generic.py` | power-profiles-daemon ve UPower klavye ışığı |
| `gpu.py` | NVIDIA saat tavanı ve güç sınırı (helper ile); durum `gpu.json` (mod + boot_id) |
| `power.py` | Pil tasarrufu kademeleri; açılan her şeyin eski hali kaydedilir ve geri yüklenir |
| `tune.py` | Optimizasyon denetimleri (`check_*` → dict) ve düzeltmeleri |
| `daemon.py` | UPower ve tccd sinyalleri, kapak durumu, Hyprland olayları; açılış modu (boot_id başına bir kez) |
| `profiles.py` | Omarchy/power-profiles-daemon seçimiyle eşitleme |
| `sensors.py`, `hardware.py` | Ölçümler ve donanım bilgisi (GPU adı önbellekte; `lspci` çağrılmaz) |
| `helper.py` | `run(komut, …)` → `pkexec lcc-helper`; sürüm denetimi |
| `config.py` | `config.json` (DEFAULTS ile birleştirme, atomik yazma), `state_dir()` |
| `i18n.py` | `t(anahtar)`; dil: ayar → klavye düzeni → sistem dili |
| `gui/app.py`, `gui/bridge.py`, `gui/qml/` | PySide6 + QML pencere; köprü ölçümleri ayrı iş parçacığında yapar |
| `data/helper/lcc-helper` | Root betiği: sabit komutlar (ASPM, Wi-Fi, servis, rfkill, kamera, tccd, sleep, gpu…) |
| `data/omarchy/` | Quickshell çubuk eklentisi; veri `lcc bar` komutundan |
| `data/systemd`, `data/polkit` | daemon servisi; helper için polkit politikası ve `wheel` kuralı |

## 2. Akış: mod değiştirme

`lcc mode X` / pencere / Super+F5 → `Controller.set_mode` → `config` (güç kaynağına göre) → `backend.apply` →
`gpu.apply` → bildirim/ekran göstergesi. Fiş takılıp çekilince daemon `reapply()` çağırır (tccd güç kaynağı değişince
profili sıfırlar).

## 3. Root sınırı

Yalnızca `lcc-helper`; argümanlar betikte doğrulanır. Helper değişince `VERSION` artar; `gpu.py`/`tune.py` içindeki
`HELPER_MIN` eski helper'ı tanır ve kurulumu yenilemeyi önerir.

## 4. Test

Bugün otomatik test yok. Eklenecek düzen: `tests/` + pytest; arka uç için sahte `Backend`, sysfs için `tmp_path`,
helper için sahte `run`. Hiçbir test donanıma ya da root'a dokunmaz.
