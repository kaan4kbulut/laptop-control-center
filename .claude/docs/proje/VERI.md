# Veri

## 1. Nerede

| Ne | Yol |
|---|---|
| Ayarlar | `~/.config/laptop-control-center/config.json` (`config.DEFAULTS` ile birleştirilir) |
| Durum | `~/.local/state/laptop-control-center/`: `boot-id` (açılış modu uygulandı mı), `gpu.json` (uygulanan GPU sınırı), `power.json` (kademe ve geri yüklenecek değerler), `battery-learned.json` |
| Önbellek | `~/.cache/laptop-control-center/`: `gpus.json` (GPU adları), QML önbellekleri |
| tccd profilleri | tccd ayarlarında `lcc-<mod>-<fan>` adlı profiller (`lcc setup` yazar) |
| logind | Uyku açıkken `/etc/systemd/logind.conf.d/30-lcc-no-sleep.conf` (helper yazar) |

## 2. config.json anahtarları

| Anahtar | Anlam |
|---|---|
| `language` | auto · tr · en |
| `ac`, `battery` | `{mode, fan}`: güç kaynağına göre son seçim |
| `boot_mode` | `{ac, battery}`: açılışta uygulanacak mod; eski biçim (tek dize) de okunur |
| `cpu_limit` | `{mod: yüzde}`: turbo açık modlarda en yüksek frekansın yüzdesi |
| `gpu_limit` | `{mod: [saat %, güç % \| "max"]}` |
| `custom_fan_curve` | `[[°C, %], …]` |
| `keyboard` | `{color, brightness}` |
| `camera` | açılışta kamera açık mı |
| `power_saving` | kademeler, `auto`, `headless_on_lid`, `brightness_cap`, `freeze_apps` |

## 3. Kurallar

- Yeni anahtar `DEFAULTS`'a varsayılanıyla eklenir; eski config dosyaları bozulmadan okunur.
- Anahtar biçimi değişirse eski biçim de okunur (örnek: `boot_mode`).
