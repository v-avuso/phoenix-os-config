local _, Toolkit = ...
local feature = { id = "universalItemTooltips", section = "Item Tooltips", defaults = { enabled = true, appearance = "dialogue" },
    dependencies = { "Blizzard_SharedXMLGame" }, states = {} }
local appearances = {
    { "native", "Current UI + compact comparisons" },
    { "dialogue", "Dialogue-inspired + embedded preview" },
}

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
    if not self.running or not safe(tooltip) then return end
    local candidate = Toolkit.ItemComparison.Candidate(data)
    local link = candidate and Toolkit.ItemComparison.Link(candidate)
    if not link or (issecretvalue and issecretvalue(link)) or not C_Item.IsEquippableItem(link) then return end
    local state = self.states[tooltip]
    if not state then
        state = {}; self.states[tooltip] = state
        local function clear()
            state.data = nil
            Toolkit.ItemPreview.Hide(state)
            Toolkit.ItemPresentation.Restore(state, tooltip)
        end
        tooltip:HookScript("OnTooltipCleared", clear)
        tooltip:HookScript("OnHide", clear)
        tooltip:HookScript("OnShow", function() Toolkit.ItemPreview.Place(state, tooltip) end)
        tooltip:HookScript("OnSizeChanged", function() Toolkit.ItemPreview.Place(state, tooltip) end)
    end
    if state.data == data then return end
    state.data = data
    local styled = self.settings.appearance == "dialogue"
    if styled then Toolkit.ItemPresentation.Apply(state, tooltip) end
    -- Give comparison windows the same typography, without adding self comparisons/models.
    if tooltip.CompareHeader then return end
    for _, group in ipairs(Toolkit.ItemComparison.Groups(data)) do
        tooltip:AddLine(" ")
        local title = "Replace " .. group.equipped
        if group.partner then title = title .. (group.paired and " (with " or " + ") .. group.partner .. (group.paired and ")" or "") end
        tooltip:AddLine(title, 1, 0.82, 0, true)
        for _, row in ipairs(group.rows) do tooltip:AddLine(row, 1, 1, 1, true) end
    end
    if styled then
        Toolkit.ItemPresentation.Apply(state, tooltip)
        Toolkit.ItemPreview.Show(state, tooltip, link)
    end
end

function feature:RefreshOwned()
    for tooltip, state in pairs(self.states) do
        state.data = nil
        Toolkit.ItemPreview.Hide(state)
        Toolkit.ItemPresentation.Restore(state, tooltip)
        if not InCombatLockdown() and safe(tooltip) and tooltip:IsShown() and tooltip.RebuildFromTooltipInfo then
            tooltip:RebuildFromTooltipInfo()
        end
    end
end

function feature:Enable()
    if self.settings.appearance ~= "native" and self.settings.appearance ~= "dialogue" then
        self.settings.appearance = self.defaults.appearance
    end
    self.running = true
    if not self.registered then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip, data) self:Process(tooltip, data) end)
        self.registered = true
    end
    self:RefreshOwned()
end

function feature:Disable() self.running = false; self:RefreshOwned() end

function feature:SetAppearance(value)
    if value ~= "native" and value ~= "dialogue" then return end
    self.settings.appearance = value
    self:RefreshOwned()
    self:RefreshSettings()
end

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Enhance equipment tooltips", y,
        self.settings, "enabled", function() Toolkit:RefreshFeatures() end,
        "Add replacement statistics while preserving item information and other add-on notes.")
    Toolkit.Options.Text(panel, "Tooltip approach", y - 64)
    local dropdown = CreateFrame("DropdownButton", nil, panel, "WowStyle1DropdownTemplate")
    self.dropdown = dropdown
    dropdown:SetPoint("TOPLEFT", 24, y - 90)
    dropdown:SetWidth(340)
    dropdown:SetupMenu(function(_, menu)
        for _, entry in ipairs(appearances) do
            menu:CreateRadio(entry[2], function(value) return self.settings.appearance == value end,
                function(value) self:SetAppearance(value) end, entry[1])
        end
    end)
    return y - 132
end
function feature:RefreshSettings()
    if not self.checkbox then return end
    self.checkbox:SetChecked(self.settings.enabled)
    self.checkbox:SetEnabled(self.available)
    self.dropdown:SetEnabled(self.settings.enabled and self.available)
    for _, entry in ipairs(appearances) do
        if entry[1] == self.settings.appearance then self.dropdown:OverrideText(entry[2]) end
    end
end
Toolkit:RegisterFeature(feature)
