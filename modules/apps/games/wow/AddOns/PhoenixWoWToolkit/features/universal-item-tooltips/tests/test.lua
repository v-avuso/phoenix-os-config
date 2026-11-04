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
InCombatLockdown = function() return combat end
GetScreenHeight = function() return 1080 end
TooltipDataProcessor = { AddTooltipPostCall = function(_, callback) callbacks[#callbacks + 1] = callback end }
local function frame()
    local f = { scripts = {}, shown = true }
    function f:SetScript(event, fn) self.scripts[event] = fn end
    function f:Show() self.shown = true end
    function f:Hide() self.shown = false end
    function f:SetUnit(unit) self.unit = unit end
    function f:TryOn(link) self.item = link; self.tryCount = (self.tryCount or 0) + 1 end
    for _, name in ipairs({ 'SetSize', 'SetPoint', 'ClearAllPoints', 'SetClampedToScreen', 'EnableMouse', 'SetBackdrop', 'SetBackdropColor', 'SetAutoDress', 'Undress', 'SetFacing' }) do f[name] = function() end end
    created[#created + 1] = f
    return f
end
CreateFrame = frame
assert(loadfile(root .. '/features/universal-item-tooltips/Preview.lua'))('PhoenixWoWToolkit', T)
assert(loadfile(root .. '/features/universal-item-tooltips/Feature.lua'))('PhoenixWoWToolkit', T)
local feature = T.feature
assert(feature.defaults.enabled and feature:GetAvailability())
feature:Enable(); assert(#callbacks == 1)
info = { method = 0, item = { hyperlink = 'equipped' }, additionalItems = {} }
local tooltip = { lines = { 'Original stats', 'Other add-on annotation' }, hooks = {} }
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
assert(#tooltip.lines == 7)
local state = feature.states[tooltip]
assert(state.preview.shown and state.model.item == 'candidate')
tooltip.top, tooltip.bottom = 1000, 100
T.ItemPreview.Place(state, tooltip); assert(not state.preview.shown, 'never overlap item/comparison text when no space fits')
tooltip.top, tooltip.bottom = 600, 300
T.ItemPreview.Place(state, tooltip); assert(state.preview.shown)
callbacks[1](tooltip, data); assert(#tooltip.lines == 7, 'duplicate section')
state.model.scripts.OnModelLoaded(); assert(state.model.item == 'candidate')
tooltip.hooks.OnHide(); local tries = state.model.tryCount
state.model.scripts.OnModelLoaded(); assert(state.model.tryCount == tries and not state.preview.shown, 'stale preview callback')
tooltip:RebuildFromTooltipInfo(); feature:Disable()
assert(#tooltip.lines == 2 and not state.preview.shown, 'toggle must restore native tooltip and annotations')
feature:Enable(); assert(#callbacks == 1 and #tooltip.lines == 7, 'no duplicate processor on re-enable')
tooltip.CompareHeader = {}; tooltip.lines = {}; callbacks[1](tooltip, data); assert(#tooltip.lines == 0)
tooltip.CompareHeader, tooltip.forbidden = nil, true; callbacks[1](tooltip, data); assert(#tooltip.lines == 0)
combat = true; feature:Disable() -- No native rebuild/secure anchor calls in combat.
print('Item tooltips: native comparisons, rings/paired weapons, fallbacks, annotations, preview lifecycle and independent toggle passed')
print('NOT TESTED: real model rendering, window coverage, combat taint or visual layout in WoW')
