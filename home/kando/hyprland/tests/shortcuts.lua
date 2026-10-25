-- Model the inspected 0.56.2 native binding boundary, not live compositor IO:
-- global() sets releasePending; auto_consuming uses ok; release forwarding uses
-- the remembered press result, even when focus/modifiers change during the hold.
local configure = dofile(arg[1])
local binds, pressed, portal, forwarded, mouse = {}, {}, {}, {}, {}
local current_bind, down, focused
local modifier_down = false
hl = {
  is_key_down = function(key) return modifier_down and key == "Control_L" end,
  get_active_window = function() return focused end,
  bind = function(key, fn, flags)
    assert(not binds[key], "duplicate binding for " .. key)
    binds[key] = {fn = fn, flags = flags}
  end,
  dispatch = function(fn) return fn() end,
  dsp = { global = function(id)
    return function()
      current_bind.pending = true
      portal[#portal + 1] = {id = id, down = down}
      return {ok = true}
    end
  end,
  send_shortcut = function(args)
    assert(args.window == nil, "native routing must not retarget pointer focus")
    return function()
      current_bind.pending = true
      mouse[#mouse + 1] = {key = args.key, mods = args.mods, down = down}
      return {ok = true}
    end
  end },
}
local is_game = dofile(arg[2])({extra_classes = {"fixture-game.exe"}, excluded_classes = {"game-dialog"}})
configure(is_game)
local function event(key, value, modified, inhibited)
  down = value == 1
  local b = assert(binds[key])
  local sent
  local allowed = (not modified or b.flags.ignore_mods) and (not inhibited or b.flags.dont_inhibit)
  if down then
    local r = {ok = true}
    if allowed then current_bind = b; b.pending = false; r = b.fn() end
    sent = not allowed or b.flags.non_consuming or (b.flags.auto_consuming and r.ok == false) or false
    pressed[key] = sent
  else
    if b.pending and allowed then current_bind = b; b.pending = false; b.fn() end
    assert(pressed[key] ~= nil)
    sent = pressed[key]
    pressed[key] = nil
    -- Intentionally retain pending: native global() sets it again on release.
    -- Another held key can prevent the native all-keys-up cleanup.
  end
  if sent then forwarded[#forwarded + 1] = {key = key, down = down} end
end
for _, key in ipairs({"F23", "F24"}) do
  focused = {tags = {"game*"}}
  local p, f, m = #portal, #forwarded, #mouse
  event(key, 1); event(key, 0)
  assert(#portal == p, "a game hold must not trigger Kando")
  assert(#forwarded == f and #mouse == m + 2, "both native mouse edges must arrive without F-key leakage")
  assert(mouse[#mouse - 1].down and not mouse[#mouse].down)
  assert(mouse[#mouse].key == (key == "F23" and "mouse:276" or "mouse:275"))

  focused = {class = "firefox"}
  p, f, m = #portal, #forwarded, #mouse
  event(key, 1)
  focused = {tags = {"game*"}}
  event(key, 0, true, true) -- modifiers/inhibitor can change while menu is held
  assert(#portal == p + 2 and portal[#portal - 1].down and not portal[#portal].down,
    "desktop press must get its portal release after focus changes")
  assert(#forwarded == f, "consumed desktop hold must not leak either edge")

  -- Exercise releasePending left over from the prior portal release.
  p, f = #portal, #forwarded
  event(key, 1)
  focused = {class = "firefox"}
  event(key, 0)
  assert(#portal == p and #forwarded == f and #mouse == m + 2, "game-to-desktop hold must finish its native release")

  p = #portal
  event(key, 1); event(key, 0)
  assert(#portal == p + 2, "Kando must be available on the next desktop press")
  assert(portal[#portal].id:find(key == "F23" and "global%-menu" or "contextual%-menu"))
  assert(binds[key].flags.transparent and binds[key].flags.auto_consuming)
end
-- Independent simultaneous holds, one routed to game and one to desktop.
focused = {class = "fixture-game.exe"}; local p, f, m = #portal, #forwarded, #mouse
event("F23", 1)
focused = nil; event("F24", 1)
event("F23", 0); event("F24", 0)
assert(#portal == p + 2 and #forwarded == f and #mouse == m + 2)
focused = {content_type = "game"}; p, f, m = #portal, #forwarded, #mouse
modifier_down = true
event("F24", 1); event("F24", 0)
assert(#portal == p and #forwarded == f and #mouse == m + 2)
assert(mouse[#mouse].mods == "CTRL")
modifier_down = false
focused = {class = "game-dialog", tags = {"game"}}; p = #portal
event("F23", 1); event("F23", 0)
assert(#portal == p + 2, "classification exclusions must also apply to input routing")
-- Roll back only native translation while retaining conditional Kando bypass.
binds, pressed = {}, {}
configure(is_game, "keys")
focused = {tags = {"game*"}}; p, f, m = #portal, #forwarded, #mouse
event("F23", 1); event("F23", 0)
assert(#portal == p and #mouse == m and #forwarded == f + 2)
print("Kando press/release routing: passed")
