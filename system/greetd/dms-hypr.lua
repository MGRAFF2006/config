-- Minimal Hyprland Lua session for DMS greeter (Hyprland 0.55+).
-- dms-greeter -C appends the greeter start hook; do not launch qs here.

hl.env("DMS_RUN_GREETER", "1")
hl.config({
	misc = {
		disable_hyprland_logo = true,
		disable_splash_rendering = true,
	},
})
