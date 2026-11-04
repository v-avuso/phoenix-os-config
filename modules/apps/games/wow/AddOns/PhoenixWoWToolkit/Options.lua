local _, Toolkit = ...
Toolkit.Options = {}

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

function Toolkit:BuildOptions()
    if self.content then self.content:Hide() end
    local content = CreateFrame("Frame", nil, self.scroll)
    self.content = content
    content:SetSize(600, 1)
    self.scroll:SetScrollChild(content)
    local groups, order = {}, {}
    for _, feature in ipairs(self.features) do
        local section = feature.section or feature.id
        if not groups[section] then groups[section] = {}; order[#order + 1] = section end
        table.insert(groups[section], feature)
    end
    local y = -12
    for _, section in ipairs(order) do
        self.Options.Text(content, section, y, "GameFontNormalLarge")
        y = y - 28
        for _, feature in ipairs(groups[section]) do y = feature:RegisterSettings(content, y) end
        y = y - 20
    end
    content:SetHeight(math.max(1, -y))
    self.optionsDirty = false
end

function Toolkit:CreateOptions()
    local panel = CreateFrame("Frame")
    self.Options.Text(panel, "Phoenix WoW Toolkit", -16, "GameFontNormalLarge")
    self.scroll = CreateFrame("ScrollFrame", nil, panel, "UIPanelScrollFrameTemplate")
    self.scroll:SetPoint("TOPLEFT", 0, -44)
    self.scroll:SetPoint("BOTTOMRIGHT", -32, 16)
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
