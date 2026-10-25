return function(is_game, game_buttons)
  assert(type(is_game) == "function", "Kando requires the Phoenix game classifier")
  game_buttons = game_buttons or "mouse"
  local function modifiers()
    local mods = {}
    for _, entry in ipairs({
      {"SHIFT", "Shift_L", "Shift_R"}, {"CTRL", "Control_L", "Control_R"},
      {"ALT", "Alt_L", "Alt_R"}, {"SUPER", "Super_L", "Super_R"},
      {"MOD5", "ISO_Level3_Shift", "Mode_switch"},
      {"MOD3", "ISO_Level5_Shift", "ISO_Level5_Latch"},
    }) do
      if hl.is_key_down(entry[2]) or hl.is_key_down(entry[3]) then mods[#mods + 1] = entry[1] end
    end
    return table.concat(mods, " ")
  end
  for key, entry in pairs({ F23 = {"global-menu", 276}, F24 = {"contextual-menu", 275} }) do
    local shortcut = hl.dsp.global("menu.kando.Kando:" .. entry[1])
    local held_action
    hl.bind(key, function()
      -- Both global() and send_shortcut() request a native release callback.
      -- Latch its route at press; focus changes cannot start a different action.
      if held_action then
        local finish = held_action
        held_action = nil
        return finish()
      end
      if is_game(hl.get_active_window()) then
        -- Keys mode retains the previous auto_consuming passthrough behavior.
        if game_buttons == "keys" then return { ok = false } end
        held_action = function()
          -- No window selector: use ordinary pointer focus without focus changes
          -- or fake pointer coordinates. Re-read held modifiers on both edges.
          return hl.dispatch(hl.dsp.send_shortcut({ mods = modifiers(), key = "mouse:" .. entry[2] }))
        end
      else
        held_action = function() return hl.dispatch(shortcut) end
      end
      return held_action()
    end, {
      auto_consuming = true,
      -- Do not shadow the pending portal release, including when modifiers or
      -- shortcut inhibition change during the hold. Session-lock rules remain.
      transparent = true, ignore_mods = true, dont_inhibit = true,
    })
  end
end
