local root = assert(arg[1])
package.path = root .. "/?.lua;" .. package.path
-- Session startup initializes current.lua from this palette on first login.
package.loaded["scheme.current"] = require("scheme.default")
local rules, actions, windows = {}, {}, {}
local function action(kind)
    return function(value) return { kind = kind, value = value } end
end
hl = {
    window_rule = function(rule) rules[#rules + 1] = rule end,
    workspace_rule = function() end,
    layer_rule = function() end,
    get_active_special_workspace = function() return nil end,
    get_windows = function() return windows end,
    dispatch = function(value) actions[#actions + 1] = value end,
    dsp = {
        focus = action("focus"), exec_cmd = action("exec"),
        window = { move = action("move") },
        workspace = { toggle_special = action("toggle") },
    },
}
require("hyprland.rules")
local communication = {}
local routes_communication = false
for _, rule in ipairs(rules) do
    if rule.tag == "+communication_app" then
        for class in rule.match.class:gmatch("[^|]+") do communication[class] = true end
    end
    if rule.match.tag == "communication_app" and rule.workspace == "special:communication" then
        routes_communication = true
    end
end
assert(not communication.discord, "Discord must not receive the communication tag")
assert(communication.equibop and communication.vesktop and communication.whatsapp)
assert(routes_communication, "Other communication clients retain their route")

local toggle = require("utils.functions").toggle
-- Neither launch missing Discord nor move an existing one. WhatsApp still moves.
for _, discord_running in ipairs({ false, true }) do
    windows = { { class = "whatsapp", workspace = { name = "2" } } }
    if discord_running then
        windows[#windows + 1] = { class = "discord", workspace = { name = "4" } }
    end
    actions = {}
    toggle("communication")()
    local whatsapp_moved = false
    for _, entry in ipairs(actions) do
        assert(entry.kind ~= "exec", "Communication must not launch Discord")
        if entry.kind == "move" then
            assert(entry.value.window.class == "whatsapp", "Communication must not move Discord")
            assert(entry.value.workspace == "special:communication")
            whatsapp_moved = true
        end
    end
    assert(whatsapp_moved, "WhatsApp keeps move-on-toggle behavior")
end
print("Discord workspace routing and communication toggle checks passed")
