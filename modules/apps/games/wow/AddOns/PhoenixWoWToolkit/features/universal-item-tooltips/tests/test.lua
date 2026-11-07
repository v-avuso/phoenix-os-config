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
-- Native fallback and dropdown remain independent of the optional renderer.
local callbacks, combat = {}, false
TooltipDataProcessor = { AllTypes='all', AddTooltipPostCall=function(kind,fn) callbacks[kind]=fn end }
C_AddOns={ IsAddOnLoaded=function() return false end }
InCombatLockdown=function() return combat end
local function frame()
    local f={scripts={}}
    function f:SetScript(event,fn) self.scripts[event]=fn end
    function f:RegisterEvent() end
    function f:SetPoint() end
    function f:SetWidth() end
    function f:SetSize() end
    function f:SetMinMaxValues() end
    function f:SetValueStep() end
    function f:SetObeyStepOnDrag() end
    function f:SetValue(value) self.value=value;if self.scripts.OnValueChanged then self.scripts.OnValueChanged(self,value) end end
    function f:SetChecked(value) self.checked=value end
    function f:SetEnabled(value) self.enabled=value end
    function f:SetupMenu(fn) self.generate=fn end
    function f:OverrideText(text) self.label=text end
    return f
end
CreateFrame=frame
assert(loadfile(root..'/features/universal-item-tooltips/DialogueUI.lua'))('PhoenixWoWToolkit',T)
assert(loadfile(root..'/features/universal-item-tooltips/Feature.lua'))('PhoenixWoWToolkit',T)
local feature=T.feature
feature.settings={enabled=true,appearance='dialogue'}
feature:Enable(); assert(feature.settings.appearance=='dialogueUI')
info={method=0,item={hyperlink='equipped'},additionalItems={}}
local tooltip={lines={'Original stats','Other add-on annotation'},hooks={}}
function tooltip:IsForbidden() return self.forbidden or false end
function tooltip:IsProtected() return false end
function tooltip:IsShown() return true end
function tooltip:HookScript(event,fn) self.hooks[event]=fn end
function tooltip:AddLine(text) self.lines[#self.lines+1]=text end
function tooltip:RebuildFromTooltipInfo()
    self.lines={'Original stats','Other add-on annotation'}
    if self.hooks.OnTooltipCleared then self.hooks.OnTooltipCleared() end
    callbacks[0](self,data)
end
GameTooltip=tooltip
callbacks[0](tooltip,data)
assert(#tooltip.lines==7 and tooltip.lines[2]=='Other add-on annotation','missing Dialogue UI falls back to compact native content')
callbacks[0](tooltip,data); assert(#tooltip.lines==7,'no duplicate summary')
feature:Disable(); assert(#tooltip.lines==2)
feature:Enable(); assert(#tooltip.lines==7)
feature:SetAppearance('native'); assert(#tooltip.lines==7)
feature:SetAppearance('invalid'); assert(feature.settings.appearance=='native')
T.Options={Text=function() end,Checkbox=frame}
feature.available=true; feature:RegisterSettings({},0); feature:RefreshSettings()
feature.opacitySlider.scripts.OnValueChanged(feature.opacitySlider,82.2)
assert(feature.settings.backgroundOpacity==82 and feature.opacitySlider.value==82,'opacity slider persists a rounded percentage')
local choices={}
feature.dropdown.generate(nil,{CreateRadio=function(_,label,selected,choose,value) choices[value]={label=label,selected=selected,choose=choose} end})
assert(choices.native.selected('native') and not choices.dialogueUI.selected('dialogueUI'))
choices.dialogueUI.choose('dialogueUI')
assert(feature.settings.appearance=='dialogueUI' and feature.dropdown.label==choices.dialogueUI.label)
feature.settings.enabled=false; feature:RefreshSettings(); assert(not feature.dropdown.enabled)
combat=true; feature:Disable()
print('Item tooltips: native deltas, ring/weapon delegation, optional-dependency fallback, annotations, independent settings and approach migration passed')
