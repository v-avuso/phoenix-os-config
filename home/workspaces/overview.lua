-- Plugin loading is deferred until after the first configuration pass.
return function(version, path, settings)
  -- A system update does not replace the compositor of an existing session.
  if hl.version() ~= version then return end

  -- Declare on every pass, including the pass after the plugin has loaded.
  hl.plugin.load(path)
  for _, plugin in ipairs(hl.get_loaded_plugins()) do
    if plugin.name == "hyprexpo" then
      hl.config({ plugin = { hyprexpo = settings } })
      return
    end
  end
end
