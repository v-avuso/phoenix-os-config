local _, Toolkit = ...
local feature = {
    id = "opieVisualDelay",
    section = "OPie Visual Delay",
    dependencies = { "OPie" },
    defaults = { enabled = true, delayMs = 50 },
}

local function milliseconds(value)
    value = tonumber(value)
    if not value or value ~= value then return 50 end
    return math.max(0, math.min(250, math.floor(value + 0.5)))
end

function feature:GetAvailability(dependencies)
    dependencies = dependencies or {
        opieLoaded = C_AddOns.IsAddOnLoaded("OPie"),
        opieVersion = C_AddOns.GetAddOnMetadata("OPie", "Version"),
    }
    if not dependencies.opieLoaded then return false, "OPie not loaded" end
    if dependencies.opieVersion ~= "8.10.2" then
        return false, "Unverified OPie version: " .. (dependencies.opieVersion or "unknown")
    end
    if not GetBuildInfo or select(4, GetBuildInfo()) ~= 120105 then
        return false, "Unverified Retail client interface"
    end
    self.view, self.reason = Toolkit.OPieDelay.Find()
    if self.view and self.gate then
        for _, key in ipairs({ "main", "proxy", "tip", "core" }) do
            if self.view[key] ~= self.gate.view[key] then return false, "Renderer replaced; reload required" end
        end
    end
    return self.view ~= nil, self.reason
end

function feature:Enable()
    self.settings.delayMs = milliseconds(self.settings.delayMs)
    if not self.gate then self.gate = Toolkit.OPieDelay.Bind(self.view) end
    self.gate:Configure(true, self.settings.delayMs)
end

function feature:Disable()
    if self.gate then self.gate:Configure(false, self.settings.delayMs) end
end

function feature:SetDelay(value)
    self.settings.delayMs = milliseconds(value)
    if self.gate then self.gate:Configure(self.active, self.settings.delayMs) end
    self:RefreshSettings()
end

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Enable visual delay", y,
        self.settings, "enabled", function()
            Toolkit:RefreshFeatures()
            self:RefreshSettings()
        end)
    Toolkit.Options.Text(panel, "Ring appearance delay (ms)", y - 40)
    local slider = CreateFrame("Slider", nil, panel, "OptionsSliderTemplate")
    self.slider = slider
    slider:SetPoint("TOPLEFT", 24, y - 68)
    slider:SetSize(240, 16)
    slider:SetMinMaxValues(0, 250)
    slider:SetValueStep(1)
    slider:SetObeyStepOnDrag(true)
    if slider.Low then slider.Low:SetText("0") end
    if slider.High then slider.High:SetText("250") end
    if slider.Text then slider.Text:SetText("") end
    slider:SetScript("OnValueChanged", function(_, value)
        if not self.refreshing then self:SetDelay(value) end
    end)
    local input = CreateFrame("EditBox", nil, panel, "InputBoxTemplate")
    self.input = input
    input:SetPoint("LEFT", slider, "RIGHT", 24, 0)
    input:SetSize(64, 24)
    input:SetAutoFocus(false)
    input:SetNumeric(true)
    input:SetMaxLetters(3)
    local function commit() self:SetDelay(input:GetText()) end
    input:SetScript("OnEnterPressed", function() commit(); input:ClearFocus() end)
    input:SetScript("OnEditFocusLost", commit)
    input:SetScript("OnEscapePressed", function() self:RefreshSettings(); input:ClearFocus() end)
    return y - 116
end

function feature:RefreshSettings()
    self.refreshing = true
    self.settings.delayMs = milliseconds(self.settings.delayMs)
    self.checkbox:SetChecked(self.settings.enabled)
    self.checkbox:SetEnabled(self.available)
    self.slider:SetValue(self.settings.delayMs)
    self.input:SetText(tostring(self.settings.delayMs))
    self.refreshing = false
end

Toolkit:RegisterFeature(feature)
