local root = assert(arg[1])
local T = { RegisterFeature = function(self, feature) self.feature = feature end }
Enum = { TooltipComparisonMethod = { Single = 0, WithBothHands = 1, WithBagMainHandItem = 2, WithBagOffHandItem = 3 }, TooltipDataType = { Item = 0 } }
issecretvalue = function(value) return value == 'secret' end
canaccessallvalues = function(value) return not value.secret end
local info, deltaCalls, inventory = nil, {}, nil
C_Item = {
    GetItemLinkByGUID = function(guid) return guid end,
    GetDetailedItemLevelInfo = function(link) return link == 'candidate' and 100 or 80 end,
    IsEquippableItem = function(link) return link ~= 'junk' end,
    GetItemInfoInstant = function(link) return link end,
    IsDressableItemByID = function(id) return id ~= 'ring' end,
}
GetInventoryItemLink = function() return inventory end
C_TooltipComparison = {
    GetItemComparisonInfo = function() return info end,
    GetItemComparisonDelta = function(a, b, c, paired)
        deltaCalls[#deltaCalls + 1] = { a, b, c, paired }
        return { '|cff20ff20+38 Stamina|r', '|cffff4040-51 Critical Strike|r' }
    end,
}
assert(loadfile(root .. '/features/universal-item-tooltips/Comparison.lua'))('PhoenixWoWToolkit', T)
local data = { hyperlink = 'candidate' }
info = { method = 0, item = { hyperlink = 'equipped' }, additionalItems = {} }
local groups = T.ItemComparison.Groups(data)
assert(#groups == 1 and #groups[1].rows == 3 and groups[1].rows[2]:find('+38 Stamina', 1, true))
info.additionalItems = { { hyperlink = 'other-ring' } }
assert(#T.ItemComparison.Groups(data) == 2, 'ring/trinket alternatives must not be guessed')
info.additionalItems = { { hyperlink = 'equipped' } }
assert(#T.ItemComparison.Groups(data) == 1, 'identical alternatives must not duplicate the summary')
info.additionalItems = { { hyperlink = 'other-ring' } }
info.method = 1; groups = T.ItemComparison.Groups(data)
assert(#groups == 1 and groups[1].partner == 'other-ring' and deltaCalls[#deltaCalls][4] == false)
info.method = 2; groups = T.ItemComparison.Groups(data)
assert(groups[1].paired and deltaCalls[#deltaCalls][4] == true, 'paired bag weapon stats must be additive')
inventory = 'candidate'; assert(#T.ItemComparison.Groups(data) == 0, 'equipped-item self comparison')
inventory = nil
assert(#T.ItemComparison.Groups({ hyperlink = 'secret' }) == 0)
info = nil; assert(#T.ItemComparison.Groups(data) == 0, 'uncached comparison fallback')
info = { method = 99, item = { hyperlink = 'equipped' }, additionalItems = {} }
assert(#T.ItemComparison.Groups(data) == 0, 'unknown native method fallback')
local callbacks, combat, created = {}, false, {}
STANDARD_TEXT_FONT = 'Fonts/FRIZQT__.TTF'
C_TransmogCollection = {
    GetItemInfo = function() return 42, 84 end,
    GetAppearanceCameraIDBySource = function(source) assert(source == 84); return 100 end,
}
local appliedCameras = 0
Model_ApplyUICamera = function(model, camera) model.camera = camera; appliedCameras = appliedCameras + 1 end
InCombatLockdown = function() return combat end
GetScreenHeight = function() return 1080 end
TooltipDataProcessor = { AddTooltipPostCall = function(_, callback) callbacks[#callbacks + 1] = callback end }
local function frame()
    local f = { scripts = {}, shown = true, alpha = 1 }
    function f:SetScript(event, fn) self.scripts[event] = fn end
    function f:Show() self.shown = true end
    function f:Hide() self.shown = false end
    function f:SetUnit(unit) self.unit = unit end
    function f:SetAlpha(alpha) self.alpha = alpha end
    function f:SetUseTransmogSkin(enabled) self.masked = enabled end
    function f:SetItemAppearance(appearance) self.appearance = appearance end
    function f:GetModelFileID() return 0 end
    function f:SetTexture() end
    function f:SetVertexColor() end
    function f:SetAllPoints() end
    function f:SetWidth(width) self.width = width end
    function f:SetChecked(checked) self.checked = checked end
    function f:SetEnabled(enabled) self.enabled = enabled end
    function f:SetupMenu(generator) self.generate = generator end
    function f:OverrideText(text) self.label = text end
    function f:TryOn(link) self.item = link; self.tryCount = (self.tryCount or 0) + 1 end
    for _, name in ipairs({ 'SetSize', 'SetPoint', 'ClearAllPoints', 'SetClampedToScreen', 'EnableMouse', 'SetBackdrop', 'SetBackdropColor', 'SetAutoDress', 'Undress', 'SetFacing' }) do f[name] = function() end end
    created[#created + 1] = f
    return f
end
CreateFrame = frame
assert(loadfile(root .. '/features/universal-item-tooltips/Preview.lua'))('PhoenixWoWToolkit', T)
assert(loadfile(root .. '/features/universal-item-tooltips/Presentation.lua'))('PhoenixWoWToolkit', T)
assert(loadfile(root .. '/features/universal-item-tooltips/Feature.lua'))('PhoenixWoWToolkit', T)
local feature = T.feature
assert(feature.defaults.enabled and feature:GetAvailability())
feature.settings = { enabled = true, appearance = 'dialogue' }
feature:Enable(); assert(#callbacks == 1)
info = { method = 0, item = { hyperlink = 'equipped' }, additionalItems = {} }
local tooltip = { lines = { 'Original stats', 'Other add-on annotation' }, hooks = {}, padding = { 3, 4, 5, 6 } }
function tooltip:GetPadding() return table.unpack(self.padding) end
function tooltip:SetPadding(...) self.padding = { ... } end
function tooltip:CreateTexture() return frame() end
local titleFont = { file = 'ElvUI.ttf', size = 12, flags = 'OUTLINE' }
function titleFont:GetFont() return self.file, self.size, self.flags end
function titleFont:SetFont(file, size, flags) self.file, self.size, self.flags = file, size, flags end
function tooltip:GetLeftLine(index) if index == 1 then return titleFont end end
function tooltip:GetRightLine() end
function tooltip:NumLines() return #self.lines end
function tooltip:IsForbidden() return self.forbidden or false end
function tooltip:IsProtected() return false end
function tooltip:IsShown() return true end
function tooltip:GetTop() return self.top or 600 end
function tooltip:GetBottom() return self.bottom or 300 end
function tooltip:HookScript(event, fn) self.hooks[event] = fn end
function tooltip:AddLine(line) self.lines[#self.lines + 1] = line end
function tooltip:RebuildFromTooltipInfo()
    self.lines = { 'Original stats', 'Other add-on annotation' }
    self.hooks.OnTooltipCleared()
    for _, callback in ipairs(callbacks) do callback(self, data) end
end
callbacks[1](tooltip, data)
assert(tooltip.lines[1] == 'Original stats' and tooltip.lines[2] == 'Other add-on annotation')
assert(#tooltip.lines == 7 and titleFont.file == STANDARD_TEXT_FONT and titleFont.size == 16)
local state = feature.states[tooltip]
assert(state.preview == state.model and state.model.item == 'candidate', 'preview is an embedded transparent model, never a bordered floating panel')
assert(state.model.masked and state.model.alpha == 0, 'no blank panel or naked player while model loads')
assert(tooltip.padding[1] > 3, 'reserve space beside the original item text')
state.model.scripts.OnModelLoaded()
assert(state.model.alpha == 1 and state.model.camera == 100 and appliedCameras > 0, 'apply the appearance camera after asynchronous load')
callbacks[1](tooltip, data); assert(#tooltip.lines == 7, 'duplicate section')
state.model.scripts.OnModelLoaded(); assert(state.model.item == 'candidate')
tooltip.hooks.OnHide(); local tries = state.model.tryCount
state.model.scripts.OnModelLoaded(); assert(state.model.tryCount == tries and not state.preview.shown, 'stale preview callback')
tooltip:RebuildFromTooltipInfo(); feature:Disable()
assert(#tooltip.lines == 2 and not state.preview.shown and tooltip.padding[1] == 3 and tooltip.padding[4] == 6, 'toggle must restore native tooltip, padding and annotations')
feature:Enable(); assert(#callbacks == 1 and #tooltip.lines == 7, 'no duplicate processor on re-enable')
tooltip.CompareHeader = {}; tooltip.lines = {}; callbacks[1](tooltip, data); assert(#tooltip.lines == 0)
tooltip.CompareHeader, tooltip.forbidden = nil, true; callbacks[1](tooltip, data); assert(#tooltip.lines == 0)
tooltip.CompareHeader, tooltip.forbidden = nil, false
feature:SetAppearance('native')
assert(#tooltip.lines == 7 and not state.preview.shown and tooltip.padding[1] == 3 and titleFont.file == 'ElvUI.ttf' and titleFont.flags == 'OUTLINE', 'current UI restores fonts and keeps summaries without styling or model')
feature:SetAppearance('invalid'); assert(feature.settings.appearance == 'native')
feature:SetAppearance('dialogue')
assert(state.preview.shown and tooltip.padding[1] > 3)
C_TransmogCollection.GetAppearanceCameraIDBySource = function() return 0 end
tooltip:RebuildFromTooltipInfo()
assert(not state.preview.shown and tooltip.padding[1] == 3, 'unsupported camera leaves no empty frame or reserved column')
-- Exercise the actual native-dropdown callbacks, not a parallel settings setter.
T.Options = { Text = function() end, Checkbox = function() return frame() end }
feature.available = true
feature:RegisterSettings({}, 0); feature:RefreshSettings()
local choices = {}
feature.dropdown.generate(nil, { CreateRadio = function(_, label, selected, choose, value)
    choices[value] = { selected = selected, choose = choose, label = label }
end })
assert(choices.dialogue.selected('dialogue') and not choices.native.selected('native'))
choices.native.choose('native')
assert(feature.settings.appearance == 'native' and feature.dropdown.label == choices.native.label)
feature.settings.enabled = false; feature:RefreshSettings()
assert(not feature.dropdown.enabled, 'disabled feature has a disabled approach selector')
combat = true; feature:Disable() -- No native rebuild/secure anchor calls in combat.
print('Item tooltips: native comparisons, rings/paired weapons, fallbacks, annotations, preview lifecycle and independent toggle passed')
print('NOT TESTED: real model rendering, window coverage, combat taint or visual layout in WoW')
