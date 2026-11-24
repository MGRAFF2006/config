-- Wispr positions its full popup canvas itself under XWayland.
-- Only pin/style the overlay windows; keep their native sizing and input.
hl.window_rule({
	name = "wispr-flow-indicator",
	match = { class = "^(wispr-flow|Wispr Flow)$", initial_title = "^Flow Status Indicator$" },
	float = true,
	pin = true,
	no_initial_focus = true,
	-- Avoid hover focus, but allow deliberate clicks and interactive controls.
	no_follow_mouse = true,
	decorate = false,
	border_size = 0,
	no_shadow = true,
	no_blur = true,
	no_dim = true,
})

-- Menus cover the work area transparently and position their own contents.
hl.window_rule({
	name = "wispr-flow-menu",
	match = { class = "^(wispr-flow|Wispr Flow)$", initial_title = "^Flow Context Menu$" },
	float = true,
	pin = true,
	no_initial_focus = true,
	no_follow_mouse = true,
	decorate = false,
	border_size = 0,
	no_shadow = true,
	no_blur = true,
	no_dim = true,
})

-- Hyprland 0.57 selects XWayland windows by their rectangle, even outside an
-- X11 input shape. Honor the overlay's input region during that selection.
-- Optional: this shared config also runs on machines without Wispr installed.
local input_plugin = "/opt/wispr-flow-appimage/usr/lib/wispr-flow/resources/Release/wispr-hypr-input.so"
local input_file = io.open(input_plugin, "rb")
if input_file then
	input_file:close()
	hl.plugin.load(input_plugin)
end
