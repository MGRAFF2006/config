-- Electric glass. Kept outside DMS-generated fragments so updates preserve it.
hl.config({
	general = {
		gaps_in = 5,
		gaps_out = 10,
		border_size = 2,
		col = {
			active_border = { colors = { "rgb(58c7ff)", "rgb(56e2cb)", "rgb(a994ff)" }, angle = 45 },
			inactive_border = "rgba(65759655)",
		},
	},
	decoration = {
		rounding = 14,
		rounding_power = 3,
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
					tint = "rgba(58c7ff12)",
				},
			},
			glow = {
				enabled = true,
				range = 10,
				render_power = 3,
				color = "rgba(58c7ff32)",
				color_inactive = "rgba(58c7ff08)",
			},
		},
	})
end

hl.curve("electricOut", { type = "bezier", points = { { 0.16, 1 }, { 0.3, 1 } } })
hl.curve("electricSpring", { type = "spring", mass = 1, stiffness = 260, damping = 25 })
hl.animation({ leaf = "windowsIn", enabled = true, speed = 3.5, spring = "electricSpring", style = "popin 94%" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 2, bezier = "electricOut", style = "popin 96%" })
hl.animation({ leaf = "windowsMove", enabled = true, speed = 3.5, spring = "electricSpring" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 3, bezier = "electricOut", style = "slidefade 15%" })
hl.animation({ leaf = "fade", enabled = true, speed = 2.5, bezier = "electricOut" })
hl.animation({ leaf = "border", enabled = true, speed = 3, bezier = "electricOut" })

-- Tint selected application surfaces without fading documents in every app.
hl.window_rule({ name = "electric-tools", match = { class = "^(org\\.kde\\.dolphin|org\\.kde\\.konsole|org\\.wezfurlong\\.wezterm)$", fullscreen = false }, opacity = "0.94 0.90" })
hl.window_rule({ name = "electric-fullscreen", match = { fullscreen = true }, opacity = "1.0 override 1.0 override" })
hl.layer_rule({ name = "electric-shell-glass", match = { namespace = "^dms:.*" }, blur = true, ignore_alpha = 0.01 })
