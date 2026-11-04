-- Behavioral fixture, not a WoW renderer/taint emulator.
local source = assert(arg[1])
local frames, combat = {}, false
function InCombatLockdown() return combat end
function hooksecurefunc(object, method, callback)
    local original = assert(object[method], method)
    object[method] = function(self, ...)
        original(self, ...)
        callback(self, ...)
    end
end
local function object(parent)
    local value = { shown = true, alpha = 1, parent = parent, scripts = {}, protected = false }
    function value:IsProtected() return self.protected or (self.parent and self.parent:IsProtected()) or false end
    function value:GetParent() return self.parent end
    function value:IsShown() return self.shown end
    function value:GetAlpha() return self.alpha end
    function value:CheckMutation() assert(not (combat and self:IsProtected()), 'protected mutation in combat') end
    function value:Show() self:CheckMutation(); self.shown = true end
    function value:Hide() self:CheckMutation(); self.shown = false end
    function value:SetShown(shown) self:CheckMutation(); self.shown = shown end
    function value:SetAlpha(alpha) self:CheckMutation(); self.alpha = alpha end
    function value:SetScript(event, callback) self.scripts[event] = callback end
    function value:HookScript(event, callback)
        local original = self.scripts[event]
        self.scripts[event] = function(...)
            if original then original(...) end
            callback(...)
        end
    end
    function value:RegisterEvent(event) self.events = self.events or {}; self.events[event] = true end
    function value:SetPoint() end
    function value:SetJustifyH() end
    function value:SetText(text) self.text = text end
    function value:SetWordWrap() end
    function value:SetEnabled(enabled) self.enabled = enabled end
    function value:SetSize() end
    function value:SetHeight() end
    function value:SetScrollChild() end
    function value:SetMinMaxValues() end
    function value:SetValueStep() end
    function value:SetObeyStepOnDrag() end
    function value:SetAutoFocus() end
    function value:SetNumeric() end
    function value:SetMaxLetters() end
    function value:SetValue(v) self.value = v end
    function value:SetChecked(checked) self.checked = checked end
    function value:GetChecked() return self.checked end
    function value:CreateFontString() return object(self) end
    function value:Click()
        if self.shown and self.scripts.OnClick then self.scripts.OnClick(self) end
    end
    return value
end
function CreateFrame(_, _, parent, template)
    local frame = object(parent)
    if template == 'UICheckButtonTemplate' then frame.Text = object(frame) end
    frames[#frames + 1] = frame
    return frame
end
local function header(parent)
    local h = object(parent)
    h.Text, h.Background, h.MinimizeButton = object(h), object(h), object(h)
    h.MinimizeButton:SetScript('OnClick', function() parent.collapsed = not parent.collapsed end)
    return h
end
local function module()
    local m = object()
    m.Header = header(m)
    return m
end
local function tracker()
    local t = object()
    t.Header, t.modules, t.topModulePadding = header(t), {}, 38
    function t:ForEachModule(callback) for _, m in ipairs(self.modules) do callback(m) end end
    function t:Update()
        self.Header:Show()
        self.Header.Text:Show()
        self.Header.Background:SetShown(true)
        self.Header.MinimizeButton:Show()
    end
    function t:AddModule(m) self.modules[#self.modules + 1] = m end
    return t
end
C_AddOns = { IsAddOnLoaded = function() return false end, GetAddOnMetadata = function() end }
SlashCmdList = {}
Settings = { RegisterCanvasLayoutCategory = function() return {} end, RegisterAddOnCategory = function() end }
local function emit(event, name)
    -- Snapshot: callbacks may create another event frame.
    local count = #frames
    for i = 1, count do
        local f = frames[i]
        if f.events and f.events[event] and f.scripts.OnEvent then f.scripts.OnEvent(f, event, name) end
    end
end
local toolkit = {}
for line in io.lines(source .. '/PhoenixWoWToolkit.toc') do
    if line:match('%.lua$') then assert(loadfile(source .. '/' .. line))('PhoenixWoWToolkit', toolkit) end
end
PhoenixWoWToolkitDB = { features = { unrelated = { preserved = true } } }
emit('ADDON_LOADED', 'PhoenixWoWToolkit') -- Tracker not loaded yet.
local feature
for _, f in ipairs(toolkit.features) do if f.id == 'objectiveTracker' then feature = f end end
assert(feature, 'Objective Tracker feature must be registered')
assert(feature.settings.hideGlobalHeader and feature.settings.hideSectionMinimizeButtons, 'default-on independent options')
ObjectiveTrackerFrame = tracker()
local cachedUpdate = ObjectiveTrackerFrame.Update -- Blizzard's dirty closure captures this before hooks.
local campaign, quests = module(), module()
quests.Header.MinimizeButton.alpha = .45 -- Preserve a skin's non-default alpha.
local skinnedButton = quests.Header.MinimizeButton
local custom = { Header = { Text = object() } } -- No minimize button.
ObjectiveTrackerFrame:AddModule(campaign)
ObjectiveTrackerFrame:AddModule(quests)
ObjectiveTrackerFrame:AddModule(custom)
emit('ADDON_LOADED', 'Blizzard_ObjectiveTracker')
local function checkHidden(t)
    assert(not t.Header.Text:IsShown() and not t.Header.Background:IsShown())
    assert(not t.Header.MinimizeButton:IsShown(), 'global minimize must have no hotspot')
    assert(t.Header:IsShown() and t.topModulePadding == 38, 'preserve layout')
end
checkHidden(ObjectiveTrackerFrame)
assert(campaign.Header.Text:IsShown() and campaign.Header.Background:IsShown())
local button = campaign.Header.MinimizeButton
assert(button:IsShown() and button:GetAlpha() == 0)
button:Click(); assert(campaign.collapsed)
button:Click(); assert(not campaign.collapsed)
button:SetAlpha(.7); assert(button:GetAlpha() == 0, 'skin refresh must remain invisible')
ObjectiveTrackerFrame:Update(); checkHidden(ObjectiveTrackerFrame)
quests.Header.MinimizeButton = object(quests.Header)
cachedUpdate(ObjectiveTrackerFrame)
assert(quests.Header.MinimizeButton:GetAlpha() == 0, 'cached Blizzard updates must discover new controls')
emit('PLAYER_ENTERING_WORLD'); checkHidden(ObjectiveTrackerFrame)
-- Use the real Settings callbacks: persistence and immediate, independent application.
local function toggle(label, value)
    for _, f in ipairs(frames) do
        if f.Text and f.Text.text == label then
            f:SetChecked(value); f.scripts.OnClick(f); return
        end
    end
    error('Missing checkbox: ' .. label)
end
toggle('Hide Objective Tracker Global Header', false)
assert(ObjectiveTrackerFrame.Header.Text:IsShown() and ObjectiveTrackerFrame.Header.Background:IsShown())
assert(ObjectiveTrackerFrame.Header.MinimizeButton:IsShown())
assert(button:GetAlpha() == 0, 'section setting independent of global setting')
toggle('Hide Section Minimize Buttons', false)
assert(button:GetAlpha() == .7 and quests.Header.MinimizeButton:GetAlpha() == 1, 'restore latest external alpha')
assert(skinnedButton:GetAlpha() == .45, 'restore detached skinned controls too')
toggle('Hide Objective Tracker Global Header', true)
assert(button:GetAlpha() == .7, 'global option must not suppress sections')
toggle('Hide Section Minimize Buttons', true)
-- Replacement header / new module discovered by container update/add, no polling.
ObjectiveTrackerFrame.Header = header(ObjectiveTrackerFrame)
ObjectiveTrackerFrame:Update(); checkHidden(ObjectiveTrackerFrame)
local fresh = module(); ObjectiveTrackerFrame:AddModule(fresh)
assert(fresh.Header.MinimizeButton:GetAlpha() == 0)
fresh.Header.MinimizeButton = object(fresh.Header)
ObjectiveTrackerFrame:Update()
assert(fresh.Header.MinimizeButton:GetAlpha() == 0)
-- External visibility intent while suppressed is preserved on disable.
ObjectiveTrackerFrame.Header.Background:Hide()
toggle('Hide Objective Tracker Global Header', false)
assert(not ObjectiveTrackerFrame.Header.Background:IsShown())
-- Protected frames are untouched in combat, then reconciled after combat.
toggle('Hide Objective Tracker Global Header', true)
ObjectiveTrackerFrame.protected = true
button.protected = true
combat = true
toggle('Hide Objective Tracker Global Header', false)
toggle('Hide Section Minimize Buttons', false)
assert(not ObjectiveTrackerFrame.Header.Text:IsShown() and button:GetAlpha() == 0)
combat = false
emit('PLAYER_REGEN_ENABLED')
assert(ObjectiveTrackerFrame.Header.Text:IsShown() and button:GetAlpha() == .7)
ObjectiveTrackerFrame.protected, button.protected = false, false
-- Legacy tables, optional/missing controls, and replacement tracker discovery.
local legacy = tracker(); legacy.ForEachModule, legacy.modules = nil, nil
legacy.MODULES = { module(), { Header = {} } }
ObjectiveTrackerFrame = legacy
toggle('Hide Objective Tracker Global Header', true)
toggle('Hide Section Minimize Buttons', true)
emit('PLAYER_ENTERING_WORLD')
checkHidden(legacy)
assert(legacy.MODULES[1].Header.MinimizeButton:GetAlpha() == 0)
-- Whole-module disable restores owned values; callbacks become inert.
feature.settings.enabled = false; toolkit:RefreshFeatures()
assert(legacy.Header.Text:IsShown() and legacy.MODULES[1].Header.MinimizeButton:GetAlpha() == 1)
legacy:Update(); assert(legacy.Header.Text:IsShown())
assert(PhoenixWoWToolkitDB.features.unrelated.preserved)
assert(PhoenixWoWToolkit == toolkit, 'public core registration remains available')
-- A fresh runtime must retain both independently saved false values.
toggle('Hide Objective Tracker Global Header', false)
toggle('Hide Section Minimize Buttons', false)
local saved = PhoenixWoWToolkitDB
frames, toolkit, ObjectiveTrackerFrame = {}, {}, tracker()
for line in io.lines(source .. '/PhoenixWoWToolkit.toc') do
    if line:match('%.lua$') then assert(loadfile(source .. '/' .. line))('PhoenixWoWToolkit', toolkit) end
end
PhoenixWoWToolkitDB = saved
emit('ADDON_LOADED', 'PhoenixWoWToolkit')
assert(not saved.features.objectiveTracker.hideGlobalHeader and not saved.features.objectiveTracker.hideSectionMinimizeButtons)
assert(ObjectiveTrackerFrame.Header.Text:IsShown())
print('Objective Tracker visibility, click, restoration, refresh, combat-deferral and persistence fixtures passed')
