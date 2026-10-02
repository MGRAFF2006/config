-- DWM-style per-monitor tags via hyprsplit.
-- Super+N switches tag N on the *focused* monitor only; other monitors stay put.

local hs = require("hyprsplit")

hs.config({
	num_workspaces = 9,
	-- false: empty tags disappear (DWM-like); Super+N still jumps to that number
	persistent_workspaces = false,
	-- Prefer laptop first so tags 1–9 stay on eDP-1; external gets 11–19, …
	force_monitor_priority = true,
})
hs.monitor_priority({ "eDP-1" })

-- Replace global workspace binds from dms.binds with per-monitor tags.
for i = 1, 9 do
	local n = tostring(i)
	hl.unbind("SUPER + " .. n)
	hl.unbind("SUPER + SHIFT + " .. n)
	hl.bind("SUPER + " .. n, hs.dsp.focus({ workspace = i }), {
		description = "tag " .. n .. " (this monitor)",
	})
	hl.bind("SUPER + SHIFT + " .. n, hs.dsp.window.move({ workspace = i, follow = false }), {
		description = "move to tag " .. n .. " (this monitor)",
	})
end

-- Relative tag switches also stay on the current monitor.
local rel = {
	{ "SUPER + Page_Down", "e+1" },
	{ "SUPER + Page_Up", "e-1" },
	{ "SUPER + U", "e+1" },
	{ "SUPER + I", "e-1" },
	{ "SUPER + mouse_down", "e+1" },
	{ "SUPER + mouse_up", "e-1" },
}
for _, b in ipairs(rel) do
	hl.unbind(b[1])
	hl.bind(b[1], hs.dsp.focus({ workspace = b[2] }))
end

local mov = {
	{ "SUPER + CTRL + down", "e+1" },
	{ "SUPER + CTRL + up", "e-1" },
	{ "SUPER + CTRL + U", "e+1" },
	{ "SUPER + CTRL + I", "e-1" },
	{ "SUPER + SHIFT + Page_Down", "e+1" },
	{ "SUPER + SHIFT + Page_Up", "e-1" },
	{ "SUPER + SHIFT + U", "e+1" },
	{ "SUPER + SHIFT + I", "e-1" },
	{ "SUPER + CTRL + mouse_down", "e+1" },
	{ "SUPER + CTRL + mouse_up", "e-1" },
}
for _, b in ipairs(mov) do
	hl.unbind(b[1])
	hl.bind(b[1], hs.dsp.window.move({ workspace = b[2], follow = true }))
end
