local _, Toolkit = ...
local feature = { id = "universalItemTooltips", section = "Item Tooltips", defaults = { enabled = true },
    dependencies = { "Blizzard_SharedXMLGame" }, states = {} }

local function safe(tooltip)
    return not tooltip:IsForbidden() and not tooltip:IsProtected()
        and not (tooltip.IsAnchoringSecret and tooltip:IsAnchoringSecret())
end

function feature:GetAvailability()
    return not not (TooltipDataProcessor and C_TooltipComparison and C_TooltipComparison.GetItemComparisonInfo
        and C_TooltipComparison.GetItemComparisonDelta and C_Item and C_Item.IsEquippableItem
        and C_Item.GetItemInfoInstant and C_Item.IsDressableItemByID and Enum and Enum.TooltipComparisonMethod ~= nil)
end

function feature:Process(tooltip, data)
    if not self.running or not safe(tooltip) or tooltip.CompareHeader then return end
    local candidate = Toolkit.ItemComparison.Candidate(data)
    local link = candidate and Toolkit.ItemComparison.Link(candidate)
    if not link or (issecretvalue and issecretvalue(link)) or not C_Item.IsEquippableItem(link) then return end
    local state = self.states[tooltip]
    if not state then
        state = {}; self.states[tooltip] = state
        local function clear() state.data = nil; Toolkit.ItemPreview.Hide(state) end
        tooltip:HookScript("OnTooltipCleared", clear)
        tooltip:HookScript("OnHide", clear)
        tooltip:HookScript("OnShow", function() Toolkit.ItemPreview.Place(state, tooltip) end)
        tooltip:HookScript("OnSizeChanged", function() Toolkit.ItemPreview.Place(state, tooltip) end)
    end
    if state.data == data then return end
    state.data = data
    for _, group in ipairs(Toolkit.ItemComparison.Groups(data)) do
        tooltip:AddLine(" ")
        local title = "Replace " .. group.equipped
        if group.partner then title = title .. (group.paired and " (with " or " + ") .. group.partner .. (group.paired and ")" or "") end
        tooltip:AddLine(title, 1, 0.82, 0, true)
        for _, row in ipairs(group.rows) do tooltip:AddLine(row, 1, 1, 1, true) end
    end
    Toolkit.ItemPreview.Show(state, tooltip, link)
end

function feature:RefreshOwned()
    for tooltip, state in pairs(self.states) do
        state.data = nil
        Toolkit.ItemPreview.Hide(state)
        if not InCombatLockdown() and safe(tooltip) and tooltip:IsShown() and tooltip.RebuildFromTooltipInfo then
            tooltip:RebuildFromTooltipInfo()
        end
    end
end

function feature:Enable()
    self.running = true
    if not self.registered then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip, data) self:Process(tooltip, data) end)
        self.registered = true
    end
    self:RefreshOwned()
end

function feature:Disable() self.running = false; self:RefreshOwned() end

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Use Dialogue UI-style item tooltips", y,
        self.settings, "enabled", function() Toolkit:RefreshFeatures() end,
        "Add compact replacement statistics and an equipment preview; keep your tooltip information.")
    return y - 72
end
function feature:RefreshSettings() self.checkbox:SetChecked(self.settings.enabled); self.checkbox:SetEnabled(self.available) end
Toolkit:RegisterFeature(feature)
