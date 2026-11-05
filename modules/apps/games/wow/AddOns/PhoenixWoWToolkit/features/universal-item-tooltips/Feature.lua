local _, Toolkit = ...
local feature = { id = "universalItemTooltips", section = "Item Tooltips", defaults = { enabled = true, appearance = "dialogueUI", framing = "dialogueUI" },
    dependencies = { "Blizzard_SharedXMLGame", "DialogueUI" }, states = {} }
local appearances = {
    { "native", "Default" },
    { "dialogueUI", "Dialogue UI" },
}
local function safe(tooltip)
    return tooltip and not tooltip:IsForbidden() and not tooltip:IsProtected()
        and not (tooltip.IsAnchoringSecret and tooltip:IsAnchoringSecret())
end
local function accessible(data)
    return data and not (issecretvalue and issecretvalue(data))
        and (not canaccessallvalues or canaccessallvalues(data))
end

function feature:GetAvailability()
    return not not (TooltipDataProcessor and C_TooltipComparison and C_TooltipComparison.GetItemComparisonInfo
        and C_TooltipComparison.GetItemComparisonDelta and C_Item and C_Item.IsEquippableItem
        and Enum and Enum.TooltipComparisonMethod ~= nil)
end

function feature:Render(tooltip, data, force)
    if not self.running or self.settings.appearance ~= "dialogueUI" or not safe(tooltip) then
        if self.adapter.lease and self.adapter.lease.source == tooltip then self.adapter:Release() end
        return
    end
    if not accessible(data) or data.type ~= Enum.TooltipDataType.Item then self.adapter:Release(false, "native non-item/restricted data"); return end
    local candidate = Toolkit.ItemComparison.Candidate(data)
    local link = candidate and Toolkit.ItemComparison.Link(candidate)
    if not link or (issecretvalue and issecretvalue(link)) then
        self.adapter:Release(); return
    end
    self.adapter:Show(tooltip, data, link, force)
end

function feature:Process(tooltip, data)
    if not self.running or not safe(tooltip) then return end
    if tooltip.CompareHeader then return end
    local candidate = Toolkit.ItemComparison.Candidate(data)
    local link = candidate and Toolkit.ItemComparison.Link(candidate)
    if not link or (issecretvalue and issecretvalue(link)) then return end
    if self.settings.appearance == "dialogueUI" and tooltip == GameTooltip and self.adapter:Bind() then
        self.adapter:Watch(tooltip) -- Mirror after the final native Show, including later annotations.
        return
    end
    if Toolkit.ComparisonVisibility and Toolkit.ComparisonVisibility:HidesHovered() then return end
    local state = self.states[tooltip]
    if not state then
        state = {}; self.states[tooltip] = state
        local function clear() state.data = nil end
        tooltip:HookScript("OnTooltipCleared", clear)
        tooltip:HookScript("OnHide", clear)
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
end

function feature:RefreshOwned()
    if self.adapter then self.adapter:Release() end
    local tooltips = {}
    if GameTooltip then tooltips[GameTooltip] = true end
    for tooltip, state in pairs(self.states) do state.data = nil; tooltips[tooltip] = true end
    for tooltip in pairs(tooltips) do
        if safe(tooltip) and not InCombatLockdown() and tooltip:IsShown() and tooltip.RebuildFromTooltipInfo then
            tooltip:RebuildFromTooltipInfo()
        end
    end
end

function feature:Enable()
    -- Migrate the former imitation to the real renderer without losing the chosen intent.
    if self.settings.appearance ~= "native" then self.settings.appearance = "dialogueUI" end
    self.running = true
    self.settings.framing = self.settings.framing or "dialogueUI"
    if not self.adapter then
        self.adapter = Toolkit.DialogueTooltip.New()
        self.adapter.request = function(tooltip, data) self:Render(tooltip, data) end
    end
    if Toolkit.TooltipStyle and not self.style then self.style=Toolkit.TooltipStyle.New(self.adapter,self.settings) end
    if self.style then self.style:Configure(true) end
    if not self.registered then
        TooltipDataProcessor.AddTooltipPostCall(Enum.TooltipDataType.Item, function(tooltip, data) self:Process(tooltip, data) end)
        TooltipDataProcessor.AddTooltipPostCall(TooltipDataProcessor.AllTypes, function(tooltip, data)
            if self.style then self.style:Observe(tooltip,data) end
            self.adapter:RestorePending(tooltip)
            if self.adapter.lease and self.adapter.lease.source == tooltip
                and (not accessible(data) or data.type ~= Enum.TooltipDataType.Item) then
                self.adapter:Release(false, "native non-item/restricted data")
            end
        end)
        local events = CreateFrame("Frame")
        events:RegisterEvent("PLAYER_EQUIPMENT_CHANGED")
        events:RegisterEvent("PLAYER_REGEN_ENABLED")
        events:SetScript("OnEvent", function(_, event)
            for tooltip in pairs(self.adapter.pending) do self.adapter:RestorePending(tooltip) end
            local lease = self.adapter.lease
            if self.running and event == "PLAYER_EQUIPMENT_CHANGED" and lease then self:Render(lease.source, lease.data, true) end
        end)
        self.registered = true
    end
    self:RefreshOwned()
end

function feature:Disable() self.running = false; if self.style then self.style:Configure(false) end; self:RefreshOwned() end
function feature:SetAppearance(value)
    if value ~= "native" and value ~= "dialogueUI" then return end
    self.settings.appearance = value
    if self.style then self.style:Configure(self.running) end
    self:RefreshOwned()
    self:RefreshSettings()
end
function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Customize item tooltips", y,
        self.settings, "enabled", function() Toolkit:RefreshFeatures() end,
        "Choose framing and content styles independently.")
    Toolkit.Options.Text(panel, "Tooltip content style", y - 64)
    self.dropdown = CreateFrame("DropdownButton", nil, panel, "WowStyle1DropdownTemplate")
    self.dropdown:SetPoint("TOPLEFT", 24, y - 90)
    self.dropdown:SetWidth(340)
    self.dropdown:SetupMenu(function(_, menu)
        for _, entry in ipairs(appearances) do
            menu:CreateRadio(entry[2], function(value) return self.settings.appearance == value end,
                function(value) self:SetAppearance(value) end, entry[1])
        end
    end)
    Toolkit.Options.Text(panel,"Tooltip framing style",y-136)
    self.frameDropdown=CreateFrame("DropdownButton",nil,panel,"WowStyle1DropdownTemplate")
    self.frameDropdown:SetPoint("TOPLEFT",24,y-162);self.frameDropdown:SetWidth(340)
    self.frameDropdown:SetupMenu(function(_,menu)
        for _,entry in ipairs(appearances) do
            menu:CreateRadio(entry[2],function(value) return self.settings.framing==value end,
                function(value) self.settings.framing=value;if self.style then self.style:Configure(self.running) end;self:RefreshOwned();self:RefreshSettings() end,entry[1])
        end
    end)
    return y - 204
end
function feature:RefreshSettings()
    if not self.checkbox then return end
    self.checkbox:SetChecked(self.settings.enabled)
    self.checkbox:SetEnabled(self.available)
    self.dropdown:SetEnabled(self.settings.enabled and self.available)
    self.frameDropdown:SetEnabled(self.settings.enabled and self.available)
    for _, entry in ipairs(appearances) do
        if entry[1] == self.settings.appearance then self.dropdown:OverrideText(entry[2]) end
        if entry[1] == self.settings.framing then self.frameDropdown:OverrideText(entry[2]) end
    end
end
if SlashCmdList then
    SLASH_PWTTIP1 = "/pwttip"
    SlashCmdList.PWTTIP = function()
        local adapter = feature.adapter
        print("PWT tooltips: enabled=" .. tostring(feature.settings and feature.settings.enabled)
            .. " approach=" .. tostring(feature.settings and feature.settings.appearance))
        print("Dialogue UI: " .. (adapter and (adapter.reason or adapter.status) or "not initialized")
            .. "; active=" .. tostring(not not (adapter and adapter.lease)))
        if adapter then
            print("PWT renderer: renders=" .. adapter.renders .. " unchanged=" .. adapter.reuses
                .. " releases=" .. adapter.releases .. "; last=" .. (adapter.lastRelease or "none"))
            print("PWT last view: " .. (adapter.sample or "not sampled"))
        end
    end
end
Toolkit:RegisterFeature(feature)
