PanelTemplates_SelectTab = function(tab) tab:SetEnabled(false) end
PanelTemplates_DeselectTab = function(tab) tab:SetEnabled(true) end
PanelTemplates_TabResize = function() end
-- Executes the locally supplied, unmodified OPie renderer and visual notification.
-- WoW frame rendering, secure snippets and taint are NOT emulated by this fixture.
local toolkitSource, opieSource = assert(arg[1]), assert(arg[2])
local now, timers, frames = 0, {}, {}
local nativeInputs, angle, nested, modifier = 0, 0, false, false
local function noop() end
unpack = table.unpack or unpack
wipe = function(t) for k in pairs(t) do t[k] = nil end end
sin = function(v) return math.sin(math.rad(v)) end
cos = function(v) return math.cos(math.rad(v)) end
GetTime = function() return now end
GetBuildInfo = function() return '12.1.5', '', '', 120105 end
GetFramerate = function() return 60 end
GetPhysicalScreenSize = function() return 1920, 1080 end
GetScreenWidth = function() return 1920 end
GetCursorPosition = function() return 960, 540 end
GetFileIDFromPath = function() return nil end -- Local add-on textures can remain file paths.
issecretvalue = function() return false end
secretwrap = function(v) return v end
IsAltKeyDown = function() return modifier end
IsControlKeyDown, IsShiftKeyDown, IsMetaKeyDown = function() return false end, function() return false end, function() return false end
MouselookStop = noop
C_GamePad = { IsEnabled = function() return false end }
C_Texture = { GetAtlasInfo = function() return nil end }
C_KeyBindings = { GetBindingByKey = function() return nil end }
LootAlertSystem = { alertFramePool = { GetNextActive = function() return false end } }
C_Timer = { After = function(delay, callback) timers[#timers + 1] = { due = now + delay, callback = callback } end }
securecall = function(fn, ...) return fn(...) end
function hooksecurefunc(object, method, callback)
    local original = assert(object[method], method)
    object[method] = function(...)
        local result = table.pack(original(...))
        callback(...)
        return table.unpack(result, 1, result.n)
    end
end
function EnumerateFrames(previous)
    if not previous then return frames[1] end
    for i, frame in ipairs(frames) do if frame == previous then return frames[i + 1] end end
end
local Methods = {}
local function object(kind, name, parent)
    local f = setmetatable({ kind = kind, name = name, parent = parent, alpha = 1, scale = 1,
        shown = true, scripts = {}, children = {}, regions = {}, points = {} }, { __index = Methods })
    if parent then parent.children[#parent.children + 1] = f end
    if name then _G[name] = f end
    frames[#frames + 1] = f
    return f
end
function Methods:IsForbidden() return false end
function Methods:IsProtected() return self.protected or false end
function Methods:IsObjectType(kind) return self.kind == kind end
function Methods:GetName() return self.name end
function Methods:GetParent() return self.parent end
function Methods:GetChildren() return table.unpack(self.children) end
function Methods:GetRegions() return table.unpack(self.regions) end
function Methods:SetParent(parent) self.parent = parent end
function Methods:SetSize(w, h) self.w, self.h = w, h end
function Methods:SetHeight(h) self.h = h end
function Methods:SetScrollChild(child) self.scrollChild = child end
function Methods:SetVerticalScroll() end
function Methods:GetSize() return self.w, self.h end
function Methods:SetFrameStrata(v) self.strata = v end
function Methods:GetFrameStrata() return self.strata end
function Methods:SetFrameLevel(v) self.level = v end
function Methods:GetFrameLevel() return self.level end
function Methods:SetPoint(...) self.points = { ... } end
function Methods:ClearAllPoints() self.points = {} end
function Methods:GetCenter() return 960, 540 end
function Methods:SetScale(v) self.scale = v end
function Methods:GetScale() return self.scale end
function Methods:GetEffectiveScale() return self.scale * (self.parent and self.parent:GetEffectiveScale() or 1) end
function Methods:SetAlpha(v) assert(not self:IsProtected(), 'protected alpha mutation'); self.alpha = v end
function Methods:GetAlpha() return self.alpha end
function Methods:GetEffectiveAlpha() return self.alpha * (self.parent and self.parent:GetEffectiveAlpha() or 1) end
function Methods:IsShown() return self.shown end
function Methods:IsVisible() return self.shown and (not self.parent or self.parent:IsVisible()) end
function Methods:SetShown(v)
    local changed = self.shown ~= v
    self.shown = v
    if changed then
        local event = v and 'OnShow' or 'OnHide'
        if self.scripts[event] then self.scripts[event](self) end
    end
end
function Methods:Show() self:SetShown(true) end
function Methods:Hide() assert(not self:IsProtected(), 'protected Hide'); self:SetShown(false) end
function Methods:SetScript(key, callback) self.scripts[key] = callback end
function Methods:GetScript(key) return self.scripts[key] end
function Methods:CreateTexture(name)
    local t = object('Texture', name, nil); t.parent = self
    self.regions[#self.regions + 1] = t
    return t
end
function Methods:SetTexture(path) self.texture = type(path) == 'string' and (GetFileIDFromPath(path) or path) or path end
function Methods:GetTexture() return self.texture end
function Methods:GetTexCoord() return 0, 0, 0, 0, 0 end
function Methods:CreateAnimationGroup()
    return setmetatable({ CreateAnimation = function() return setmetatable({}, { __index = function() return noop end }) end },
        { __index = function() return noop end })
end
function Methods:SetOwner(owner) self.owner = owner end
function Methods:IsOwned(owner) return self.owner == owner end
function Methods:CreateFontString() return object('FontString') end
function Methods:SetValue(v)
    self.value = v
    if self.scripts.OnValueChanged then self.scripts.OnValueChanged(self, v) end
end
function Methods:SetEnabled(v) self.enabled = v end
function Methods:SetChecked(v) self.checked = v end
function Methods:GetChecked() return self.checked end
function Methods:GetText() return self.text end
function Methods:ClearFocus() if self.scripts.OnEditFocusLost then self.scripts.OnEditFocusLost(self) end end
function Methods:GetStatusBarTexture() return self.statusTexture end
function Methods:SetStatusBarTexture() self.statusTexture = self:CreateTexture() end
for _, name in ipairs({ 'SetVertexColor', 'SetAlphaFromBoolean', 'SetTexCoord', 'SetTexelSnappingBias',
    'SetSnapToPixelGrid', 'SetRotation', 'SetMinMaxValues', 'SetLooping', 'SetAnimationSpeedMultiplier',
    'ClearLines', 'AddLine', 'SetText', 'SetIcon', 'SetIconTexCoord', 'SetIconAtlas', 'SetIconVertexColor',
    'SetDominantColor', 'SetOverlayIcon', 'SetOverlayIconVertexColor', 'SetUsable', 'SetCount',
    'SetBinding', 'SetCooldown', 'SetCooldownTextShown', 'SetShortLabel', 'SetCooldownDuration',
    'SetEquipState', 'SetHighlighted', 'SetActive', 'SetOuterGlow', 'SetQualityOverlay',
    'SetJustifyH', 'SetWordWrap', 'SetValueStep', 'SetObeyStepOnDrag', 'SetAutoFocus', 'SetNumeric',
    'SetMaxLetters', 'RegisterEvent' }) do Methods[name] = noop end
function Methods:SetText(text) self.text = text end
function Methods:SetFontObject() end
function Methods:SetIcon(icon) self.icon = icon end
function Methods:SetHighlighted(value) self.highlighted = value end
function CreateFrame(kind, name, parent, template)
    local frame = object(kind, name, parent)
    if template == 'UICheckButtonTemplate' then frame.Text = object('FontString', nil, frame) end
    return frame
end
UIParent = CreateFrame('Frame', 'UIParent')
GameTooltip = CreateFrame('GameTooltip', 'GameTooltip', UIParent)
GameTooltip_SetDefaultAnchor = function(tip, owner) tip:SetOwner(owner) end
local tip = CreateFrame('GameTooltip', 'NotGameTooltip1', UIParent)
local options = { RingScale = 1, InteractionMode = 1, RingAtMouse = false, IndicationOffsetX = 0,
    IndicationOffsetY = 0, SliceBinding = false }
local PC = { GetPartialHintRaw = function() end }
function PC:RegisterOption(key, value) options[key] = value end
function PC:GetOpenRing(config)
    if config then for k, v in pairs(options) do config[k] = v end end
    return 'TestRing', 3, 0
end
function PC:GetCurrentInputs() nativeInputs = nativeInputs + 1; return 'cursor', nil, angle, true, 0 end
function PC:GetOpenRingSlice() return 1, 'token', nil, nil, nested and 2 or 0, 'ring', false end
function PC:GetOpenRingSliceAction(index) return 'slice:' .. index, true, 0, 1000 + index, 'Slice ' .. index, 0, 0, 0, nil, nil, nil, 'Slice' end
local EV = { After = function(delay, fn) C_Timer.After(delay, fn) end, UnregisterEvent = noop }
local T = { OPieCore = PC, Evie = EV, NotGameTooltip = tip, L = function(text) return text end,
    Niji = { _tex = {}, _pal = {} }, exUI = { Create = function(_, _, name, parent) return object('Frame', name, parent) end } }
OPie = { HUM = { NotGameTooltip = tip } }
assert(loadfile(opieSource .. '/UI/RingView.lua'))('OPie', T)
local core = CreateFrame('Button', 'OPieRT-12345678-abcd', UIParent)
core.protected = true
-- Run OPie's real notification callback with its original local dependencies.
local handle = assert(io.open(opieSource .. '/OPieCore.lua', 'rb'))
local coreSource = handle:read('*a'); handle:close()
local notification = assert(coreSource:match('(function OR_SecCore:NotifyState.-\nend)\n\n%-%- Responding to WoW Events'))
local environment = setmetatable({ OR_SecCore = core, ORI = T.OPieUI,
    coreEnvW = { activeRing = { name = 'TestRing' }, openCollection = { 1, 2, 3 } },
    markSliceBindings = noop, OR_PadStickCapture = { Release = noop }, OR_PadRestoreState = {},
    OR_GetEffectiveGlobalOption = function() return false end }, { __index = _G })
core.CheckCVars = noop
assert(load(notification, '@OPieCore.lua:NotifyState', 't', environment))()
local toolkit = {}
assert(loadfile(toolkitSource .. '/features/opie-visual-delay/Renderer.lua'))('PhoenixWoWToolkit', toolkit)
-- Real client dimensions are rounded; the protected notification frame need not
-- remain a direct UIParent child (for example after another add-on reparents it).
for _, frame in ipairs(UIParent.children) do
    if frame.w == 150 and frame.level == 100 then frame:SetSize(149.99446105957, 149.99446105957) end
end
for i, frame in ipairs(UIParent.children) do
    if frame == core then table.remove(UIParent.children, i); break end
end
core.parent = nil
local view, why = toolkit.OPieDelay.Find()
assert(view, why)
local width, height = view.main:GetSize()
view.main:SetSize(149, 150)
assert(not toolkit.OPieDelay.Find(), 'materially different dimensions must fail closed')
view.main:SetSize(width, height)
local extraCore = object('Button', 'OPieRT-87654321-dcba')
extraCore.protected, extraCore.NotifyState = true, core.NotifyState
assert(not toolkit.OPieDelay.Find(), 'ambiguous notification frames must fail closed')
extraCore.NotifyState = nil
assert(toolkit.OPieDelay.Find())
local pointer = view.main.regions[1]
local filename = pointer.texture
pointer.texture, GetFileIDFromPath = 777, function() return 777 end
assert(toolkit.OPieDelay.Find(), 'numeric texture representation')
pointer.texture, GetFileIDFromPath = filename, function() return nil end
local gate = arg[3] == 'baseline' and { Configure = noop } or toolkit.OPieDelay.Bind(view)
gate:Configure(true, 50)
local function invisible()
    assert(view.main:GetAlpha() == 0 and view.proxy:GetAlpha() == 0, 'ring leaked')
    if view.tip:IsOwned(view.proxy) then assert(view.tip:GetAlpha() == 0, 'tooltip leaked') end
end
local function advance(dt)
    local target = now + dt
    while now < target - 1e-9 do
        local step = math.min(1/240, target - now); now = now + step
        local due = timers; timers = {}
        for _, timer in ipairs(due) do
            if timer.due <= now + 1e-9 then timer.callback() else timers[#timers + 1] = timer end
        end
        for _, frame in ipairs(frames) do
            local fn = frame:GetScript('OnUpdate')
            if fn and frame:IsVisible() then fn(frame, step) end
        end
    end
end
local function notify(state) core:NotifyState(state, 'TestRing', 1) end
-- Native source still gets cursor updates during the hidden interval.
notify('open'); invisible()
local inputs = nativeInputs
advance(.020); invisible(); assert(nativeInputs > inputs)
angle, modifier, nested = 120, true, true
advance(.010); invisible()
local highlighted
for _, child in ipairs(view.main.children) do
    if child.highlighted then highlighted = child.icon end
end
assert(highlighted == 1001, 'native directional slice selection must update while invisible')
notify('close'); invisible()
advance(.30)
assert(not view.main:IsShown(), 'native close animation must still complete')
-- Stale timers after close/reopen cannot reveal a new ring early.
for i = 1, 8 do
    notify('open'); advance(.010); invisible(); notify('close')
end
notify('open'); advance(.049); invisible()
advance(.002); assert(view.main:GetAlpha() > 0 and view.tip:GetAlpha() > 0)
-- Nested switch keeps a visible ring visible and a hidden ring's original deadline.
notify('switch'); assert(not gate.hidden)
notify('close'); advance(.3)
notify('open'); advance(.030); notify('switch'); advance(.019); invisible()
advance(.002); assert(not gate.hidden)
-- Restore native alpha on disabling, even during an opening animation.
notify('close'); notify('open'); advance(.020); invisible()
local expected = gate.alpha[view.main]
gate:Configure(false, 50); assert(view.main:GetAlpha() == expected)
advance(.1); assert(not gate.hidden)
-- Zero delay, native animations disabled, another tooltip owner, early disable/re-enable.
gate:Configure(true, 0); notify('open'); assert(not gate.hidden)
notify('close'); advance(.3)
options.XTAnimation = false
gate:Configure(true, 50); notify('open'); invisible()
view.tip:SetOwner(UIParent); assert(view.tip:GetAlpha() > 0, 'unrelated tooltip suppressed')
view.tip:SetOwner(view.proxy); invisible()
gate:Configure(false, 50); gate:Configure(true, 50)
notify('close'); notify('open'); advance(.049); invisible(); advance(.002); assert(not gate.hidden)
-- Max delay and cancellation with no native close animation.
gate:Configure(true, 250); notify('close'); notify('open'); advance(.249); invisible()
advance(.002); assert(not gate.hidden)
notify('close')
assert(type(core.NotifyState) == 'function' and core:IsProtected())
-- Structure checks must fail before adding hooks or touching any alpha.
local notificationFunction = core.NotifyState
core.NotifyState = nil
assert(not toolkit.OPieDelay.Find(), 'missing lifecycle function must fail closed')
core.NotifyState = notificationFunction
local duplicate = object('Frame', nil, UIParent)
duplicate:SetSize(150, 150); duplicate:SetFrameStrata('FULLSCREEN'); duplicate:SetFrameLevel(100)
duplicate:CreateTexture():SetTexture(filename)
assert(not toolkit.OPieDelay.Find(), 'ambiguous renderer must fail closed')
table.remove(UIParent.children) -- Remove the deliberately ambiguous fixture.
view.proxy.protected = true
assert(not toolkit.OPieDelay.Find(), 'unexpected protected visual frame must fail closed')
view.proxy.protected = false
assert(toolkit.OPieDelay.Find())
-- Exercise the actual Core, Options and feature settings against this proven gate.
assert(loadfile(toolkitSource .. '/Core.lua'))('PhoenixWoWToolkit', toolkit)
local events = frames[#frames]
assert(loadfile(toolkitSource .. '/Options.lua'))('PhoenixWoWToolkit', toolkit)
assert(loadfile(toolkitSource .. '/features/opie-visual-delay/Feature.lua'))('PhoenixWoWToolkit', toolkit)
local feature = toolkit.features[1]
feature.gate = gate -- Reuse the already hooked renderer, don't attach a second observer.
local version = '8.10.2'
C_AddOns = { IsAddOnLoaded = function() return true end, GetAddOnMetadata = function() return version end }
SlashCmdList = {}
Settings = { RegisterCanvasLayoutCategory = function() return {} end, RegisterAddOnCategory = noop }
PhoenixWoWToolkitDB = nil
events.scripts.OnEvent(events, 'ADDON_LOADED', 'PhoenixWoWToolkit')
assert(feature.settings.enabled and feature.settings.delayMs == 50)
feature.slider:SetValue(73)
assert(feature.settings.delayMs == 73 and feature.input:GetText() == '73')
feature.input:SetText('18'); feature.input.scripts.OnEnterPressed(feature.input)
assert(feature.settings.delayMs == 18 and feature.slider.value == 18)
feature.input:SetText('999'); feature.input.scripts.OnEditFocusLost(feature.input)
assert(feature.settings.delayMs == 250)
feature.slider:SetValue(-4); assert(feature.settings.delayMs == 0)
feature.slider:SetValue(50.4); assert(feature.settings.delayMs == 50)
feature.input:SetText('9'); feature.input.scripts.OnEscapePressed(feature.input)
assert(feature.settings.delayMs == 50 and feature.input:GetText() == '50')
notify('open'); invisible()
feature.checkbox:SetChecked(false); feature.checkbox.scripts.OnClick(feature.checkbox)
assert(not gate.enabled and not gate.hidden and feature.settings.enabled == false)
feature.checkbox:SetChecked(true); feature.checkbox.scripts.OnClick(feature.checkbox)
notify('close'); notify('open'); invisible()
version = '8.11'
events.scripts.OnEvent(events, 'ADDON_LOADED', 'OPie')
feature:RefreshSettings()
assert(not feature.available and not gate.enabled and not gate.hidden and not feature.checkbox.enabled)
assert(PhoenixWoWToolkitDB.features.opieVisualDelay.delayMs == 50)
GetBuildInfo = function() return '12.2', '', '', 120200 end
assert(not feature:GetAvailability({ opieLoaded = true, opieVersion = '8.10.2' }))
print('Actual OPie 8.10.2 renderer + notification: tap/hold/flick updates, stale timers, nested switches, animations, tooltip ownership, disable and 0/250 ms passed')
print('Settings, numeric validation, version/client gating and missing/ambiguous/protected structure checks passed')
print('NOT TESTED: actual protected-action execution, GPU frame presentation, combat lockdown or taint in WoW')
