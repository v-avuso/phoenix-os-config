-- Executes installed, unmodified Dialogue UI source. Graphics and game APIs are doubles.
local root, upstream = assert(arg[1]), assert(arg[2])
local toc = assert(io.open(upstream .. '/DialogueUI.toc'))
local version = toc:read('*a'):match('## Version:%s*([^%s]+)'); toc:close()
assert(version == '1.0.7', 'This investigation targets the installed Dialogue UI 1.0.7')
unpack = table.unpack or unpack
local function noop() end
local frames = {}
local function frame(kind, _, parent, template)
    local f = { kind = kind, parent = parent, scripts = {}, events = {}, shown = true, w = 16, h = 16, points = {}, alpha = 1 }
    function f:SetScript(event, callback) self.scripts[event] = callback end
    function f:RegisterEvent(event) self.events[event] = true end
    function f:UnregisterEvent(event) self.events[event] = nil end
    function f:Show() local changed = not self.shown; self.shown = true; if changed and self.scripts.OnShow then self.scripts.OnShow(self) end end
    function f:Hide() local changed = self.shown; self.shown = false; if changed and self.scripts.OnHide then self.scripts.OnHide(self) end end
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
    function f:GetEffectiveScale() return 1 end
    function f:SetAlpha(alpha) self.alpha = alpha end
    function f:SetModelAlpha(alpha) self.modelAlpha = alpha end
    function f:SetText(text) self.text = text end
    function f:GetText() return self.text end
    function f:GetWrappedWidth() return math.min(#(self.text or '')*6, self.w) end
    function f:SetTexture(texture) self.texture = texture end
    function f:SetFontObject(font) self.font = font end
    function f:TryOn(item) self.tried = item; self.tries = (self.tries or 0)+1 end
    function f:SetUnit(unit) self.unit = unit; self.units = (self.units or 0)+1 end
    function f:SetKey() return true end
    function f:CreateTexture() return frame('Texture', nil, self) end
    function f:CreateFontString() return frame('FontString', nil, self) end
    for _, name in ipairs({ 'SetIgnoreParentScale', 'SetIgnoreParentAlpha', 'SetFixedFrameStrata', 'SetClampedToScreen',
        'SetClampRectInsets', 'SetSpacing', 'SetJustifyV', 'SetJustifyH', 'SetTextColor', 'SetTextureSliceMargins',
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
C_Timer = { After = function() error('Unexpected uncached-item retry') end }
C_Item = { IsDressableItemByID = function() return true end, GetItemInfoInstant = function() return 123 end,
    GetItemLinkByGUID = function() return 'item:equipped' end }
C_PetJournal = { GetPetInfoByItemID = noop }
C_TransmogCollection = { GetAppearanceCameraIDBySource = function() return 70 end }
Model_ApplyUICamera = function(model, camera) model.appliedCamera = camera end
local compareCalls = 0
TooltipComparisonManager = { CreateComparisonItem = function(_,data) return { hyperlink = data.hyperlink } end }
C_TooltipComparison = {
    GetItemComparisonInfo = function() compareCalls=compareCalls+1; return { method = 0, item = { guid = 'equipped' }, additionalItems = {} } end,
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
local probe = assert(loadfile(root..'/features/universal-item-tooltips/research/DialogueUIProbe.lua'))()
local shared, reason = probe.Find('1.0.7')
assert(shared and not reason)
assert(shared == addon.SharedTooltip, 'one-time structural discovery locates the real, initially unused singleton')
assert(not shared.PreviewModel, 'discovery works before the first quest hover initializes the model')
assert(not probe.Find('unknown'))
-- Public annotation callback gives the same actual instance, without namespace access.
local captured
DialogueUIAPI.AddItemTooltipProcessorExternal(function(tooltip) captured=tooltip end)
shared:SetOwner(frame('BagButton'), 'ANCHOR_NONE')
shared:SetHyperlink('item:candidate')
drain()
assert(compareCalls == 0 and not captured, 'SetHyperlink does NOT mark data as an item or trigger item processors')
shared:Hide()
local owner = frame('BagButton')
local lease = assert(probe.Show(shared, owner, 'item:candidate'))
drain()
assert(captured == shared, 'public callback receives the same renderer used for the bag-item proof')
assert(compareCalls > 0 and shared.HotkeyFrame:IsShown(), 'actual comparison and modifier-hint machinery runs')
assert(shared.Background.texture == 'DialogueUI-owned/TooltipBackground-Temp.png', 'upstream owns its theme asset')
assert(shared.PreviewModel.Model1.tried == 300 and shared.PreviewModel.y > 0, 'actual source-based preview overhangs the tooltip')
assert(shared.grid[1][1].font == 'DUIFont_Tooltip_Large', 'upstream font objects are used')
assert(shared:GetLeftLineText(6) == 'Replace [item:equipped]')
local model = shared.PreviewModel.Model1
model.scripts.OnModelLoaded(model)
assert(model.appliedCamera == 70, 'upstream applies its camera after model loading')
assert(not probe.Show(shared, owner, 'secret', lease), 'restricted input retains the original display')
local tries, reads = model.tries, dataCalls
assert(probe.Show(shared, owner, 'item:candidate', lease) == lease)
assert(model.tries == tries and dataCalls == reads, 'same hover does not repeatedly reload the model')
shared:OnEvent('MODIFIER_STATE_CHANGED', 'LSHIFT', 1)
assert(DialogueUI_DB.TooltipShowItemComparison == false and shared:GetLeftLineText(6) == 'Show Comparison', 'original Shift toggle works')
shared:OnEvent('MODIFIER_STATE_CHANGED', 'LSHIFT', 0)
assert(DialogueUI_DB.TooltipShowItemComparison == false, 'releasing Shift must not toggle a second time')
shared:OnEvent('MODIFIER_STATE_CHANGED', 'LSHIFT', 1)
assert(DialogueUI_DB.TooltipShowItemComparison == true, 'comparison preference is owned by Dialogue UI')
-- A quest takeover wins, and releasing our stale lease cannot hide it.
local questOwner = frame('QuestRewardButton')
shared:SetOwner(questOwner, 'ANCHOR_NONE'); shared:SetQuestItem('reward',1)
assert(not probe.Show(shared, owner, 'item:candidate', lease), 'do not steal a live quest tooltip')
probe.Release(lease)
assert(shared:IsShown() and shared.owner == questOwner, 'stale release preserves quest ownership')
shared:Hide()
lease = assert(probe.Show(shared,owner,'item:candidate'))
probe.Release(lease)
assert(not shared:IsShown() and not shared.tooltipInfo and not shared.events.TOOLTIP_DATA_UPDATE)
local duplicate = frame('Frame')
for _, name in ipairs({ 'ProcessInfo', 'ShowItemComparison', 'DisplayModel', 'ShowHotkey', 'GetHyperlink', 'SetQuestItem' }) do duplicate[name]=noop end
duplicate.forbidden = true
assert(probe.Find('1.0.7') == shared, 'skip forbidden frames before inspecting their structure')
duplicate.forbidden, duplicate.protected = false,true
assert(probe.Find('1.0.7') == shared, 'skip protected candidates')
duplicate.protected = false
assert(not probe.Find('1.0.7'), 'ambiguous discovery fails safely')
print('Dialogue UI original renderer: bag-item data, theme/fonts, overhanging preview, source camera, comparisons, modifier toggle, refresh coalescing and singleton lease passed')
print('NOT TESTED: GPU pixels, live native-tooltip suppression, annotations from other add-ons, combat/taint, bags/AH or quest handoffs inside WoW')
