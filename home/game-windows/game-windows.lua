-- Policy uses compositor state only: no subprocesses, polling or monitor names.
return function(options)
  local extra, excluded = {}, {}
  for _, class in ipairs(options.extra_classes) do extra[class] = true end
  for _, class in ipairs(options.excluded_classes) do excluded[class] = true end

  local function is_game(w)
    if not w or excluded[w.class] then return false end
    if extra[w.class] or w.content_type == "game" then return true end
    for _, tag in ipairs(w.tags or {}) do
      if tag == "game" or tag == "game*" then return true end
    end
    return false
  end

  local function rule(match)
    if next(excluded) then match.class = options.excluded_regex end
    hl.window_rule({ match = match, tile = true, no_follow_mouse = true,
      focus_on_activate = false, confine_pointer = false })
  end
  rule({ tag = "game" })
  rule({ content = "game" })
  for class in pairs(extra) do
    if not excluded[class] then
      -- Exact class matches are escaped using Lua patterns only for construction
      -- of the compositor's RE2 expression (escape every RE2 metacharacter).
      local escaped = class:gsub("([\\.^$|?*+(){}%[%]])", "\\%1")
      hl.window_rule({ match = { class = "^" .. escaped .. "$" }, tile = true,
        no_follow_mouse = true, focus_on_activate = false, confine_pointer = false })
    end
  end

  -- tile is static. Reconcile late content/tag classification and fullscreen
  -- transitions, addressing only the event's window and never changing its WS.
  local reconciling = {}
  local function reconcile(w)
    if not w or not w.mapped or not w.floating or not is_game(w) or reconciling[w.address] then return end
    reconciling[w.address] = true
    hl.dispatch(hl.dsp.window.float({ action = "unset", window = w }))
    reconciling[w.address] = nil
  end
  hl.on("window.open", reconcile)
  hl.on("window.fullscreen", reconcile)
  hl.on("window.update_rules", reconcile)

end
