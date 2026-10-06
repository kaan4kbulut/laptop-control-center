// Saf yardımcılar (Nerd Font simgeleri, biçimlendirme).

function modeIcon(mode) {
  if (mode === "performance") return "󰓅"
  if (mode === "balanced") return "󰊚"
  if (mode === "quiet") return "󰖔"
  if (mode === "powersave") return "󰌪"
  return "󰈐"
}

function parse(raw) {
  try {
    var d = JSON.parse(String(raw || "").trim())
    return d && typeof d === "object" ? d : null
  } catch (e) {
    return null
  }
}

function labelOf(list, id) {
  var items = Array.isArray(list) ? list : []
  for (var i = 0; i < items.length; i++) if (items[i].id === id) return items[i].label
  return id || ""
}

// Tekerlekle sıradaki/önceki mod (pil tasarrufu modu döngüye girmez).
function cycleMode(modes, current, delta) {
  var ids = (Array.isArray(modes) ? modes : []).map(function (m) { return m.id }).filter(function (id) { return id !== "powersave" })
  if (ids.length === 0) return ""
  var i = ids.indexOf(current)
  if (i < 0) return ids[0]
  return ids[(i + delta + ids.length) % ids.length]
}

function num(v, digits) {
  if (v === undefined || v === null || isNaN(Number(v))) return "—"
  return Number(v).toFixed(digits || 0)
}

if (typeof module !== "undefined") {
  module.exports = { modeIcon: modeIcon, parse: parse, labelOf: labelOf, cycleMode: cycleMode, num: num }
}
