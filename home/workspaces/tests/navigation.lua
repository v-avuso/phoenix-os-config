local calls = {}
local monitor = { name = "DP-2", active_workspace = { id = 11 } }
hl = {
  get_monitor_at_cursor = function() return monitor end,
  dsp = { focus = function(value) return value end },
  dispatch = function(value) calls[#calls + 1] = value end,
}
local configure = dofile(arg[1])
configure({ ["DP-1"] = { first = 1, count = 5 },
  ["HDMI-A-2"] = { first = 6, count = 5 }, ["DP-2"] = { first = 11, count = 5 } })
for _, case in ipairs({
  {"DP-1", 1, -1, 5}, {"DP-1", 5, 1, 1}, {"DP-1", 2, 1, 3},
  {"HDMI-A-2", 6, -1, 10}, {"HDMI-A-2", 10, 1, 6},
  {"DP-2", 11, 1, 12}, {"DP-2", 15, 1, 11}, {"DP-2", 11, -1, 15},
  {"DP-2", 3, 1, 11}, {"DP-2", 3, -1, 15},
}) do
  monitor = { name = case[1], active_workspace = { id = case[2] } }
  calls = {}
  phoenix_workspace_step(case[3])
  assert(calls[1].monitor == case[1], "must target pointer monitor, not keyboard focus")
  assert(calls[2].workspace == tostring(case[4]), "must stay within its group including empty slots")
end
calls = {}
monitor = { name = "unknown" }
phoenix_workspace_step(1)
assert(#calls == 0)
monitor = nil
phoenix_workspace_step(1)
assert(#calls == 0)
print("Workspace navigation: cursor monitor, empty slots, wrapping and unknown outputs passed")
