-- Electric glass. Kept outside DMS-generated fragments so updates preserve it.
hl.config({
	general = {
		gaps_in = 2,
		gaps_out = 2,
		border_size = 2,
	},
	decoration = {
		rounding = 4,
		rounding_power = 2,
		active_opacity = 1,
		inactive_opacity = 1,
		shadow = {
			enabled = true,
			range = 32,
			render_power = 3,
			offset = "0 6",
			color = "rgba(03071280)",
			color_inactive = "rgba(03071248)",
		},
		blur = {
			enabled = true,
			size = 8,
			passes = 3,
			ignore_opacity = true,
			noise = 0.015,
			contrast = 0.95,
			brightness = 0.95,
			vibrancy = 0.22,
			popups = true,
		},
	},
})

-- Hyprland 0.57 effects; older installations retain regular frosted blur.
if hl.get_config("decoration.blur.variant") ~= nil then
	hl.config({
		decoration = {
			blur = {
				variant = "acrylic",
				acrylic = {
					refraction = 10,
					bulb = 32,
					clarity = 0.25,
					aberration = 0.018,
				},
			},
			glow = {
				enabled = true,
				range = 4,
				render_power = 4,
				-- Colors come from DMS's wallpaper-derived colors.lua.
			},
		},
	})
end

hl.curve("electricOut", { type = "bezier", points = { { 0.16, 1 }, { 0.3, 1 } } })
hl.animation({ leaf = "windowsIn", enabled = true, speed = 1.6, bezier = "electricOut", style = "popin 99%" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 1.2, bezier = "electricOut", style = "popin 99%" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 1.5, bezier = "electricOut" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 1.4, bezier = "electricOut", style = "slide 3%" })
hl.animation({ leaf = "fade", enabled = true, speed = 1, bezier = "electricOut" })
hl.animation({ leaf = "border", enabled = true, speed = 1.5, bezier = "electricOut" })

-- Tint selected application surfaces without fading documents in every app.
hl.window_rule({ name = "electric-tools", match = { class = "^(org\\.kde\\.dolphin|org\\.kde\\.konsole|org\\.wezfurlong\\.wezterm)$", fullscreen = false }, opacity = "0.94 0.90" })
hl.window_rule({ name = "electric-fullscreen", match = { fullscreen = true }, opacity = "1.0 override 1.0 override" })
hl.layer_rule({ name = "electric-shell-glass", match = { namespace = "^dms:.*" }, blur = true, ignore_alpha = 0.01 })
