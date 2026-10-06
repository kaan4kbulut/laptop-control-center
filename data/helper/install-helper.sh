#!/bin/bash
# Güç tasarrufu yardımcısını ve polkit izinlerini kurar (root). Depo kökünden:
#   pkexec bash data/helper/install-helper.sh "$PWD"
set -euo pipefail
src=${1:?depo dizini}
install -Dm755 "$src/data/helper/lcc-helper" /usr/local/libexec/lcc-helper
install -Dm644 "$src/data/polkit/io.github.laptop-control-center.helper.policy" \
    /usr/share/polkit-1/actions/io.github.laptop-control-center.helper.policy
install -Dm644 "$src/data/polkit/49-laptop-control-center.rules" \
    /etc/polkit-1/rules.d/49-laptop-control-center.rules
echo "lcc-helper kuruldu"
