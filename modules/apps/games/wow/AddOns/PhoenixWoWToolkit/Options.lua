local _, Toolkit = ...
Toolkit.Options = {}
local tabs = {"General", "Tooltip", "Combat", "Extensions"}
local function featureTab(feature)
    for _, name in ipairs(tabs) do if feature.optionsTab == name then return name end end
    return "General"
end

function Toolkit.Options.Text(panel, text, y, font)
    local label = panel:CreateFontString(nil, "ARTWORK", font or "GameFontHighlight")
    label:SetPoint("TOPLEFT", 16, y)
    label:SetPoint("RIGHT", panel, "RIGHT", -24, 0)
    label:SetJustifyH("LEFT")
    label:SetText(text)
    return label
end

function Toolkit.Options.Checkbox(panel, text, y, settings, key, onChanged, description)
    local checkbox = CreateFrame("CheckButton", nil, panel, "UICheckButtonTemplate")
    checkbox:SetPoint("TOPLEFT", 12, y)
    checkbox.Text:SetText(text)
    checkbox.Text:SetFontObject("GameFontHighlight")
    checkbox:SetChecked(settings[key])
    if description then
        local label = panel:CreateFontString(nil, "ARTWORK", "GameFontHighlightSmall")
        label:SetPoint("TOPLEFT", checkbox, "BOTTOMLEFT", 34, 2)
        label:SetPoint("RIGHT", panel, "RIGHT", -24, 0)
        label:SetJustifyH("LEFT")
        label:SetWordWrap(true)
        label:SetText(description)
    end
    checkbox:SetScript("OnClick", function(self)
        settings[key] = self:GetChecked()
        onChanged()
    end)
    return checkbox
end

function Toolkit:SelectOptionsTab(name)
    self.selectedOptionsTab = name
    for tab, content in pairs(self.contents or {}) do
        content:SetShown(tab == name)
        if self.tabButtons then
            local update = tab == name and PanelTemplates_SelectTab or PanelTemplates_DeselectTab
            update(self.tabButtons[tab])
        end
    end
    self.content = self.contents[name]
    self.scroll:SetScrollChild(self.content)
    self.scroll:SetVerticalScroll(0)
end

function Toolkit:BuildOptions()
    for _, content in pairs(self.contents or {}) do content:Hide() end
    self.contents = {}
    for _, tab in ipairs(tabs) do
        local content = CreateFrame("Frame", nil, self.scroll)
        self.contents[tab] = content
        content:SetSize(600, 1)
        local groups, order = {}, {}
        for _, feature in ipairs(self.features) do
            if featureTab(feature) == tab then
                local section = feature.section or feature.id
                if not groups[section] then groups[section] = {}; order[#order + 1] = section end
                table.insert(groups[section], feature)
            end
        end
        local y = -12
        for _, section in ipairs(order) do
            self.Options.Text(content, section, y, "GameFontNormalLarge")
            y = y - 28
            for _, feature in ipairs(groups[section]) do y = feature:RegisterSettings(content, y) end
            y = y - 20
        end
        if #order == 0 then
            self.Options.Text(content, "No options available yet.", y)
            y = y - 28
        end
        content:SetHeight(math.max(1, -y))
    end
    self:SelectOptionsTab(self.selectedOptionsTab or "General")
    self.optionsDirty = false
end

function Toolkit:CreateOptions()
    local panel = CreateFrame("Frame")
    self.Options.Text(panel, "Phoenix WoW Toolkit", -16, "GameFontNormalLarge")
    self.tabButtons = {}
    for index, name in ipairs(tabs) do
        local button = CreateFrame("Button", nil, panel, "PanelTabButtonTemplate")
        button:SetPoint("TOPLEFT", 16 + (index-1)*120, -44)
        button:SetText(name)
        PanelTemplates_TabResize(button,16)
        button:SetScript("OnEnter",nil)
        button:SetScript("OnLeave",nil)
        button:SetScript("OnClick", function() self:SelectOptionsTab(name) end)
        self.tabButtons[name] = button
    end
    self.scroll = CreateFrame("ScrollFrame", nil, panel, "UIPanelScrollFrameTemplate")
    self.scroll:SetPoint("TOPLEFT", 0, -80)
    self.scroll:SetPoint("BOTTOMRIGHT", -32, 16)
    local hasGeneral = false
    for _, feature in ipairs(self.features) do
        if featureTab(feature) == "General" then hasGeneral = true; break end
    end
    if not hasGeneral and #self.features > 0 then
        self.selectedOptionsTab = featureTab(self.features[1])
    end
    local function refresh()
        if self.optionsDirty then self:BuildOptions() end
        for _, feature in ipairs(self.features) do feature:RefreshSettings() end
    end
    self.optionsDirty = true
    panel.OnRefresh = refresh
    panel:SetScript("OnShow", refresh)
    self.category = Settings.RegisterCanvasLayoutCategory(panel, "Phoenix WoW Toolkit")
    Settings.RegisterAddOnCategory(self.category)
    refresh()
end
