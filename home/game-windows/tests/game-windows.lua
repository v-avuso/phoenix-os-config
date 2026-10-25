local configure = dofile(arg[1])
local events, rules, actions = {}, {}, {}
hl = {
  window_rule = function(r) rules[#rules + 1] = r end,
  on = function(name, fn) events[name] = fn end,
  unbind = function() error("Navigation must remain unchanged") end,
  bind = function() error("Navigation must remain unchanged") end,
  dispatch = function(a) actions[#actions + 1] = a end,
  dsp = {
    window = {
      float = function(a) a.kind = "float"; return a end,
    },
  },
}
configure({extra_classes = {"wow.exe", "dialog.exe"}, excluded_classes = {"dialog.exe"},
  excluded_regex = "negative:(dialog\\.exe)"})
assert(#rules == 3 and rules[3].match.class == "^wow\\.exe$")
assert(rules[1].tile and rules[1].no_follow_mouse and rules[1].confine_pointer == false)
assert(rules[1].match.class == "negative:(dialog\\.exe)")
local function window(class, monitor, rank)
  return {address = class, class = class, monitor = {id = monitor}, focus_history_id = rank,
    mapped = true, visible = true, accepts_input = true, workspace = {active = true}}
end
local game = window("steam_app_275850", 1, 0)
game.tags, game.fullscreen, game.floating = {"game*"}, 2, true
local browser = window("firefox", 2, 2)
browser.fullscreen, browser.xwayland, browser.floating = 2, true, true
local count = #actions
events["window.open"](browser)
assert(#actions == count) -- ordinary apps untouched
events["window.open"](game)
assert(actions[#actions].kind == "float" and actions[#actions].window == game)
assert(actions[#actions].action == "unset")
game.floating = false
count = #actions
events["window.fullscreen"](game)
assert(#actions == count) -- no fullscreen transition for an already tiled game
local wine = window("wow.exe", 1, 0)
wine.floating = true
events["window.fullscreen"](wine)
assert(actions[#actions].window == wine)
local native = window("native-game", 1, 0)
native.content_type, native.floating = "game", true
events["window.update_rules"](native)
assert(actions[#actions].window == native) -- late content hint
local dialog = window("dialog.exe", 1, 0)
dialog.tags, dialog.floating = {"game"}, true
count = #actions
events["window.open"](dialog)
assert(#actions == count) -- exclusion beats both extra class and upstream tag
game.floating = true
hl.dispatch = function(a)
  actions[#actions + 1] = a
  events["window.update_rules"](a.window)
end
events["window.fullscreen"](game) -- recursive rule updates stay bounded
print("game window policy: passed")
