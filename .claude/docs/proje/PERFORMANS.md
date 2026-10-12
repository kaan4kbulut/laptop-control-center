# Performans

## Mod ölçümleri (2026-10-12, Monster Tulpar T6 V3.7, i9-13900HX + RTX 5070 Ti Laptop)

| Mod | İşlemci | Ekran kartı saat tavanı |
|---|---|---|
| Performans | tek iş parçacığı 5,37 GHz; 8 iş parçacığı 4,8; 32 iş parçacığı 3,7 GHz | sınırsız |
| Eğlence | tavan 4,5 GHz (yükte 3,8 ölçüldü), boşta 0,8 GHz | 2163 MHz |
| Sessiz | turbo kapalı, en çok 2,2 GHz (yükte 2,0) | 1390 MHz |

`nvidia-smi -pl` (güç sınırı) bu cihazda desteklenmiyor; saat tavanı (`-lgc`) çalışıyor ve kart uyuyup uyanınca korunuyor.

## Güç

- Boşta NVIDIA kartı tamamen uyur (runtime D3). Bunu bozan şeyler bulundu ve düzeltildi: `lcc bar`'ın `lspci` ve
  `nvidia-smi` çağırması, voxtype ekran göstergesinin NVIDIA'da çizmesi.
- Daemon olay güdümlü (UPower/tccd sinyalleri, inotify); yoklama yalnızca kapak denetiminde.
