local _, Toolkit = ...
local feature = { id = "comparisonCleanup", section = "Comparison Cleanup", defaults = { enabled = true },
    dependencies = { "Blizzard_SharedXMLGame" }, states = {}, watched = {} }
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local function accessible(value) return public(value) and (not canaccessallvalues or canaccessallvalues(value)) end
local function safe(tooltip)
    return tooltip and not tooltip:IsForbidden() and not tooltip:IsProtected()
        and not (tooltip.IsAnchoringSecret and tooltip:IsAnchoringSecret())
end
local function region(tooltip, side, index) return _G[tooltip:GetName() .. "Text" .. side .. index] end

function feature:GetAvailability()
    return not not (TooltipComparisonManager and type(TooltipComparisonManager.SetItemTooltip) == "function"
        and type(TooltipComparisonManager.Initialize) == "function" and C_TooltipComparison
        and C_TooltipComparison.GetItemComparisonDelta and Enum and Enum.TooltipComparisonMethod)
end

function feature:Apply(tooltip)
    local state = self.states[tooltip]
    if self.writing or not self.running or not state or not state.first or not safe(tooltip) then return end
    if tooltip:NumLines() ~= state.last then
        if state.trimmed then
            for _, entry in ipairs(state.regions) do entry.region:SetShown(entry.shown) end
            state.trimmed = false
        end
        return
    end
    local width, height = tooltip:GetSize()
    if not public(width) or not public(height) then return end
    if width ~= state.bodyWidth or height ~= state.bodyHeight then
        state.fullWidth, state.fullHeight = width, height
    end
    if not state.fullWidth then return end -- Wait for native layout, rather than guess.
    self.writing = true
    for _, entry in ipairs(state.regions) do entry.region:Hide() end
    tooltip:SetSize(state.bodyWidth, state.bodyHeight)
    self.writing = false
    state.trimmed = true
end

function feature:Watch(tooltip)
    if not safe(tooltip) or self.watched[tooltip] or not tooltip.ProcessInfo then return end
    local name = tooltip:GetName()
    if not public(name) or type(name) ~= "string" then return end
    self.watched[tooltip] = true
    hooksecurefunc(tooltip, "ProcessInfo", function()
        if not self.running or not safe(tooltip) then return end
        local width, height = tooltip:GetSize()
        if public(width) and public(height) and width > 0 and height > 0 then
            self.states[tooltip] = { lines = tooltip:NumLines(), bodyWidth = width, bodyHeight = height }
        end
    end)
    tooltip:HookScript("OnTooltipCleared", function() self.states[tooltip] = nil end)
    tooltip:HookScript("OnShow", function() self:Apply(tooltip) end)
    tooltip:HookScript("OnSizeChanged", function() self:Apply(tooltip) end)
    -- Show also refreshes layout on an already-visible tooltip (no OnShow event).
    hooksecurefunc(tooltip, "Show", function() self:Apply(tooltip) end)
end

function feature:Trim(manager, primary)
    if not self.running or not manager.compareInfo or not accessible(manager.compareInfo) then return end
    local info, methods = manager.compareInfo, Enum.TooltipComparisonMethod
    if not info or not info.additionalItems then return end
    -- Preserve paired-item explanations and cycling hints unless separately proven.
    if info.method ~= methods.Single and info.method ~= methods.WithBothHands then return end
    if not primary and info.method ~= methods.Single then return end
    if #info.additionalItems > 1 and GetCVarBool("allowCompareWithToggle") then return end
    local index = primary and 1 or 2
    local tooltip = manager.tooltip and manager.tooltip.shoppingTooltips[index]
    local state = self.states[tooltip]
    if not state or not safe(tooltip) then return end
    local displayed = primary and info.item or info.additionalItems[manager.comparisonIndex or 1]
    local partner = info.method ~= methods.Single and info.additionalItems[manager.comparisonIndex or 1] or nil
    if not displayed or not accessible(displayed) or not accessible(manager.comparisonItem) then return end
    local delta = C_TooltipComparison.GetItemComparisonDelta(manager.comparisonItem, displayed, partner, false)
    if not delta or not accessible(delta) or #delta == 0 then return end
    local last = state.lines + 2 + #delta
    if tooltip:NumLines() ~= last then return end -- Additional annotations must survive.
    local header = primary and info.method == methods.WithBothHands
        and ITEM_DELTA_MULTIPLE_COMPARISON_DESCRIPTION or ITEM_DELTA_DESCRIPTION
    local intro = region(tooltip, "Left", state.lines + 2)
    if not intro or not public(intro:GetText()) or intro:GetText() ~= header then return end
    for i, text in ipairs(delta) do
        local font = region(tooltip, "Left", state.lines + 2 + i)
        if not public(text) or not font or not public(font:GetText()) or font:GetText() ~= text then return end
    end
    local regions = {}
    for line = state.lines + 1, last do
        local right = region(tooltip, "Right", line)
        local rightText = right and right:GetText()
        local rightShown = right and right:IsShown()
        if not public(rightShown) or (rightShown and (not public(rightText) or (rightText and rightText ~= ""))) then return end
        if line == state.lines + 1 then
            local blank = region(tooltip, "Left", line)
            local text = blank and blank:GetText()
            if not public(text) or (text and text ~= "" and text ~= " ") then return end
        end
        for _, side in ipairs({ "Left", "Right" }) do
            local font = region(tooltip, side, line)
            if font then
                local shown = font:IsShown()
                if not public(shown) then return end
                regions[#regions + 1] = { region = font, shown = shown }
            end
        end
    end
    state.first, state.last, state.regions = state.lines + 1, last, regions
    self:Apply(tooltip)
end

function feature:Enable()
    self.running = true
    if self.registered then return end
    self.registered = true
    self:Watch(ShoppingTooltip1); self:Watch(ShoppingTooltip2)
    hooksecurefunc(TooltipComparisonManager, "Initialize", function(_, owner)
        for _, tooltip in ipairs(owner.shoppingTooltips or {}) do self:Watch(tooltip) end
    end)
    hooksecurefunc(TooltipComparisonManager, "SetItemTooltip", function(manager, primary) self:Trim(manager, primary) end)
end

function feature:Disable()
    self.running, self.writing = false, true
    for tooltip, state in pairs(self.states) do
        if state.trimmed and safe(tooltip) then
            for _, entry in ipairs(state.regions) do entry.region:SetShown(entry.shown) end
            tooltip:SetSize(state.fullWidth, state.fullHeight)
        end
    end
    self.writing = false
    self.states = {}
end

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Hide redundant comparison statistics", y,
        self.settings, "enabled", function() Toolkit:RefreshFeatures() end,
        "Keep equipped-item information and side-by-side comparison; hide the duplicate stat footer.")
    return y - 72
end
function feature:RefreshSettings() self.checkbox:SetChecked(self.settings.enabled); self.checkbox:SetEnabled(self.available) end
Toolkit:RegisterFeature(feature)
