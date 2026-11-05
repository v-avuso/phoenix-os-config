local _, Toolkit = ...
local feature = { id = "comparisonCleanup", section = "Comparison Cleanup", defaults = { enabled = true, hideTarget = "equipped" },
    dependencies = { "Blizzard_SharedXMLGame" }, states = {}, watched = {} }
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local function accessible(value) return public(value) and (not canaccessallvalues or canaccessallvalues(value)) end
local function safe(tooltip)
    return tooltip and not tooltip:IsForbidden() and not tooltip:IsProtected()
        and not (tooltip.IsAnchoringSecret and tooltip:IsAnchoringSecret())
end
local function region(tooltip, side, index) return _G[tooltip:GetName() .. "Text" .. side .. index] end
local function stillMatches(tooltip,state)
    local count=tooltip:NumLines()
    if not public(count) or count~=state.last then return false end
    for _,entry in ipairs(state.regions or {}) do
        local font=entry.region
        local shown=font:IsShown()
        if not public(shown) then return false end
        local expected=state.expected and state.expected[font]
        if expected then
            local text=font:GetText()
            if not public(text) or text~=expected then return false end
        elseif shown and not entry.shown then
            local text=font:GetText()
            if not public(text) or (text and text~="") then return false end
        end
    end
    return true
end
Toolkit.ComparisonVisibility = feature
function feature:IsManaged() return self.settings and self.settings.enabled ~= false end
function feature:HidesHovered() return self:IsManaged() and (self.settings.hideTarget == "hovered" or self.settings.hideTarget == "both") end
function feature:HidesEquipped()
    local target = self.settings and self.settings.hideTarget or "equipped"
    return (not self.settings or self:IsManaged()) and (target == "equipped" or target == "both")
end
function feature:BodyLineLimit(tooltip)
    if not self:HidesEquipped() then return end
    local context = self.contexts and self.contexts[tooltip]
    if context then self:Trim(context.manager, context.primary) end
    local state = self.states[tooltip]
    if not self:HidesEquipped() or not state or not state.first or not safe(tooltip) then return end
    if not stillMatches(tooltip,state) then return end
    return state.lines
end

function feature:GetAvailability()
    return not not (TooltipComparisonManager and type(TooltipComparisonManager.SetItemTooltip) == "function"
        and type(TooltipComparisonManager.Initialize) == "function" and C_TooltipComparison
        and C_TooltipComparison.GetItemComparisonDelta and Enum and Enum.TooltipComparisonMethod)
end

-- Native frame dimensions can still describe the previous/full tooltip in a
-- ProcessInfo post-hook. Use the verified spacer's real line position instead.
local function measuredHeights(tooltip, state)
    local first = region(tooltip, "Left", 1)
    local spacer = region(tooltip, "Left", state.first)
    local last = region(tooltip, "Left", state.last)
    if not first or not spacer or not last or not first.GetTop or not spacer.GetTop or not last.GetBottom then return end
    local top, firstTop, spacerTop, lastBottom = tooltip:GetTop(), first:GetTop(), spacer:GetTop(), last:GetBottom()
    if not public(top) or not public(firstTop) or not public(spacerTop) or not public(lastBottom)
        or not top or not firstTop or not spacerTop or not lastBottom then return end
    local inset = top - firstTop
    if tooltip.GetPadding then
        local _, bottom, _, extraTop = tooltip:GetPadding()
        if not public(bottom) or not public(extraTop) then return end
        inset = inset + (bottom or 0) - (extraTop or 0)
    end
    if inset < 0 or firstTop < spacerTop or spacerTop < lastBottom then return end
    return top - spacerTop + inset, top - lastBottom + inset
end

function feature:Apply(tooltip)
    local state = self.states[tooltip]
    if self.writing or not self.running or not self:HidesEquipped() or not state or not state.first or not safe(tooltip) then return end
    local count = tooltip:NumLines()
    if not public(count) then return end
    local valid = stillMatches(tooltip,state)
    if not valid then
        if state.trimmed then
            self.writing = true
            for _, entry in ipairs(state.regions) do if entry.shown then entry.region:SetShown(true) end end
            local _, height = tooltip:GetSize()
            if public(height) and height == state.appliedHeight then tooltip:SetHeight(state.fullHeight) end
            self.writing = false
            state.trimmed = false
        end
        return
    end
    local width, height = tooltip:GetSize()
    if not public(width) or not public(height) then return end
    if not state.trimmed or height ~= state.appliedHeight then state.fullHeight = height end
    state.fullWidth = width
    local bodyHeight, fullHeight = measuredHeights(tooltip, state)
    if fullHeight then state.fullHeight = fullHeight end
    self.writing = true
    -- Recognition is sufficient to suppress the text: never wait for a size delta.
    for _, entry in ipairs(state.regions) do entry.region:Hide() end
    if bodyHeight then tooltip:SetHeight(bodyHeight); state.appliedHeight = bodyHeight end
    self.writing = false
    state.trimmed = true
    state.status = bodyHeight and "trimmed" or "footer hidden; awaiting line geometry"
    if state.index then self.trace[state.index] = "matched footer; " .. state.status end
end

function feature:Watch(tooltip)
    if not safe(tooltip) or self.watched[tooltip] or not tooltip.ProcessInfo then return end
    local name = tooltip:GetName()
    if not public(name) or type(name) ~= "string" then return end
    self.watched[tooltip] = true
    hooksecurefunc(tooltip, "ProcessInfo", function()
        if not self.running or not safe(tooltip) then return end
        local count = tooltip:NumLines()
        if public(count) then self.states[tooltip] = { lines = count } end
    end)
    tooltip:HookScript("OnTooltipCleared", function() self.states[tooltip] = nil end)
    tooltip:HookScript("OnShow", function() self:Apply(tooltip) end)
    tooltip:HookScript("OnSizeChanged", function() self:Apply(tooltip) end)
    -- Show also refreshes layout on an already-visible tooltip (no OnShow event).
    hooksecurefunc(tooltip, "Show", function() self:Apply(tooltip) end)
    hooksecurefunc(tooltip, "SetShown", function(_, shown) if public(shown) and shown then self:Apply(tooltip) end end)
end

function feature:Trim(manager, primary)
    self.trace = self.trace or {}
    local index = primary and 1 or 2
    local function note(reason) self.trace[index] = reason end
    if not self.running or not self:HidesEquipped() then note("equipped comparison visible by setting"); return end
    if not manager.compareInfo or not accessible(manager.compareInfo) then note("comparison data unavailable"); return end
    local info, methods = manager.compareInfo, Enum.TooltipComparisonMethod
    if not info or not info.additionalItems then note("additional-item data unavailable"); return end
    -- Preserve paired-item explanations and cycling hints unless separately proven.
    if info.method ~= methods.Single and info.method ~= methods.WithBothHands then note("paired/unknown method retained"); return end
    if not primary and info.method ~= methods.Single then note("combined secondary retained"); return end
    if #info.additionalItems > 1 and GetCVarBool("allowCompareWithToggle") then note("cycling hint retained"); return end
    local tooltip = manager.tooltip and manager.tooltip.shoppingTooltips[index]
    local state = self.states[tooltip]
    if not safe(tooltip) then note("tooltip restricted"); return end
    self.contexts = self.contexts or {}
    self.contexts[tooltip] = {manager=manager,primary=primary}
    if state and state.first and stillMatches(tooltip,state) then
        self:Apply(tooltip); note("matched footer; " .. (state.status or "layout pending")); return
    end
    local displayed = primary and info.item or info.additionalItems[manager.comparisonIndex or 1]
    local partner = info.method ~= methods.Single and info.additionalItems[manager.comparisonIndex or 1] or nil
    if not displayed or not accessible(displayed) or not accessible(manager.comparisonItem) then note("item data inaccessible"); return end
    local delta = C_TooltipComparison.GetItemComparisonDelta(manager.comparisonItem, displayed, partner, false)
    if not delta or not accessible(delta) or #delta == 0 then note("no accessible deltas"); return end
    local actual = tooltip:NumLines()
    if not public(actual) then note("line count restricted"); return end
    -- Match the exact API-generated suffix, not a ProcessInfo count: a later
    -- processing pass may already include the native comparison footer.
    local body = actual - 2 - #delta
    if body < 1 then note("comparison suffix missing"); return end
    local last = actual
    state = state or {}
    local header = primary and info.method == methods.WithBothHands
        and ITEM_DELTA_MULTIPLE_COMPARISON_DESCRIPTION or ITEM_DELTA_DESCRIPTION
    local intro = region(tooltip, "Left", body + 2)
    if not intro or not public(intro:GetText()) or intro:GetText() ~= header then note("header mismatch"); return end
    for i, text in ipairs(delta) do
        local font = region(tooltip, "Left", body + 2 + i)
        if not public(text) or not font or not public(font:GetText()) or font:GetText() ~= text then note("delta mismatch at row " .. i); return end
    end
    local regions = {}
    for line = body + 1, last do
        local right = region(tooltip, "Right", line)
        local rightText = right and right:GetText()
        local rightShown = right and right:IsShown()
        if not public(rightShown) or (rightShown and (not public(rightText) or (rightText and rightText ~= ""))) then note("right-column annotation or restricted value"); return end
        if line == body + 1 then
            local blank = region(tooltip, "Left", line)
            local text = blank and blank:GetText()
            if not public(text) or (text and text ~= "" and text ~= " ") then note("spacer mismatch"); return end
        end
        for _, side in ipairs({ "Left", "Right" }) do
            local font = region(tooltip, side, line)
            if font then
                local shown = font:IsShown()
                if not public(shown) then note("font visibility restricted"); return end
                regions[#regions + 1] = { region = font, shown = shown }
            end
        end
    end
    state.lines = body
    self.states[tooltip] = state
    state.first, state.last, state.regions, state.index = body + 1, last, regions, index
    state.expected = {}
    self.regionWatched = self.regionWatched or {}
    for _, entry in ipairs(regions) do
        local font = entry.region
        local text = font:GetText()
        if entry.shown and public(text) and text then state.expected[font] = text end
        if not self.regionWatched[font] then
            self.regionWatched[font] = true
            local observed = font
            local function reapply()
                local current = self.states[tooltip]
                if current and current.expected and current.expected[observed] then self:Apply(tooltip) end
            end
            if font.Show then hooksecurefunc(font, "Show", reapply) end
            if font.SetShown then hooksecurefunc(font, "SetShown", reapply) end
        end
    end
    self:Apply(tooltip)
    if C_Timer and C_Timer.After then
        C_Timer.After(0, function()
            if self.states[tooltip] == state then self:Apply(tooltip) end
        end)
    end
    note("matched footer; " .. (state.status or "layout not applied"))
end

function feature:Diagnostic()
    local lines = {
        "PWT comparison cleanup: enabled=" .. tostring(self.settings and self.settings.enabled)
            .. " available=" .. tostring(self:GetAvailability()) .. " running=" .. tostring(not not self.running),
        "Primary: " .. (self.trace and self.trace[1] or "no comparison hook observed"),
        "Secondary: " .. (self.trace and self.trace[2] or "no comparison hook observed"),
    }
    local owner = TooltipComparisonManager and TooltipComparisonManager.tooltip
    for index, tooltip in ipairs(owner and owner.shoppingTooltips or { ShoppingTooltip1, ShoppingTooltip2 }) do
        local state = self.states[tooltip]
        if safe(tooltip) and state and state.regions then
            local visible = 0
            for _, entry in ipairs(state.regions) do
                local shown = entry.region:IsShown()
                if not public(shown) then visible = nil; break end
                if entry.shown and shown then visible = visible + 1 end
            end
            lines[#lines + 1] = "Live comparison " .. index .. ": footer fonts shown="
                .. tostring(visible or "restricted") .. " (expected 0)"
        end
    end
    return lines
end

if SlashCmdList then
    SLASH_PWTCOMPARE1 = "/pwtcompare"
    SlashCmdList.PWTCOMPARE = function() for _, text in ipairs(feature:Diagnostic()) do print(text) end end
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
            for _, entry in ipairs(state.regions) do if entry.shown then entry.region:SetShown(true) end end
            tooltip:SetSize(state.fullWidth, state.fullHeight)
        end
    end
    self.writing = false
    self.states = {}
end

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Manage comparison statistics", y,
        self.settings, "enabled", function() Toolkit:RefreshFeatures() end,
        "Choose where replacement statistics appear, without a Shift comparison hint.")
    Toolkit.Options.Text(panel, "Hide comparison statistics", y - 64)
    local choices = { { "equipped", "In currently equipped item" }, { "hovered", "In hovered item" },
        { "both", "In both" }, { "neither", "In neither" } }
    self.dropdown = CreateFrame("DropdownButton", nil, panel, "WowStyle1DropdownTemplate")
    self.dropdown:SetPoint("TOPLEFT", 24, y - 90); self.dropdown:SetWidth(340)
    self.dropdown:SetupMenu(function(_, menu)
        for _, entry in ipairs(choices) do
            menu:CreateRadio(entry[2], function(value) return self.settings.hideTarget == value end,
                function(value)
                    self:Disable(); self.settings.hideTarget = value
                    Toolkit:RefreshFeatures()
                    if self.settings.enabled and self.available then self:Enable() end
                    local tooltips = Toolkit.byID and Toolkit.byID.universalItemTooltips
                    if tooltips then tooltips:RefreshOwned() end
                    self:RefreshSettings()
                end, entry[1])
        end
    end)
    self.choices = choices
    return y - 132
end
function feature:RefreshSettings()
    self.checkbox:SetChecked(self.settings.enabled); self.checkbox:SetEnabled(self.available)
    self.dropdown:SetEnabled(self.settings.enabled and self.available)
    for _, entry in ipairs(self.choices) do if entry[1] == self.settings.hideTarget then self.dropdown:OverrideText(entry[2]) end end
end
Toolkit:RegisterFeature(feature)
