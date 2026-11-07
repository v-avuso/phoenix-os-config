PanelTemplates_SelectTab = function(tab) tab:SetEnabled(false) end
PanelTemplates_DeselectTab = function(tab) tab:SetEnabled(true) end
PanelTemplates_TabResize = function() end
local source = assert(arg[1])
local frames = {}
local function frame()
    local f = { scripts = {}, labels = {} }
    function f:RegisterEvent() end
    function f:SetScript(event, fn) self.scripts[event] = fn end
    function f:SetPoint() end
    function f:SetSize() end
    function f:SetHeight() end
    function f:SetShown(value) self.hidden=not value end
    function f:SetEnabled(value) self.enabled=value end
    function f:SetText(value) self.text=value end
    function f:SetVerticalScroll() end
    function f:SetScrollChild(child) self.child = child end
    function f:Hide() self.hidden = true end
    function f:CreateFontString()
        local l = {}
        function l:SetPoint() end
        function l:SetJustifyH() end
        function l:SetText(text) self.text = text end
        self.labels[#self.labels + 1] = l
        return l
    end
    frames[#frames + 1] = f
    return f
end
CreateFrame = frame
local category = { GetID = function() return 42 end }
Settings = {
    RegisterCanvasLayoutCategory = function(panel) category.panel = panel; return category end,
    RegisterAddOnCategory = function() end,
    OpenToCategory = function(id) assert(id == 42) end,
}
SlashCmdList = {}
local toolkit = {}
assert(loadfile(source .. '/Core.lua'))('PhoenixWoWToolkit', toolkit)
assert(loadfile(source .. '/Options.lua'))('PhoenixWoWToolkit', toolkit)
local function feature(id, section)
    local f = { id = id, section = section, defaults = { enabled = true }, starts = 0, stops = 0 }
    function f:GetAvailability() return true end
    function f:Enable() self.starts = self.starts + 1 end
    function f:Disable() self.stops = self.stops + 1 end
    function f:RegisterSettings(_, y) return y - 40 end
    function f:RefreshSettings() end
    return toolkit:RegisterFeature(f)
end
local a = feature('a', 'Shared section')
PhoenixWoWToolkitDB = { features = { a = { enabled = false }, unrelated = { value = 7 } } }
frames[1].scripts.OnEvent(frames[1], 'ADDON_LOADED', 'PhoenixWoWToolkit')
assert(not a.active and PhoenixWoWToolkitDB.features.unrelated.value == 7)
assert(PhoenixWoWToolkit == toolkit and toolkit.apiVersion == 1)
local c = feature('c', 'Tooltips'); c.optionsTab='Tooltip'
local b = feature('b', 'Shared section') -- External registration after core initialization.
assert(b.active and b.starts == 1 and toolkit.optionsDirty)
category.panel.OnRefresh()
local sectionCount = 0
for _, label in ipairs(toolkit.content.labels) do if label.text == 'Shared section' then sectionCount = sectionCount + 1 end end
assert(sectionCount == 1, 'Contributors to one section must share a heading')
assert(toolkit.contents.Tooltip.hidden and not toolkit.content.hidden)
toolkit.tabButtons.Tooltip.scripts.OnClick()
assert(toolkit.content==toolkit.contents.Tooltip and toolkit.contents.General.hidden)
assert(toolkit.content.labels[1].text=='Tooltips','tooltip features have their own page')
toolkit.tabButtons.General.scripts.OnClick()
assert(toolkit.content==toolkit.contents.General)
local combatFeature=feature('combat','Combat Tracking'); combatFeature.optionsTab='Combat'
category.panel.OnRefresh()
toolkit.tabButtons.Combat.scripts.OnClick()
assert(toolkit.content==toolkit.contents.Combat and toolkit.contents.General.hidden)
assert(toolkit.content.labels[1].text=='Combat Tracking')
a.settings.enabled = true; toolkit:RefreshFeatures()
b.settings.enabled = false; toolkit:RefreshFeatures()
assert(a.active and not b.active and a.starts == 1 and b.stops == 1)
assert(not pcall(function() feature('a', 'Duplicate') end))
assert(SLASH_PHOENIXWOWTOOLKIT1 == '/pwt'); SlashCmdList.PHOENIXWOWTOOLKIT()
print('Core: saved preferences, late external registration, shared sections, independent toggles and /pwt passed')
