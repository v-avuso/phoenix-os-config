local phoenixIdleBlackShader = @IDLE_BLACK_SHADER@
local phoenixIdleBlankState = rawget(_G, "phoenix_idle_blank_state")

if type(phoenixIdleBlankState) ~= "table" then
  phoenixIdleBlankState = { active = false }
  rawset(_G, "phoenix_idle_blank_state", phoenixIdleBlankState)
end

local function phoenixIdleReadOption(name, expectedType)
  local ok, value = pcall(hl.get_config, name)
  if not ok or type(value) ~= expectedType then
    return nil
  end
  return value
end

function phoenix_idle_blank(blank)
  if blank == true then
    if phoenixIdleBlankState.active then
      return
    end

    local shader = phoenixIdleReadOption("decoration:screen_shader", "string")
    local cursorInvisible = phoenixIdleReadOption("cursor:invisible", "boolean")
    if shader == nil or cursorInvisible == nil then
      return
    end

    phoenixIdleBlankState.shader = shader
    phoenixIdleBlankState.cursorInvisible = cursorInvisible
    phoenixIdleBlankState.active = true
    pcall(hl.config, {
      decoration = { screen_shader = phoenixIdleBlackShader },
      cursor = { invisible = true },
    })
  elseif blank == false and phoenixIdleBlankState.active then
    local shader = phoenixIdleReadOption("decoration:screen_shader", "string")
    local cursorInvisible = phoenixIdleReadOption("cursor:invisible", "boolean")
    if shader == nil or cursorInvisible == nil then
      return
    end

    local restore = {}
    if shader == phoenixIdleBlackShader then
      restore.decoration = { screen_shader = phoenixIdleBlankState.shader }
    end
    if cursorInvisible then
      restore.cursor = { invisible = phoenixIdleBlankState.cursorInvisible }
    end

    local ok = true
    if next(restore) then
      ok = pcall(hl.config, restore)
    end
    if ok then
      phoenixIdleBlankState.active = false
      phoenixIdleBlankState.shader = nil
      phoenixIdleBlankState.cursorInvisible = nil
    end
  end
end
