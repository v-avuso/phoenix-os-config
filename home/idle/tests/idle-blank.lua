local helperPath = assert(arg[1], "expected the idle helper path")
local shaderPath = assert(arg[2], "expected the black shader path")
local blackShader = "/nix/store/test-phoenix-idle-black.frag"

local function readFile(path)
  local file = assert(io.open(path, "rb"))
  local contents = file:read("*a")
  file:close()
  return contents
end

local helperTemplate = readFile(helperPath)
local shaderSource = readFile(shaderPath)
assert(shaderSource:match("#version 300 es"), "shader is not GLSL ES 300")
assert(shaderSource:match("fragColor = vec4%(0%.0, 0%.0, 0%.0, 1%.0%)"), "shader is not opaque black")

local options = {}
local configCalls = {}
local reads = {}
hl = {
  get_config = function(name)
    reads[name] = (reads[name] or 0) + 1
    return options[name]
  end,
  config = function(settings)
    configCalls[#configCalls + 1] = settings
    for key, value in pairs(settings.decoration or {}) do
      options["decoration:" .. key] = value
    end
    for key, value in pairs(settings.cursor or {}) do
      options["cursor:" .. key] = value
    end
  end,
}

local function loadHelper()
  local source = helperTemplate:gsub("@IDLE_BLACK_SHADER@", function()
    return string.format("%q", blackShader)
  end)
  local compile = loadstring or load
  local chunk, err = compile(source, "@idle-blank.lua")
  assert(chunk, err)
  chunk()
end

local function reset(shader, cursorInvisible)
  _G.phoenix_idle_blank_state = nil
  _G.phoenix_idle_blank = nil
  options = {
    ["decoration:screen_shader"] = shader,
    ["cursor:invisible"] = cursorInvisible,
  }
  configCalls = {}
  reads = {}
  loadHelper()
end

for _, initialCursor in ipairs({ false, true }) do
  reset("previous-shader.frag", initialCursor)
  phoenix_idle_blank(true)
  phoenix_idle_blank(true)
  assert(options["decoration:screen_shader"] == blackShader)
  assert(options["cursor:invisible"] == true)
  assert(#configCalls == 1, "repeated idle should apply only once")
  assert(reads["decoration:screen_shader"] == 1 and reads["cursor:invisible"] == 1,
    "repeated idle must reuse its original snapshot")

  phoenix_idle_blank(false)
  phoenix_idle_blank(false)
  assert(options["decoration:screen_shader"] == "previous-shader.frag")
  assert(options["cursor:invisible"] == initialCursor, "cursor visibility was not restored")
  assert(#configCalls == 2, "repeated wake should restore only once")
end

reset("previous-shader.frag", false)
phoenix_idle_blank(true)
options["decoration:screen_shader"] = "another-owner.frag"
phoenix_idle_blank(false)
assert(options["decoration:screen_shader"] == "another-owner.frag",
  "wake overwrote a competing shader change")
assert(options["cursor:invisible"] == false, "cursor state was not restored independently")
assert(configCalls[#configCalls].decoration == nil,
  "wake attempted to restore a shader it no longer owns")

reset("", false)
phoenix_idle_blank(true)
loadHelper()
phoenix_idle_blank(true)
assert(#configCalls == 1, "helper reload lost the in-progress snapshot")
phoenix_idle_blank(false)
assert(options["decoration:screen_shader"] == "", "empty shader option was not preserved")
assert(options["cursor:invisible"] == false)

reset("configured-shader.frag", false)
phoenix_idle_blank(true)
-- Hyprland 0.56.2 recreates its Lua state and resets config values before
-- executing the config again. Model those upstream reload semantics here.
_G.phoenix_idle_blank_state = nil
_G.phoenix_idle_blank = nil
options["decoration:screen_shader"] = "configured-shader.frag"
options["cursor:invisible"] = false
loadHelper()
phoenix_idle_blank(false)
assert(options["decoration:screen_shader"] == "configured-shader.frag",
  "config reload left the display black")
assert(options["cursor:invisible"] == false, "config reload left the cursor hidden")

reset("configured-shader.frag", false)
local normalConfig = hl.config
hl.config = function(settings)
  options["decoration:screen_shader"] = settings.decoration.screen_shader
  options["cursor:invisible"] = true
  error("fixture config failure after partial apply")
end
phoenix_idle_blank(true)
assert(phoenix_idle_blank_state.active, "partial apply discarded recovery state")
hl.config = normalConfig
phoenix_idle_blank(false)
assert(options["decoration:screen_shader"] == "configured-shader.frag",
  "wake did not restore shader after partial config failure")
assert(options["cursor:invisible"] == false,
  "wake did not restore cursor after partial config failure")
assert(not phoenix_idle_blank_state.active, "recovery snapshot remained stale")

reset("previous-shader.frag", false)
phoenix_idle_blank(false)
assert(#configCalls == 0, "wake without saved idle state must be a no-op")

print("idle blank: snapshot, idempotence, reload, ownership, and restore fixtures passed")
