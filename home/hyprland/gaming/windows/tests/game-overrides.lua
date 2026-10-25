local configure = dofile(arg[1])
local rules = {}
hl = {
  window_rule = function(rule) rules[#rules + 1] = rule end,
  on = function() error("Fullscreen must not be enforced by event callbacks") end,
  dispatch = function() error("Existing windows must remain untouched") end,
}
configure({enable = true, excluded_classes = {}})
assert(#rules == 1)
local rule = rules[1]
assert(rule.fullscreen == true)
assert(rule.match.class == "^steam_app_default$")
assert(rule.match.title == "^World of Warcraft$")
assert(rule.match.xwayland == true)
-- The override changes only startup fullscreen; tiling, input and placement
-- remain owned by their existing policies.
for key in pairs(rule) do
  assert(key == "match" or key == "fullscreen")
end
for key in pairs(rule.match) do
  assert(key == "class" or key == "title" or key == "xwayland")
end
configure({enable = false, excluded_classes = {}})
configure({enable = true, excluded_classes = {"steam_app_default"}})
assert(#rules == 1) -- both existing escape hatches cover the override
configure({enable = true, excluded_classes = {"dialog.exe"}})
assert(#rules == 2)
print("game fullscreen overrides: passed")
