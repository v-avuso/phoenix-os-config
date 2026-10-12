-- Target the pointer's screen explicitly: Kando can temporarily own keyboard focus.
return function(ranges)
  function phoenix_workspace_step(direction)
    local monitor = hl.get_monitor_at_cursor()
    local range = monitor and ranges[monitor.name]
    if not range or (direction ~= 1 and direction ~= -1) then return end
    local current = monitor.active_workspace and monitor.active_workspace.id
    local target
    if not current or current < range.first or current >= range.first + range.count then
      target = direction == 1 and range.first or range.first + range.count - 1
    else
      target = range.first + (current - range.first + direction) % range.count
    end
    hl.dispatch(hl.dsp.focus({ monitor = monitor.name }))
    hl.dispatch(hl.dsp.focus({ workspace = tostring(target) }))
  end
end
