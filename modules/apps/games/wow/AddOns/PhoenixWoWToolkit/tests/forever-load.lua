-- Load the actual Forever manifest and initialize Settings with absent optional APIs.
local root = assert(arg[1])
local frames = {}
local object
local function noop() end
local methods = {
    SetScript = function(self, event, fn) self.scripts[event] = fn end,
    CreateFontString = function() return object() end,
    CreateTexture = function() return object() end,
    GetID = function() return 42 end,
}
function object()
    local value = setmetatable({scripts = {}}, {__index = function(_, key)
        if key == 'Low' or key == 'High' then return nil end
        return methods[key] or noop
    end})
    value.Text = setmetatable({}, {__index = function() return noop end})
    return value
end
CreateFrame = function()
    local value = object()
    frames[#frames + 1] = value
    return value
end
PanelTemplates_SelectTab, PanelTemplates_DeselectTab, PanelTemplates_TabResize = noop, noop, noop
Settings = {
    RegisterCanvasLayoutCategory = function(panel) return {GetID = function() return 42 end, panel = panel} end,
    RegisterAddOnCategory = noop, OpenToCategory = noop,
}
SlashCmdList = {}
InCombatLockdown = function() return false end
C_AddOns = {IsAddOnLoaded = function() return false end, GetAddOnMetadata = function() return nil end}
UnitClass = function() return 'Druid', 'DRUID' end
WOW_PROJECT_ID, WOW_PROJECT_CAMELOT = 11, 11
local toolkit = {}
for line in io.lines(root .. '/PhoenixWoWToolkit_Camelot.toc') do
    if line ~= '' and line:sub(1, 1) ~= '#' then
        assert(loadfile(root .. '/' .. line))('PhoenixWoWToolkit', toolkit)
    end
end
frames[1].scripts.OnEvent(frames[1], 'ADDON_LOADED', 'PhoenixWoWToolkit')
assert(toolkit.initialized)
assert(toolkit.byID.objectiveTracker and toolkit.byID.objectiveTracker.active)
assert(toolkit.byID.opieVisualDelay and not toolkit.byID.opieVisualDelay.active)
assert(toolkit.byID.opieVisualDelay.settings.enabled == false)
assert(toolkit.byID.universalItemTooltips and toolkit.byID.comparisonCleanup)
assert(toolkit.byID.elvuiHoldToCast)
assert(toolkit.byID.wowProButtonBar and not toolkit.byID.wowProButtonBar.active)
assert(toolkit.byID.combatTracking and not toolkit.byID.combatTracking.active)
assert(toolkit.byID.combatTracking.settings.enabled == false)
assert(toolkit.byID.combatTracking.enableCheckbox)
assert(toolkit.byID.objectiveTracker.globalCheckbox)
assert(toolkit.byID.universalItemTooltips.checkbox)
assert(toolkit.selectedOptionsTab == 'General')
assert(SLASH_PHOENIXWOWTOOLKIT1 == '/pwt')
print('Forever manifest: all feature files load and General/Tooltip/Combat settings initialize')
