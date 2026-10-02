-- Bind Wacom Movink pen/touch to the Movink display (not whichever
-- screen the cursor is on). Connector name flips (DP-1 vs DP-2), so we
-- resolve by monitor description and re-apply on connect/reload.

local WACOM_DESC = "Wacom DTH135"
local PEN = "wacom-movink-13-pen"
local FINGER = "wacom-movink-13-finger"

-- Hyprland keeps one pointer position for mice and tablet tools. Preserve the
-- last mouse/touchpad position and restore it when the pen leaves proximity.
hl.exec_cmd("systemctl --user start wacom-cursor-restore.service")

local function find_movink()
	for _, m in ipairs(hl.get_monitors() or {}) do
		local desc = m.description or ""
		if desc:find(WACOM_DESC, 1, true) then
			return m
		end
	end
	return nil
end

local function bind_wacom()
	local m = find_movink()
	if not m then
		return
	end
	local out = m.name
	hl.device({ name = PEN, output = out })
	hl.device({ name = FINGER, output = out })
end

bind_wacom()
hl.on("hyprland.start", bind_wacom)
hl.on("config.reloaded", bind_wacom)
hl.on("monitor.added", function()
	bind_wacom()
	-- Tablet nodes can enumerate slightly after the DRM connector.
	hl.timer(bind_wacom, { timeout = 500, type = "oneshot" })
	hl.timer(bind_wacom, { timeout = 2000, type = "oneshot" })
end)
hl.on("monitor.removed", bind_wacom)
