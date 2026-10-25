-- Pure classification of Hyprland window metadata; no compositor calls.
return function(options)
  local extra, excluded = {}, {}
  for _, class in ipairs(options.extra_classes) do extra[class] = true end
  for _, class in ipairs(options.excluded_classes) do excluded[class] = true end

  return function(w)
    if not w or excluded[w.class] then return false end
    if extra[w.class] or w.content_type == "game" then return true end
    for _, tag in ipairs(w.tags or {}) do
      if tag == "game" or tag == "game*" then return true end
    end
    return false
  end
end
