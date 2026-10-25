return function(options)
  if options.enable == false then return end
  for _, class in ipairs(options.excluded_classes) do
    if class == "steam_app_default" then return end
  end

  -- WoW's observed initial title identifies its main Wine window. Static
  -- fullscreen applies once at mapping, preserving subsequent manual toggles.
  hl.window_rule({
    match = {
      class = "^steam_app_default$",
      title = "^World of Warcraft$",
      xwayland = true,
    },
    fullscreen = true,
  })
end
