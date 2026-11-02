local configure = dofile(arg[1])
local settings = { skip_empty = 0 }
for _, case in ipairs({
  { "0.56.2", {}, 0, 0 }, -- old live session after a package update
  { "0.57.0", {}, 1, 0 }, -- first pass: declarative load has not run yet
  { "0.57.0", {{ name = "other" }}, 1, 0 }, -- failed/absent plugin
  { "0.57.0", {{ name = "hyprexpo" }}, 1, 1 }, -- second and later passes
  { "0.56.2", {{ name = "hyprexpo" }}, 0, 0 }, -- never configure an old ABI
}) do
  local loads, configs = 0, 0
  hl = {
    version = function() return case[1] end,
    get_loaded_plugins = function() return case[2] end,
    plugin = { load = function(path)
      assert(path == "/immutable/plugin.so")
      loads = loads + 1
    end },
    config = function(value)
      assert(value.plugin.hyprexpo == settings)
      configs = configs + 1
    end,
  }
  configure("0.57.0", "/immutable/plugin.so", settings)
  assert(loads == case[3], "declare only the compatible plugin on every pass")
  assert(configs == case[4], "configure only after the compatible plugin loads")
end
print("overview lifecycle: 5 cases passed")
