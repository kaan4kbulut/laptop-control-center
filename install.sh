#!/bin/bash
# laptop-control-center kurulumu / installer
#
#   ./install.sh               kur veya güncelle (dosyalar ~/.local/share altına kopyalanır)
#   ./install.sh --dev         depo yerinde çalışsın (kopyalamak yerine bağlantı kurar)
#   ./install.sh --dry-run     hiçbir şeyi değiştirmeden yapılacakları göster
#   ./install.sh --yes         soru sormadan varsayılanlarla ilerle
#   ./install.sh --uninstall   kaldır (ayarlar ~/.config/laptop-control-center içinde kalır)
#
# Normal kullanıcı olarak çalıştırılır; root gereken adımlar için sudo sorulur.
# Tekrar çalıştırmak güvenlidir: var olan kurulum güncellenir.

set -euo pipefail

APP=laptop-control-center
SRC=$(cd "$(dirname "$(readlink -f "$0")")" && pwd)
SHARE="${XDG_DATA_HOME:-$HOME/.local/share}/$APP"
BINDIR="$HOME/.local/bin"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"
UNIT_DIR="$CONF/systemd/user"
HYPR_DIR="$CONF/hypr"
PLUGIN_DIR="$CONF/omarchy/plugins/$APP"
HELPER=/usr/local/libexec/lcc-helper

DEV=0 DRY=0 YES=0 UNINSTALL=0
for a in "$@"; do
  case $a in
    --dev) DEV=1 ;;
    --dry-run) DRY=1 ;;
    --yes|-y) YES=1 ;;
    --uninstall) UNINSTALL=1 ;;
    -h|--help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown option: $a" >&2; exit 2 ;;
  esac
done

# --- dil ve çıktı --------------------------------------------------------------
LANG_TR=0
[[ ${LC_ALL:-${LC_MESSAGES:-${LANG:-}}} == tr* ]] && LANG_TR=1
grep -qs '^KEYMAP=trq' /etc/vconsole.conf && LANG_TR=1
t() { if ((LANG_TR)); then printf '%s' "$1"; else printf '%s' "$2"; fi; }

if [[ -t 1 ]]; then B=$'\e[1m' C=$'\e[36m' G=$'\e[32m' Y=$'\e[33m' R=$'\e[31m' N=$'\e[0m'; else B= C= G= Y= R= N=; fi
step() { printf '\n%s==>%s %s%s%s\n' "$C" "$N" "$B" "$*" "$N"; }
ok()   { printf '  %s✓%s %s\n' "$G" "$N" "$*"; }
info() { printf '  · %s\n' "$*"; }
warn() { printf '  %s!%s %s\n' "$Y" "$N" "$*"; }
die()  { printf '%s✗ %s%s\n' "$R" "$*" "$N" >&2; exit 1; }

# Değiştiren her komut buradan geçer; --dry-run'da yalnızca yazdırılır.
run() {
  if ((DRY)); then printf '  %s$%s %s\n' "$Y" "$N" "$*"; return 0; fi
  "$@"
}
root() { run sudo "$@"; }

ask() {   # ask "soru" -> 0 evet / 1 hayır (varsayılan evet)
  ((YES || DRY)) && return 0
  local r; read -r -p "  $1 [$(t E Y)/$(t h n)] " r
  [[ -z $r || $r =~ ^[YyEe] ]]
}

write_file() {   # write_file <yol> (içerik stdin'den)
  local dest=$1 tmp
  tmp=$(mktemp)
  cat > "$tmp"
  if ((DRY)); then printf '  %s>%s %s\n' "$Y" "$N" "$dest"; rm -f "$tmp"; return; fi
  mkdir -p "$(dirname "$dest")"
  mv "$tmp" "$dest"
}

backup() { [[ -e $1 ]] && run cp -a "$1" "$1.bak.$(date +%Y%m%d-%H%M%S)"; return 0; }
has() { command -v "$1" >/dev/null 2>&1; }

# --- algılama -------------------------------------------------------------------
. /etc/os-release 2>/dev/null || true
DISTRO="${ID:-unknown} ${ID_LIKE:-}"
PKG=none
if has pacman; then PKG=pacman; elif has apt-get; then PKG=apt; elif has dnf; then PKG=dnf; fi
AUR=""
for h in paru yay; do has $h && { AUR=$h; break; }; done

VENDOR=$(cat /sys/class/dmi/id/sys_vendor 2>/dev/null || echo "?")
PRODUCT=$(cat /sys/class/dmi/id/product_name 2>/dev/null || echo "?")
CLEVO=0
ls /sys/bus/wmi/devices/ 2>/dev/null | grep -qi '^ABBC0F6[BCD]' && CLEVO=1
TUXEDO=0
[[ ${VENDOR^^} == *TUXEDO* ]] && TUXEDO=1
OMARCHY=0; has omarchy && [[ -d $HOME/.config/omarchy ]] && OMARCHY=1
HYPRLAND=0; has hyprctl && HYPRLAND=1

tccd_running() { busctl --system status com.tuxedocomputers.tccd >/dev/null 2>&1; }

# Ekran Intel'e bağlı, NVIDIA da var ve Omarchy video çözmeyi NVIDIA'ya veriyorsa
# tarayıcıda videolar siyah kalır (bkz. data/omarchy notu).
hybrid_video_fix_needed() {
  ((OMARCHY)) || return 1
  lspci 2>/dev/null | grep -qi 'vga.*nvidia\|3d.*nvidia' || [[ -d /proc/driver/nvidia ]] || return 1
  [[ -f /usr/lib/dri/iHD_drv_video.so || -f /usr/lib/x86_64-linux-gnu/dri/iHD_drv_video.so ]] || return 1
  local c
  for c in /sys/class/drm/card*-eDP-*; do
    [[ -e $c && $(cat "$c/status" 2>/dev/null) == connected ]] || continue
    [[ $(cat "$(readlink -f "$c/../device")/vendor" 2>/dev/null) == 0x8086 ]] && return 0
  done
  return 1
}

# --- kaldırma -----------------------------------------------------------------------
uninstall() {
  step "$(t "laptop-control-center kaldırılıyor" "Uninstalling laptop-control-center")"
  if systemctl --user list-unit-files lcc-daemon.service >/dev/null 2>&1; then
    run systemctl --user disable --now lcc-daemon.service || true
  fi
  run rm -f "$UNIT_DIR/lcc-daemon.service" "$BINDIR/lcc" \
            "${XDG_DATA_HOME:-$HOME/.local/share}/applications/$APP.desktop"
  run systemctl --user daemon-reload || true
  ok "$(t "servis ve komut kaldırıldı" "service and command removed")"

  if [[ -e $PLUGIN_DIR || -L $PLUGIN_DIR ]]; then
    local sj="$CONF/omarchy/shell.json"
    if [[ -f $sj ]] && has jq; then
      backup "$sj"
      if ((DRY)); then info "jq: $APP -> shell.json"; else
        jq --arg id "$APP" '(.bar.layout[]?) |= map(select(.id != $id))' "$sj" > "$sj.tmp" && mv "$sj.tmp" "$sj"
      fi
    fi
    run rm -rf "$PLUGIN_DIR"
    ok "$(t "bar eklentisi kaldırıldı" "bar plugin removed")"
  fi
  if [[ -f $HYPR_DIR/$APP.lua ]]; then
    backup "$HYPR_DIR/hyprland.lua"
    run sed -i "/require(\"hypr.$APP\")/d" "$HYPR_DIR/hyprland.lua"
    run rm -f "$HYPR_DIR/$APP.lua"
    ok "$(t "Hyprland kuralı ve kısayolu kaldırıldı" "Hyprland rule and shortcut removed")"
  fi
  if [[ -e $HELPER ]] && ask "$(t "Root yardımcısı ve polkit kuralı kaldırılsın mı (sudo)?" "Remove the root helper and polkit rule (sudo)?")"; then
    root rm -f "$HELPER" /usr/share/polkit-1/actions/io.github.laptop-control-center.helper.policy \
               /etc/polkit-1/rules.d/49-laptop-control-center.rules
    ok "$(t "yardımcı kaldırıldı" "helper removed")"
  fi
  run rm -rf "$SHARE"
  info "$(t "Ayarlar korunuyor: $CONF/$APP. tccd'deki lcc-* profilleri TCC'den silinebilir." \
            "Settings kept in $CONF/$APP. lcc-* profiles in tccd can be removed from TCC.")"
  ok "$(t "Kaldırıldı." "Uninstalled.")"
}

# --- kurulum adımları ---------------------------------------------------------------
check_user() {
  [[ $EUID -ne 0 ]] || die "$(t "root olarak değil, normal kullanıcı olarak çalıştırın." "Run as your normal user, not root.")"
  has systemctl || die "$(t "systemd gerekli." "systemd is required.")"
}

summary() {
  step "$(t "Algılanan sistem" "Detected system")"
  info "$(t "Cihaz" "Device"): $VENDOR $PRODUCT"
  info "$(t "Dağıtım" "Distribution"): $DISTRO ($PKG${AUR:+, AUR: $AUR})"
  info "Clevo WMI: $( ((CLEVO)) && t var yes || t yok no )   tccd: $(tccd_running && t "çalışıyor" running || t yok none)"
  info "Omarchy: $( ((OMARCHY)) && t var yes || t yok no )   Hyprland: $( ((HYPRLAND)) && t var yes || t yok no )"
  info "$(t "Kurulum biçimi" "Install mode"): $( ((DEV)) && echo "--dev ($SRC)" || echo "$SHARE")"
  ((DRY)) && warn "$(t "--dry-run: hiçbir şey değiştirilmeyecek" "--dry-run: nothing will be changed")"
  return 0
}

install_packages() {
  step "$(t "Bağımlılıklar" "Dependencies")"
  local need=()
  python3 -c 'import sys; assert sys.version_info >= (3, 10)' 2>/dev/null || need+=(python)
  python3 -c 'import gi; gi.require_version("Gio", "2.0")' 2>/dev/null || need+=(gobject)
  python3 -c 'import PySide6.QtQuick' 2>/dev/null || need+=(pyside6)
  has iw || need+=(iw)
  has brightnessctl || need+=(brightnessctl)
  has pkexec || need+=(polkit)
  if ((${#need[@]} == 0)); then ok "$(t "hepsi kurulu" "all present")"; return; fi
  local pkgs=()
  case $PKG in
    pacman)
      local -A map=([python]=python [gobject]=python-gobject [pyside6]=pyside6 [iw]=iw [brightnessctl]=brightnessctl [polkit]=polkit) ;;
    apt)
      local -A map=([python]=python3 [gobject]=python3-gi [pyside6]="python3-pyside6.qtquick python3-pyside6.qtqml python3-pyside6.qtgui python3-pyside6.qtcore qml6-module-qtquick-shapes qml6-module-qtquick-effects qml6-module-qtquick-dialogs" [iw]=iw [brightnessctl]=brightnessctl [polkit]=pkexec) ;;
    dnf)
      local -A map=([python]=python3 [gobject]=python3-gobject [pyside6]=python3-pyside6 [iw]=iw [brightnessctl]=brightnessctl [polkit]=polkit) ;;
    *)
      warn "$(t "Paket yöneticisi tanınmadı; şunları elle kurun:" "Unknown package manager; install these manually:") ${need[*]}"; return ;;
  esac
  local n; for n in "${need[@]}"; do pkgs+=(${map[$n]}); done
  info "$(t "Eksik" "Missing"): ${pkgs[*]}"
  ask "$(t "Kurulsun mu (sudo)?" "Install them (sudo)?")" || { warn "$(t "atlandı" "skipped")"; return; }
  case $PKG in
    pacman) root pacman -S --needed --noconfirm "${pkgs[@]}" ;;
    apt) root apt-get install -y "${pkgs[@]}" ;;
    dnf) root dnf install -y "${pkgs[@]}" ;;
  esac
  if ! ((DRY)) && ! python3 -c 'import PySide6.QtQuick' 2>/dev/null; then
    warn "$(t "PySide6 paketlerden kurulamadı; pencere için: pip install --user PySide6" \
              "PySide6 could not be installed from packages; for the window: pip install --user PySide6")"
  fi
}

install_clevo() {
  ((CLEVO)) || return 0
  step "$(t "Clevo donanım sürücüsü ve tccd" "Clevo hardware driver and tccd")"
  if tccd_running; then ok "$(t "tccd çalışıyor" "tccd is running")"; return; fi
  # Resmi tuxedo-drivers yalnızca TUXEDO cihazlarını kabul eder; diğer Clevo'lar
  # (Monster, XMG, Schenker...) için clevo-drivers çatalı gerekir.
  local drv=tuxedo-drivers-dkms
  ((TUXEDO)) || drv=clevo-drivers-dkms-git
  if [[ $PKG == pacman && -n $AUR ]]; then
    info "$(t "Gerekenler (AUR)" "Needed (AUR)"): $drv tuxedo-control-center-bin"
    if ask "$(t "$AUR ile kurulsun mu? DKMS modülü derlenecek, birkaç dakika sürebilir." "Install with $AUR? A DKMS module will be built, this can take a few minutes.")"; then
      run "$AUR" -S --needed "$drv" tuxedo-control-center-bin
      root systemctl enable --now tccd.service
      ((DRY)) || sleep 3
    fi
  else
    warn "$(t "Bu dağıtımda otomatik kurulamıyor. Şunları kurun ve tccd.service'i açın:" \
              "Cannot install automatically here. Install these and enable tccd.service:")"
    info "$drv, tuxedo-control-center  (https://www.tuxedocomputers.com/en/Linux-Hardware/TUXEDO-Control-Center.tuxedo)"
  fi
  if ! ((DRY)) && ! tccd_running; then
    warn "$(t "tccd yok; genel Linux arka ucu (power-profiles-daemon) kullanılacak." \
              "tccd not available; the generic Linux backend (power-profiles-daemon) will be used.")"
  fi
  # TCC'nin tepsi uygulaması ekran kartını uyanık tutar; arayüzü lcc sağlıyor.
  if [[ -f /etc/xdg/autostart/tuxedo-control-center-tray.desktop && ! -f $CONF/autostart/tuxedo-control-center-tray.desktop ]]; then
    write_file "$CONF/autostart/tuxedo-control-center-tray.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=TUXEDO Control Center
Hidden=true
EOF
    ok "$(t "TCC tepsi uygulamasının otomatik başlaması kapatıldı" "TCC tray autostart disabled")"
  fi
}

install_files() {
  step "$(t "Uygulama dosyaları" "Application files")"
  local base=$SRC
  if ((DEV)); then
    info "$(t "depodan çalışacak" "runs from the repository"): $SRC"
  else
    run mkdir -p "$SHARE"
    run rm -rf "$SHARE/lcc" "$SHARE/bin" "$SHARE/data"
    # -L: depodaki bağlantılar (ör. eklentinin fonts/ klasörü) gerçek dosya olarak kopyalanır
    run cp -rL "$SRC/lcc" "$SRC/bin" "$SRC/data" "$SHARE/"
    ((DRY)) || find "$SHARE/lcc" -name __pycache__ -type d -prune -exec rm -rf {} +
    base=$SHARE
  fi
  run mkdir -p "$BINDIR"
  run ln -sfn "$base/bin/lcc" "$BINDIR/lcc"
  ok "$BINDIR/lcc -> $base/bin/lcc"
  case ":$PATH:" in *":$BINDIR:"*) ;; *) warn "$(t "$BINDIR PATH'te değil; kabuk ayarınıza ekleyin." "$BINDIR is not in PATH; add it to your shell profile.")" ;; esac
  sed "s|@BINDIR@|$BINDIR|g" "$SRC/data/$APP.desktop" | write_file "${XDG_DATA_HOME:-$HOME/.local/share}/applications/$APP.desktop"
  ok "$(t "uygulama menüsü girdisi" "application menu entry")"
  BASE=$base
}

install_helper() {
  step "$(t "Root yardımcısı (pil tasarrufu, kamera, fan eğrisi)" "Root helper (power saving, camera, fan curve)")"
  local want have
  want=$(sed -n 's/^VERSION=//p' "$SRC/data/helper/lcc-helper")
  have=$(sed -n 's/^VERSION=//p' "$HELPER" 2>/dev/null || echo 0)
  if [[ -x $HELPER ]] && cmp -s "$SRC/data/helper/lcc-helper" "$HELPER"; then
    ok "$(t "güncel (sürüm $have)" "up to date (version $have)")"; return
  fi
  info "$(t "Kurulacak" "Will install"): $HELPER, polkit action + $(t "kural (wheel grubu parolasız)" "rule (wheel group, no password)")"
  if ask "$(t "Kurulsun mu (sudo)?" "Install it (sudo)?")"; then
    root bash "$SRC/data/helper/install-helper.sh" "$SRC"
    ok "$(t "yardımcı sürüm $want" "helper version $want")"
  else
    warn "$(t "atlandı: pil tasarrufunun root adımları, kamera ve fan eğrisi kaydı çalışmaz" \
              "skipped: power saving root steps, camera and fan curve saving will not work")"
  fi
  id -nG | grep -qw wheel || warn "$(t "Kullanıcınız wheel grubunda değil; yardımcı parola soracak." \
                                       "Your user is not in the wheel group; the helper will ask for a password.")"
}

setup_backend() {
  ((DRY)) && { step "$(t "Donanım profilleri" "Hardware profiles")"; info "lcc setup"; return; }
  tccd_running || return 0
  step "$(t "Donanım profilleri (tccd)" "Hardware profiles (tccd)")"
  if "$BINDIR/lcc" setup; then ok "$(t "lcc-* profilleri yazıldı" "lcc-* profiles written")"
  else warn "$(t "profiller yazılamadı; sonra 'lcc setup' çalıştırın" "could not write profiles; run 'lcc setup' later")"; fi
}

install_service() {
  step "$(t "Arka plan servisi" "Background service")"
  sed "s|@BINDIR@|$BINDIR|g" "$SRC/data/systemd/lcc-daemon.service" | write_file "$UNIT_DIR/lcc-daemon.service"
  # Eski ayrı 60 Hz servisi artık lcc-daemon'un içinde.
  if [[ -f $UNIT_DIR/power-watch.service ]] && grep -q "$APP" "$UNIT_DIR/power-watch.service"; then
    run systemctl --user disable --now power-watch.service || true
    info "$(t "eski power-watch.service kapatıldı" "old power-watch.service disabled")"
  fi
  run systemctl --user daemon-reload
  run systemctl --user enable lcc-daemon.service
  run systemctl --user restart lcc-daemon.service
  ok "lcc-daemon.service"
}

install_omarchy() {
  ((OMARCHY && HYPRLAND)) || return 0
  step "Omarchy / Hyprland"
  # bar eklentisi
  run mkdir -p "$(dirname "$PLUGIN_DIR")"
  run rm -rf "$PLUGIN_DIR"
  if ((DEV)); then run ln -sfn "$SRC/data/omarchy/$APP" "$PLUGIN_DIR"
  else run cp -rL "$BASE/data/omarchy/$APP" "$PLUGIN_DIR"; fi
  local sj="$CONF/omarchy/shell.json"
  if [[ -f $sj ]] && has jq && jq -e --arg id "$APP" '[.bar.layout[]?[]?.id] | index($id)' "$sj" >/dev/null 2>&1; then
    ok "$(t "bar eklentisi güncellendi" "bar plugin updated")"
  else
    run omarchy bar put "$APP" --before omarchy.monitor || run omarchy bar put "$APP"
    ok "$(t "bar eklentisi eklendi" "bar plugin added")"
  fi
  ((DRY)) || omarchy restart shell >/dev/null 2>&1 || true

  # pencere kuralı, Super+F5, gerekirse hibrit ekran kartı video düzeltmesi
  local hl="$HYPR_DIR/hyprland.lua" lua="$HYPR_DIR/$APP.lua" libva=""
  if hybrid_video_fix_needed && ! grep -qs 'LIBVA_DRIVER_NAME", "iHD"' "$hl"; then
    libva=$(cat <<'EOF'

-- Hibrit laptop: ekran Intel kartına bağlı. Omarchy NVIDIA görünce video çözmeyi
-- NVIDIA'ya veriyor; tarayıcıda videolar siyah kalıyordu. Video çözmeyi Intel yapsın.
hl.env("LIBVA_DRIVER_NAME", "iHD")
EOF
)
  fi
  write_file "$lua" <<EOF
-- laptop-control-center (install.sh tarafından yazıldı; yeniden kurulumda üzerine yazılır)

-- Ana pencere yüzer, ortada açılır, tasarım oranında (1280×760).
-- Siyah zemin tasarımın parçası; Omarchy'nin varsayılan saydamlığı uygulanmasın.
o.window("^$APP\$", {
  float = true,
  center = true,
  size = { 1600, 950 },
  tag = "-default-opacity",
})
o.window("^$APP\$", { opacity = "1 1" })

-- Super+F5: performans modları arasında geç (ekranda gösterge çıkar).
o.bind("SUPER + F5", "$(t "Performans modunu değiştir" "Cycle performance mode")", "$BINDIR/lcc mode next --notify")
$libva
EOF
  if [[ -f $hl ]] && ! grep -q "require(\"hypr.$APP\")" "$hl"; then
    backup "$hl"
    if grep -q 'require("hypr.autostart")' "$hl"; then
      run sed -i "s|^require(\"hypr.autostart\")|&\nrequire(\"hypr.$APP\")|" "$hl"
    else
      ((DRY)) || printf '\nrequire("hypr.%s")\n' "$APP" >> "$hl"
    fi
  fi
  if ! ((DRY)); then
    sleep 2
    if [[ -n $(hyprctl configerrors 2>/dev/null | tr -d '[:space:]') ]]; then
      warn "$(t "Hyprland yapılandırma hatası bildirdi; require satırı geri alınıyor:" "Hyprland reported config errors; reverting the require line:")"
      hyprctl configerrors | head -5
      sed -i "/require(\"hypr.$APP\")/d" "$hl"
    else
      ok "$(t "pencere kuralı ve Super+F5" "window rule and Super+F5")${libva:+ + $(t "hibrit video düzeltmesi" "hybrid video fix")}"
    fi
  fi
}

finish() {
  step "$(t "Bitti" "Done")"
  if ! ((DRY)); then
    systemctl --user is-active --quiet lcc-daemon.service && ok "lcc-daemon $(t "çalışıyor" "running")" || warn "lcc-daemon $(t "çalışmıyor: journalctl --user -u lcc-daemon" "not running: journalctl --user -u lcc-daemon")"
    "$BINDIR/lcc" status 2>/dev/null | head -6 | sed 's/^/  /' || true
  fi
  info "$(t "Pencere: lcc gui (uygulama menüsünde 'Kontrol Merkezi')" "Window: lcc gui (\"Control Center\" in the app menu)")"
  info "$(t "Komutlar: lcc --help" "Commands: lcc --help")"
  ((OMARCHY)) && info "$(t "Bar: sağ üstteki mod simgesi · Super+F5 modlar arasında geçer" "Bar: mode icon at the top right · Super+F5 cycles modes")"
  return 0
}

check_user
if ((UNINSTALL)); then uninstall; exit 0; fi
summary
ask "$(t "Kuruluma devam edilsin mi?" "Continue with the installation?")" || exit 0
install_packages
install_clevo
install_files
install_helper
setup_backend
install_service
install_omarchy
finish
