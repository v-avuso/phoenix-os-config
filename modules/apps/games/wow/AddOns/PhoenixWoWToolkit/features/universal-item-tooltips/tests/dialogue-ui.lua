-- Executes installed, unmodified Dialogue UI source. Graphics and game APIs are doubles.
local root, upstream = assert(arg[1]), assert(arg[2])
local toc = assert(io.open(upstream .. '/DialogueUI.toc'))
local version = toc:read('*a'):match('## Version:%s*([^%s]+)'); toc:close()
assert(version == '1.0.7', 'This investigation targets the installed Dialogue UI 1.0.7')
unpack = table.unpack or unpack
local function noop() end
local frames, timers, combat = {}, {}, false
local function frame(kind, _, parent, template)
    local f = { kind = kind, parent = parent, scripts = {}, events = {}, shown = true, w = 16, h = 16, points = {}, alpha = 1 }
    function f:SetScript(event, callback) self.scripts[event] = callback end
    function f:HookScript(event, callback)
        local original=self.scripts[event]
        self.scripts[event]=function(...) if original then original(...) end; callback(...) end
    end
    function f:RegisterEvent(event) self.events[event] = true end
    function f:UnregisterEvent(event) self.events[event] = nil end
    function f:Show() if self.nativeResetAlpha then self.alpha=1 end; local changed = not self.shown; self.shown = true; if changed and self.scripts.OnShow then self.scripts.OnShow(self) end end
    function f:Hide() local changed = self.shown; self.shown = false; if changed and self.scripts.OnHide then self.scripts.OnHide(self) end end
    function f:SetShown(shown) self.shown=shown; if shown and self.nativeResetAlpha then self.alpha=1 end end
    function f:IsShown() return self.shown end
    f.IsVisible = f.IsShown
    function f:IsForbidden() return self.forbidden or false end
    function f:IsProtected() return self.protected or false end
    function f:SetSize(w,h) self.w,self.h = w,h end
    function f:SetWidth(w) self.w = w end
    function f:GetWidth() return self.w end
    function f:GetHeight() return self.h end
    function f:SetPoint(...) self.points[#self.points+1] = { ... } end
    function f:ClearAllPoints() self.points = {} end
    function f:SetFrameStrata(strata) self.strata = strata end
    function f:GetFrameStrata() return self.strata or 'TOOLTIP' end
    function f:SetFrameLevel(level) self.level = level end
    function f:GetFrameLevel() return self.level or 1 end
    function f:GetEffectiveScale() return self.scale or 1 end
    function f:GetScale() return self.scale or 1 end
    function f:SetScale(scale) self.scale=scale end
    function f:GetAlpha() return self.alpha end
    function f:GetOwner() return self.owner end
    function f:GetLeft() return self.left or 400 end
    function f:GetRight() return self.right or 600 end
    function f:SetAlpha(alpha) assert(not (combat and self.protected)); self.alpha = alpha end
    function f:GetTextColor() return unpack(self.color or {1,1,1,1}) end
    function f:SetTextColor(...) self.color={...} end
    function f:NumLines() return #(self.rows or {}) end
    function f:GetLeftLine(index) return self.rows[index].left end
    function f:GetRightLine(index) return self.rows[index].right end
    function f:GetPrimaryTooltipData() return self.primaryData end
    function f:SetModelAlpha(alpha) self.modelAlpha = alpha end
    function f:SetText(text) self.text = text end
    function f:GetText() return self.text end
    function f:GetWrappedWidth() return math.min(#(self.text or '')*6, self.w) end
    function f:SetTexture(texture) self.texture = texture end
    function f:GetTexture() return self.texture end
    function f:SetAllPoints() end
    function f:SetBackdrop(info) self.backdrop=info end
    function f:GetBackdrop() return self.backdrop end
    function f:GetBackdropColor() return 0.05,0.05,0.05,1 end
    function f:GetBackdropBorderColor() return 0,0,0,1 end
    function f:SetBackdropColor() end
    function f:SetBackdropBorderColor() end
    function f:EnableMouse() end
    function f:SetFontObject(font) self.font = font end
    function f:TryOn(item) self.tried = item; self.tries = (self.tries or 0)+1 end
    function f:SetUnit(unit) self.unit = unit; self.units = (self.units or 0)+1 end
    function f:SetKey() return true end
    function f:CreateTexture() return frame('Texture', nil, self) end
    function f:CreateFontString() return frame('FontString', nil, self) end
    for _, name in ipairs({ 'SetIgnoreParentScale', 'SetIgnoreParentAlpha', 'SetFixedFrameStrata', 'SetClampedToScreen',
        'SetClampRectInsets', 'SetSpacing', 'SetJustifyV', 'SetJustifyH', 'SetTextureSliceMargins',
        'SetTextureSliceMode', 'SetKeepModelOnHide', 'SetModelDrawLayer', 'SetAutoDress', 'SetDoBlend',
        'SetUseTransmogChoices', 'SetUseTransmogSkin', 'FreezeAnimation', 'SetFacing', 'ClearModel', 'SetAnimation' }) do f[name] = noop end
    frames[#frames+1] = f
    return f
end
CreateFrame = frame
GetCursorPosition = function() return 100,100 end
function EnumerateFrames(previous)
    if not previous then return frames[1] end
    for i, value in ipairs(frames) do if value == previous then return frames[i+1] end end
end
issecretvalue = function(value) return value == 'secret' end
local function drain()
    for _, f in ipairs(frames) do
        local callback = f.scripts.OnUpdate
        if callback then callback(f, 0.05) end
    end
end
C_QuestLog, C_Spell = {}, {}
local color = { GetRGB = function() return 1,1,1 end, GenerateHexColor = function() return 'ffffffff' end }
NORMAL_FONT_COLOR = color
DialogueUI_DB = { TooltipShowItemComparison = true }
DialogueUIAPI = {}
C_Timer = { After = function(_, callback) timers[#timers+1]=callback end }
local dressable = true
C_Item = { IsEquippableItem = function() return true end, IsDressableItemByID = function() return dressable end, GetItemInfoInstant = function() return 123 end,
    GetItemLinkByGUID = function() return 'item:equipped' end }
C_PetJournal = { GetPetInfoByItemID = noop }
C_TransmogCollection = { GetAppearanceCameraIDBySource = function() return 70 end }
Model_ApplyUICamera = function(model, camera) model.appliedCamera = camera end
local compareCalls, comparisonMethod = 0,0
TooltipComparisonManager = { AnchorShoppingTooltips = noop, CreateComparisonItem = function(_,data) if data.type == 0 then return { hyperlink = data.hyperlink } end end }
C_TooltipComparison = {
    GetItemComparisonInfo = function(item) if not item then return end; compareCalls=compareCalls+1; return { method = comparisonMethod, item = { guid = 'equipped' }, additionalItems = {} } end,
    GetItemComparisonDelta = function() return { '+38 Stamina', '-51 Critical Strike' } end,
}
local dataCalls = 0
local function getData(link)
    dataCalls = dataCalls+1
    return { hyperlink = link or 'item:quest', dataInstanceID = 10, lines = {
        { leftText = 'Original bag item', leftColor = color }, { leftText = 'Item Level 100', leftColor = color },
        { leftText = '+20 Intellect', leftColor = color }, { leftText = 'Other native item information', leftColor = color },
    } }
end
local api = {
    Round = function(x) return math.floor(x+0.5) end, GetPixelForScale = function(_,x) return x end,
    UpdateTextureSliceScale = noop, DeltaLerp = noop, SetModelLight = noop,
    GetItemQualityColor = function() return 1,1,1 end, IsItemValidForComparison = function() return true end,
    GetTransmogItemInfo = function() return 200,300 end, AlwaysFalse = function() return false end,
    IsHoldableItem = function() return false end, GetTransmogSetup = function() return true end,
    SetModelByUnit = function(model,unit) model:SetUnit(unit) end,
    GetMaxEquippedItemLevelDelta = function() return nil,true end,
    GetItemLevelDelta = function() return '+13 Item Level' end,
    GetItemEffect = function() return nil,true end,
    GenerateMoneyText = function(price) return tostring(price)..' coins' end,
    Mixin = function(target, source) for k,v in pairs(source) do target[k]=v end; return target end,
    CreateFromMixins = function(source) local t={}; for k,v in pairs(source) do t[k]=v end; return t end,
    CreateObjectPool = function() return { Release = noop } end,
}
local addon = { API = api, PixelUtil = { AddPixelPerfectObject = noop },
    ThemeUtil = { GetTextureFile = function(_,name) return 'DialogueUI-owned/'..name end },
    L = { ['Format Replace Item'] = 'Replace [%s]', ['Hide Comparison'] = 'Hide Comparison', ['Show Comparison'] = 'Show Comparison' },
    DeviceUtil = { IsShiftDown = function(key,state) return key == 'LSHIFT' and state == 1 end },
    TooltipAPI = { GetHyperlink = getData, GetItemByGUID = getData, GetQuestItem = getData },
}
assert(loadfile(upstream..'/Code/CallbackRegistry.lua'))('DialogueUI', addon)
local files = { 'Tooltip_Base.lua', 'Tooltip_Private.lua', 'Tooltip_Public.lua' }
for _, file in ipairs(files) do
    assert(loadfile(upstream..'/Code/Tooltip/'..file))('DialogueUI', addon)
end
-- The production adapter uses these public native primitives.
function CreateColor(r,g,b,a)
    return { GetRGB=function() return r,g,b end,
        GenerateHexColor=function() return string.format('ff%02x%02x%02x',r*255,g*255,b*255) end }
end
function hooksecurefunc(object,key,callback)
    local original=assert(object[key],key)
    object[key]=function(...)
        local result=table.pack(original(...)); callback(...); return table.unpack(result,1,result.n)
    end
end
if arg[3] then
    local manager=TooltipComparisonManager
    RegisterEventCallback=noop
    assert(loadfile(arg[3]))()
    manager.CreateComparisonItem=TooltipComparisonManager.CreateComparisonItem
    TooltipComparisonManager=manager
end
C_AddOns = { IsAddOnLoaded=function() return true end, GetAddOnMetadata=function() return '1.0.7' end }
Enum = { TooltipDataType={Item=0}, TooltipComparisonMethod={Single=0,WithBothHands=1,WithBagMainHandItem=2,WithBagOffHandItem=3} }
InCombatLockdown=function() return combat end
GetInventoryItemLink=noop
local postcalls={}
TooltipDataProcessor = { AllTypes='all', AddTooltipPostCall=function(kind,fn)
    postcalls[kind]=postcalls[kind] or {}; table.insert(postcalls[kind],fn)
end }
local T = { RegisterFeature=function(self,feature) self.feature=feature end }
for _, name in ipairs({'Comparison','DialogueUI','Style','Feature'}) do
    assert(loadfile(root..'/features/universal-item-tooltips/'..name..'.lua'))('PhoenixWoWToolkit',T)
end
local found, reason = T.DialogueTooltip.Find('1.0.7')
local shared=addon.SharedTooltip
assert(found==shared and not reason and not shared.PreviewModel, 'find actual renderer before first quest hover')
assert(not T.DialogueTooltip.Find('unknown'))
-- SetHyperlink alone bypasses item-aware processing in the original source.
local captured
DialogueUIAPI.AddItemTooltipProcessorExternal(function(tooltip) captured=tooltip end)
shared:SetOwner(frame('BagButton'),'ANCHOR_NONE'); shared:SetHyperlink('item:candidate'); drain()
assert(compareCalls==0 and not captured)
shared:Hide(); shared:SetShowDelay(0.25) -- Main Dialogue UI configures this delay.
GameTooltip=frame('GameTooltip')
GameTooltip.owner=frame('BagButton')
GameTooltip.alpha=0.85
local source=GameTooltip
local nativeShow=source.Show -- C/internal callers can retain the original Show primitive.
local data=getData('item:candidate'); data.type=0
for i,line in ipairs(data.lines) do line.lineIndex=i end
data.lines[4].price=42
source.primaryData=data
local function setRows(texts)
    source.rows={}
    for _,text in ipairs(texts) do
        local left,right=frame('FontString'),frame('FontString')
        left:SetText(text); right:Hide(); right:SetText('stale hidden text')
        source.rows[#source.rows+1]={left=left,right=right}
    end
end
local feature=T.feature
feature.settings={enabled=true,appearance='dialogue'} -- Old choice migrates to the actual renderer.
feature:Enable(); assert(feature.settings.appearance=='dialogueUI')
local function hover()
    if source.scripts.OnTooltipCleared then source.scripts.OnTooltipCleared(source) end
    setRows({'Original bag item','Item Level 100','+20 Intellect','Original item information','ElvUI annotation'})
    for _,fn in ipairs(postcalls.all or {}) do fn(source,data) end
    for _,fn in ipairs(postcalls[0]) do fn(source,data) end
    -- Simulate a processor registered after Phoenix, before the final native Show.
    source.rows[5].left:SetText('Late ElvUI annotation')
    source.rows[5].left:SetTextColor(0,1,0,1)
    source:Show(); drain()
end
hover()
assert(feature.adapter.lease and source.alpha==0 and shared:IsShown() and shared.alpha==1 and shared.showDelay == -0.25, 'global hover is immediate without changing the quest tooltip delay')
assert(captured==shared and shared:GetLeftLineText(5)=='Late ElvUI annotation', 'actual renderer preserves late native text')
assert(shared.grid[5][1].color[2]==1 and shared.grid[5][1].color[1]==0)
assert(shared:GetLeftLineText(4):find('42 coins',1,true),'semantic native price row survives the mirror')
assert(shared.Background.texture=='DialogueUI-owned/TooltipBackground-Temp.png')
assert(shared.grid[1][1].font=='DUIFont_Tooltip_Large')
assert(shared.PreviewModel.Model1.tried==300 and shared.PreviewModel.y>0)
assert(shared:GetLeftLineText(7)=='Replace [item:equipped]')
assert(not shared.events.TOOLTIP_DATA_UPDATE, 'native tooltip owns data refresh while leased')
local model=shared.PreviewModel.Model1
model.scripts.OnModelLoaded(model); assert(model.appliedCamera==70)
local tries=model.tries
hover(); source:Show()
local work=timers; timers={}; for _,fn in ipairs(work) do fn() end
assert(model.tries==tries and shared:IsShown(), 'repeat rebuilds never reset model or fade')
-- Native C Show/SetShown can restore alpha without invoking the Lua SetAlpha hook.
source.nativeResetAlpha=true
source:Show(); assert(source.alpha==0 and model.tries==tries, 'cached hovers must reapply native suppression after Show')
source:SetShown(true); assert(source.alpha==0 and model.tries==tries, 'SetShown uses the same suppression path without reloading the model')
source.nativeResetAlpha=false
-- Preserve external alpha intent while keeping the source processing active.
source:SetAlpha(0); assert(source.alpha==0 and shared.alpha==1, 'the masked native tooltip must not make the replacement transparent')
source:SetAlpha(0.6); assert(source.alpha==0 and shared.alpha==1)
source.rows[5].left:SetText('Updated annotation'); source:Show()
assert(shared:GetLeftLineText(5)=='Updated annotation' and model.tries==tries)
shared:OnEvent('MODIFIER_STATE_CHANGED','LSHIFT',1)
assert(not DialogueUI_DB.TooltipShowItemComparison and not shared.events.TOOLTIP_DATA_UPDATE)
shared:OnEvent('MODIFIER_STATE_CHANGED','LSHIFT',0)
assert(not DialogueUI_DB.TooltipShowItemComparison)
shared:OnEvent('MODIFIER_STATE_CHANGED','LSHIFT',1)
assert(DialogueUI_DB.TooltipShowItemComparison)
-- Side-by-side comparisons keep their native behavior; only our renderer is placed.
local compare=frame('ShoppingTooltip'); compare.left=650; source.shoppingTooltips={compare}
TooltipComparisonManager:AnchorShoppingTooltips()
assert(shared.points[1][1]=='TOPRIGHT', 'render away from a comparison on the right')
compare.left=100; TooltipComparisonManager:AnchorShoppingTooltips()
assert(shared.points[1][1]=='TOPLEFT')
-- Quest takeover restores native alpha, without hiding the new quest tooltip.
local questOwner=frame('QuestRewardButton')
shared:SetOwner(questOwner,'ANCHOR_NONE'); shared:SetQuestItem('reward',1)
assert(not feature.adapter.lease and source.alpha==0.6 and shared:IsShown())
source:Show(); assert(not feature.adapter.lease, 'never steal a busy quest renderer')
shared:Hide(); hover()
feature:Disable(); assert(not shared:IsShown() and source.alpha==0.6)
-- Unavailable versions keep the original presentation and compact native option.
feature:Enable(); hover()
C_AddOns.GetAddOnMetadata=function() return 'changed' end
source:Show(); assert(not feature.adapter.lease and source.alpha==0.6)
C_AddOns.GetAddOnMetadata=function() return '1.0.7' end
hover()
comparisonMethod=1
source:Show(); assert(not feature.adapter.lease and source.alpha==0.6,'unproven combined weapon comparison stays native')
comparisonMethod=0
data.overrideItemLevel=700
source:Show(); assert(not feature.adapter.lease and source.alpha==0.6,'override-level math remains native')
data.overrideItemLevel=nil
GetInventoryItemLink=function() return 'item:candidate' end
source:Show(); assert(feature.adapter.lease and shared:GetLeftLineText(7)~='Replace [item:equipped]','equipped content stays uniform without self comparison')
GetInventoryItemLink=noop
hover()
-- A non-item tooltip must become visible immediately, not await a cleanup timer.
source.primaryData={type=9,hyperlink='item:candidate'}
for _,fn in ipairs(postcalls.all) do fn(source,source.primaryData) end
source:Show()
assert(source.alpha==0.6 and not shared:IsShown())
source.primaryData=data
hover()
local stableTries=model.tries
source:Hide(); nativeShow(source)
local pending=timers; timers={}; for _,fn in ipairs(pending) do fn() end
assert(feature.adapter.lease and model.tries==stableTries,'same-frame native hide/show must retain the loaded preview')
source:Hide()
pending=timers; timers={}; for _,fn in ipairs(pending) do fn() end
assert(not feature.adapter.lease and source.alpha==0.6,'a real leave releases on the next frame')
nativeShow(source); assert(feature.adapter.lease and source.alpha==0, "OnShow must catch internal/cached Show calls")
combat,source.protected=true,true
feature:Render(source,data)
assert(not feature.adapter.lease and feature.adapter.pending[source]==0.6, 'defer protected alpha restoration')
source.protected=false
feature.adapter:RestorePending(source)
assert(source.alpha==0.6 and not feature.adapter.pending[source])
combat=false
-- Independent base renderer: no singleton model/comparison callbacks are copied.
local comparison=frame('GameTooltip');comparison.left=100;comparison.right=380
local header=frame('FontString');header:SetText('Equipped')
comparison.CompareHeader={Label=header}
comparison.primaryData={type=0,hyperlink='item:equipped',lines={}}
comparison.rows={}
for _,text in ipairs({'Equipped body','Native annotation'}) do
    local left,right=frame('FontString'),frame('FontString');left:SetText(text);right:Hide()
    comparison.rows[#comparison.rows+1]={left=left,right=right}
end
for _,fn in ipairs(postcalls.all) do fn(comparison,comparison.primaryData) end
comparison:Show()
local pending=timers;timers={};for _,fn in ipairs(pending) do fn() end
drain()
local styled=feature.style.states[comparison]
assert(styled and styled.view and styled.active and comparison.alpha==0,'comparison tooltip gets a separate actual base renderer')
assert(styled.view:GetLeftLineText(1)=='Equipped' and styled.view:GetLeftLineText(3)=='Native annotation')
comparison.rows[2].left:SetText('Updated annotation')
for _,fn in ipairs(postcalls.all) do fn(comparison,comparison.primaryData) end
local update=timers;timers={};for _,fn in ipairs(update) do fn() end
drain()
assert(styled.view:GetLeftLineText(3)=='Updated annotation','visible pane updates without Show')
local second=frame('GameTooltip');second.left=20;second.right=90
second.CompareHeader={Label=header};second.primaryData=comparison.primaryData;second.rows=comparison.rows
for _,fn in ipairs(postcalls.all) do fn(second,second.primaryData) end
second:Show()
local updates=timers;timers={};for _,fn in ipairs(updates) do fn() end
drain()
feature.style:Place()
local secondView=feature.style.states[second].view
assert(secondView.points[1][1]=='TOPRIGHT' and secondView.points[1][2]==styled.view
    and secondView.points[1][3]=='TOPLEFT','outer equipped pane chains against rendered inner pane, not native width')
local width1,width2=styled.view:GetWidth(),secondView:GetWidth()
styled.view:SetWidth(700);secondView:SetWidth(700)
UIParent={GetWidth=function() return 1500 end,GetEffectiveScale=function() return 1 end}
feature.style:Place()
assert(styled.view:GetScale()<1 and secondView:GetScale()==styled.view:GetScale(),'wide comparison group scales together to fit available side')
UIParent=nil;styled.view:SetWidth(width1);secondView:SetWidth(width2)
feature.style:Place();assert(styled.view:GetScale()==1,'normal scale restored when space allows')
second:Hide()
local updates=timers;timers={};for _,fn in ipairs(updates) do fn() end
assert(not feature.style.states[second].active,'second comparison releases independently')
assert(not styled.view.DisplayModel and not styled.view.ShowItemComparison,'private singleton methods are never cloned')
feature.settings.framing='native';feature.style:Configure(true)
assert(shared.Background.shown==false and feature.style.states[shared].chrome.shown,'default frame with Dialogue UI content')
feature.settings.appearance='native';feature.style:Configure(true)
assert(comparison.alpha==1 and not styled.active,'default content restores native comparison pane')
feature.settings.framing='dialogueUI';feature.style:Configure(true)
assert(feature.style.states[comparison].texture.shown,'Dialogue UI framing with default content')
feature.settings.appearance='dialogueUI';feature.style:Configure(true)
assert(styled.active and comparison.alpha==0,'switching content back takes effect immediately')
local hideHovered=false
T.ComparisonVisibility={IsManaged=function() return true end,HidesHovered=function() return hideHovered end,BodyLineLimit=function() end}
source:Show();feature:Render(source,data,true)
assert(not shared.events.MODIFIER_STATE_CHANGED and not shared.HotkeyFrame:IsShown(),'globally managed comparisons omit the Shift hint')
hideHovered=true;feature:Render(source,data,true)
assert(shared:GetLeftLineText(7)==nil,'hovered comparison can be independently hidden')
dressable=false
C_MountJournal={GetMountFromItem=function() end}
feature:Render(source,data,true)
assert(feature.adapter.lease and not shared.usePreviewModel,'items without a model retain the same original content renderer')
feature:Disable();assert(comparison.alpha==1 and not styled.view:IsShown(),'disable restores all owned panes')
if arg[3] then print('Executed Blizzard original CreateComparisonItem with the mirrored Dialogue UI item data') end
print('Dialogue UI original renderer + production adapter: native annotation mirror, upstream theme/fonts/model/Shift, stable rebuilds, alpha restoration, comparison placement, quest takeover, version and non-item fallback passed')
print('NOT TESTED: GPU pixels, live bags/AH, arbitrary custom widgets, combat/taint or quest handoffs inside WoW')
