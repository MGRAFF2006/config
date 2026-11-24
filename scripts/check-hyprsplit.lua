-- Run from the repository root: lua scripts/check-hyprsplit.lua
-- Exercise the real dispatcher with both Hyprland integer and boolean values.
local option = 0
local dispatched
local monitor = { id = 0, name = "eDP-1", active_workspace = { id = 2 } }
hl = {
    on = function() end,
    get_active_monitor = function() return monitor end,
    get_workspace = function() return nil end,
    get_config = function() return option end,
    dispatch = function(value) dispatched = value end,
    dsp = { focus = function(value) return value end },
}
local hs = dofile("home/.config/hypr/hyprsplit/init.lua")
hs._config.num_workspaces = 9

local function focus(tag, expected)
    dispatched = nil
    hs.dsp.focus({ workspace = tag })()
    assert(dispatched and dispatched.workspace == expected,
        "option=" .. tostring(option) .. ", tag=" .. tag .. ": expected " .. expected)
end

for _, disabled in ipairs({ 0, false }) do
    option = disabled
    focus(2, "2") -- Selecting the active tag must not jump to the previous one.
    focus(3, "3")
end
for _, enabled in ipairs({ 1, true }) do
    option = enabled
    focus(2, "previous_per_monitor")
    focus(3, "3")
end
-- Monitor 1 has tags 10–18; its local tag 2 is workspace 11.
monitor.id = 1
monitor.active_workspace.id = 11
option = 0
focus(2, "11")
focus(3, "12")
option = 1
focus(2, "previous_per_monitor")
print("PASS: disabled back-and-forth stays on current tag; enabled toggle and per-monitor tag mapping retained")
