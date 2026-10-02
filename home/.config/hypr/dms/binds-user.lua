-- DMS user keybind overrides (edit via Control Center or dms; do not remove this header)

hl.unbind("SUPER + A")
hl.bind("SUPER + A", hl.dsp.exec_cmd("dms ipc call control-center toggle"))
hl.unbind("SUPER + CTRL + L")
hl.bind("SUPER + CTRL + L", hl.dsp.exec_cmd("dms ipc call lock lock"))
hl.unbind("SUPER + CTRL + Q")
hl.bind("SUPER + CTRL + Q", hl.dsp.exec_cmd("dms ipc call powermenu toggle"))
hl.unbind("SUPER + CTRL + S")
hl.bind("SUPER + CTRL + S", hl.dsp.exec_cmd("dms screenshot full"))
hl.unbind("SUPER + R")
hl.bind("SUPER + R", hl.dsp.exec_cmd("dms ipc call spotlight toggle"))
hl.unbind("SUPER + SHIFT + S")
hl.bind("SUPER + SHIFT + S", hl.dsp.exec_cmd("dms screenshot"))
hl.unbind("SUPER + B")
hl.bind("SUPER + B", hl.dsp.exec_cmd("xdg-open https://"))
hl.unbind("SUPER + CTRL + X")
hl.bind("SUPER + CTRL + X", hl.dsp.exec_cmd("alacritty"))
hl.unbind("SUPER + E")
hl.bind("SUPER + E", hl.dsp.exec_cmd("nautilus --new-window"), { description = "Nautilus file manager" })
hl.unbind("SUPER + X")
hl.bind("SUPER + X", hl.dsp.exec_cmd("alacritty"), { description = "alacritty" })
hl.unbind("SUPER + SHIFT + R")
hl.bind("SUPER + SHIFT + R", hl.dsp.layout("togglesplit"))
hl.unbind("SUPER + T")

-- DWM-style: Super+, / Super+. → previous / next monitor
-- Add Shift to move the focused window to that monitor.
hl.unbind("SUPER + comma")
hl.unbind("SUPER + period")
hl.bind("SUPER + comma", hl.dsp.focus({ monitor = "-1" }), { description = "previous monitor" })
hl.bind("SUPER + period", hl.dsp.focus({ monitor = "+1" }), { description = "next monitor" })
hl.bind("SUPER + SHIFT + comma", hl.dsp.window.move({ monitor = "-1" }), {
	description = "move window to previous monitor",
})
hl.bind("SUPER + SHIFT + period", hl.dsp.window.move({ monitor = "+1" }), {
	description = "move window to next monitor",
})
hl.bind("SUPER + CTRL + comma", hl.dsp.exec_cmd("dms ipc call settings focusOrToggle"), {
	description = "DMS settings",
})
