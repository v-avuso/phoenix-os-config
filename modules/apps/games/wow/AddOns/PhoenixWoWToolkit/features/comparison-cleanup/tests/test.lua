local root, nativeSource = assert(arg[1]), arg[2]
local function noop() end
issecretvalue = function(value) return value == 'secret' end
canaccessallvalues = function(value) return type(value) ~= 'table' or not value.secret end
Enum = { TooltipComparisonMethod = { Single = 0, WithBothHands = 1, WithBagMainHandItem = 2, WithBagOffHandItem = 3 }, TooltipDataType = { Item = 0 } }
ITEM_DELTA_DESCRIPTION, ITEM_DELTA_MULTIPLE_COMPARISON_DESCRIPTION = 'Native single comparison', 'Native combined comparison'
EQUIPPED, IF_EQUIPPED_TOGETHER = 'Equipped', 'If equipped together'
RegisterEventCallback = noop
GetCVarBool = function() return true end
local delta = { '+38 Stamina', '-51 Critical Strike' }
local postCalls, staleRight = {}, false
TooltipDataProcessor = { AddTooltipPostCall = function(_, callback) postCalls[#postCalls + 1] = callback end }
C_TooltipComparison = { GetItemComparisonDelta = function() return delta end }
C_TooltipInfo = { GetHyperlink = function() return { lines = { 'Original equipped stats', 'Other add-on annotation' } } end }
local function font(text)
    return { text = text, shown = true, GetText = function(self) return self.text end,
        IsShown = function(self) return self.shown end, Hide = function(self) self.shown = false end,
        SetShown = function(self, shown) self.shown = shown end }
end
local function tooltip(name)
    local t = { name = name, hooks = {}, lines = {}, w = 300, h = 16 }
    function t:GetName() return self.name end
    function t:IsForbidden() return false end
    function t:IsProtected() return false end
    function t:GetSize() return self.w, self.h end
    function t:SetSize(w, h)
        local changed = self.w ~= w or self.h ~= h
        self.w, self.h = w, h
        if changed and self.hooks.OnSizeChanged then self.hooks.OnSizeChanged() end
    end
    function t:NumLines() return #self.lines end
    function t:AddLine(text)
        self.lines[#self.lines + 1] = text
        _G[name .. 'TextLeft' .. #self.lines] = font(text)
        _G[name .. 'TextRight' .. #self.lines] = font(staleRight and 'old hidden value' or '')
        if staleRight then _G[name .. 'TextRight' .. #self.lines]:SetShown(false) end
        self:SetSize(300, 16 + #self.lines * 20)
    end
    function t:ClearLines() self.lines = {}; if self.hooks.OnTooltipCleared then self.hooks.OnTooltipCleared() end end
    function t:Show()
        self:SetSize(300, 16 + #self.lines * 20)
        -- A layout refresh need not change dimensions or fire OnShow again.
        for i = 1, #self.lines do _G[name .. 'TextLeft' .. i]:SetShown(true) end
        if not self.shown and self.hooks.OnShow then self.hooks.OnShow() end
        self.shown = true
    end
    function t:HookScript(event, fn) self.hooks[event] = fn end
    function t:ProcessInfo(info)
        for _, line in ipairs(info.tooltipData.lines) do self:AddLine(line) end
        for _, callback in ipairs(postCalls) do callback(self, info.tooltipData) end
        self:Show()
    end
    t.SetOwner, t.ClearAllPoints = noop, noop
    t.IsShown = function() return true end
    t.CompareHeader = { Show = noop, SetWidth = noop, Label = { SetText = noop, GetWidth = function() return 30 end } }
    return t
end
ShoppingTooltip1, ShoppingTooltip2 = tooltip('PWTTestShopping1'), tooltip('PWTTestShopping2')
function GameTooltip_AddBlankLineToTooltip(t) t:AddLine(' ') end
function GameTooltip_AddNormalLine(t, line) t:AddLine(line) end
GameTooltip_AddHighlightLine = GameTooltip_AddNormalLine
if nativeSource then
    assert(loadfile(nativeSource))() -- Original Blizzard method, not a vendored copy.
else
    TooltipComparisonManager = { Initialize = function() end, SetItemTooltip = function() end }
end
local manager = TooltipComparisonManager
local owner = { shoppingTooltips = { ShoppingTooltip1, ShoppingTooltip2 } }
manager.tooltip, manager.compareInfo, manager.comparisonItem, manager.comparisonIndex = owner,
    { method = 0, item = { hyperlink = 'equipped' }, additionalItems = {} }, { hyperlink = 'candidate' }, 1
if not nativeSource then
    function manager:SetItemTooltip()
        local t = self.tooltip.shoppingTooltips[1]
        t:ClearLines(); t:ProcessInfo({ tooltipData = C_TooltipInfo.GetHyperlink() })
        GameTooltip_AddBlankLineToTooltip(t); GameTooltip_AddNormalLine(t, ITEM_DELTA_DESCRIPTION)
        for _, line in ipairs(delta) do GameTooltip_AddHighlightLine(t, line) end
        return true
    end
end
function hooksecurefunc(object, key, callback)
    local original = object[key]
    object[key] = function(...)
        local result = table.pack(original(...)); callback(...); return table.unpack(result, 1, result.n)
    end
end
local T = { RegisterFeature = function(self, feature) self.feature = feature end }
assert(loadfile(root .. '/features/comparison-cleanup/Feature.lua'))('PhoenixWoWToolkit', T)
local feature = T.feature
assert(feature.defaults.enabled and feature:GetAvailability())
feature:Enable()
manager:SetItemTooltip(true)
assert(ShoppingTooltip1.lines[1] == 'Original equipped stats' and ShoppingTooltip1.lines[2] == 'Other add-on annotation')
assert(_G.PWTTestShopping1TextLeft1:IsShown() and _G.PWTTestShopping1TextLeft2:IsShown())
assert(not _G.PWTTestShopping1TextLeft4:IsShown() and not _G.PWTTestShopping1TextLeft6:IsShown())
assert(ShoppingTooltip1.h == 56, 'no footer-sized blank area')
ShoppingTooltip1:Show(); assert(ShoppingTooltip1.h == 56, 'native size refresh must remain trimmed')
assert(not _G.PWTTestShopping1TextLeft4:IsShown(), 'Show must not revive the footer on an already-visible tooltip')
feature:Disable()
assert(_G.PWTTestShopping1TextLeft4:IsShown() and _G.PWTTestShopping1TextLeft6:IsShown())
assert(ShoppingTooltip1.h == 136, 'disable restores native dimensions')
feature:Enable(); manager:SetItemTooltip(true); assert(ShoppingTooltip1.h == 56)
feature:Disable(); staleRight = true
feature:Enable(); manager:SetItemTooltip(true)
assert(ShoppingTooltip1.h == 56, 'hidden pooled right text must not block exact footer recognition')
staleRight = false
-- Extra annotation or altered row: leave all content intact rather than guessing.
ShoppingTooltip1:ClearLines(); ShoppingTooltip1:ProcessInfo({ tooltipData = C_TooltipInfo.GetHyperlink() })
for _, line in ipairs({ ' ', ITEM_DELTA_DESCRIPTION, delta[1], delta[2], 'New annotation' }) do ShoppingTooltip1:AddLine(line) end
feature:Trim(manager, true)
assert(_G.PWTTestShopping1TextLeft4:IsShown() and _G.PWTTestShopping1TextLeft7:IsShown())
ShoppingTooltip1:ClearLines(); ShoppingTooltip1:ProcessInfo({ tooltipData = C_TooltipInfo.GetHyperlink() })
for _, line in ipairs({ ' ', ITEM_DELTA_DESCRIPTION, 'Unexpected row', delta[2] }) do ShoppingTooltip1:AddLine(line) end
feature:Trim(manager, true); assert(_G.PWTTestShopping1TextLeft4:IsShown())
manager.compareInfo.method = 2; feature:Trim(manager, true); assert(_G.PWTTestShopping1TextLeft4:IsShown())
feature:Disable(); manager.compareInfo.method = 0; manager:SetItemTooltip(true)
assert(_G.PWTTestShopping1TextLeft4:IsShown(), 'cleanup off retains native footer')
assert(T.ItemComparison == nil, 'cleanup must not depend on the compact-comparison feature')
-- Run both real feature modules through the same item-processing path.
GetInventoryItemLink = function() end
InCombatLockdown = function() return false end
C_Item = { IsEquippableItem = function() return true end, GetItemInfoInstant = function() return 1 end,
    IsDressableItemByID = function() return false end,
    GetDetailedItemLevelInfo = function(link) return link == 'candidate' and 100 or 80 end }
C_TooltipComparison.GetItemComparisonInfo = function() return manager.compareInfo end
for _, file in ipairs({ 'Comparison', 'Preview', 'Presentation', 'Feature' }) do
    assert(loadfile(root .. '/features/universal-item-tooltips/' .. file .. '.lua'))('PhoenixWoWToolkit', T)
end
local compact = T.feature
compact.settings = { enabled = true, appearance = 'native' }
compact:Enable(); feature:Enable()
local main = tooltip('PWTTestMain')
main.CompareHeader = nil
main.shoppingTooltips = owner.shoppingTooltips
local function hover()
    main:ClearLines()
    main:ProcessInfo({ tooltipData = { hyperlink = 'candidate', lines = { 'Original item', 'Original annotation' } } })
    manager.tooltip = main
    manager:SetItemTooltip(true)
end
hover(); assert(main:NumLines() > 2 and ShoppingTooltip1.h == 56, 'both options on')
compact:Disable(); hover()
assert(main:NumLines() == 2 and ShoppingTooltip1.h == 56, 'cleanup only')
compact:Enable(); feature:Disable(); hover()
assert(main:NumLines() > 2 and ShoppingTooltip1.h == 136, 'compact only')
compact:Disable(); hover()
assert(main:NumLines() == 2 and ShoppingTooltip1.h == 136, 'both options off')
print('Comparison cleanup: exact native footer validation, body/annotation preservation, sizing, refresh and independent restoration passed')
print('Compact tooltips and cleanup: all four enable/disable combinations passed')
if nativeSource then print('Executed original Blizzard TooltipComparisonManager:SetItemTooltip from supplied source') end
print('NOT TESTED: actual font geometry, ElvUI skin behavior or combat taint in WoW')
