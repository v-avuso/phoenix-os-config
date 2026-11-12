local _, Toolkit = ...
local forever = WOW_PROJECT_CAMELOT and WOW_PROJECT_ID == WOW_PROJECT_CAMELOT
local feature = {
    id = "opieVisualDelay",
    section = "OPie Visual Delay",
    dependencies = { "OPie" },
    defaults = { enabled = not forever, delayMs = 50, fadeMs = 100 },
}

local function milliseconds(value, fallback)
    value = tonumber(value)
    if not value or value ~= value then return fallback or 50 end
    return math.max(0, math.min(1000, math.floor(value + 0.5)))
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
    local interface = GetBuildInfo and select(4, GetBuildInfo())
    if interface ~= 120105 and interface ~= 16001 then
        return false, "Unverified client interface"
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
    self.settings.fadeMs = milliseconds(self.settings.fadeMs, 100)
    if not self.gate then self.gate = Toolkit.OPieDelay.Bind(self.view) end
    self.gate:Configure(true, self.settings.delayMs, self.settings.fadeMs)
end

function feature:Disable()
    if self.gate then self.gate:Configure(false, self.settings.delayMs, self.settings.fadeMs) end
end

function feature:SetDelay(value)
    self.settings.delayMs = milliseconds(value)
    if self.gate then self.gate:Configure(self.active, self.settings.delayMs, self.settings.fadeMs) end
    self:RefreshSettings()
end

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Enable visual delay", y,
        self.settings, "enabled", function()
            Toolkit:RefreshFeatures()
            self:RefreshSettings()
        end)
    local function timingControl(label, offset, key, fallback)
        Toolkit.Options.Text(panel, label, y + offset)
        local slider = CreateFrame("Slider", nil, panel, "OptionsSliderTemplate")
        slider:SetPoint("TOPLEFT", 24, y + offset - 28)
        slider:SetSize(240, 16)
        slider:SetMinMaxValues(0, 1000)
        slider:SetValueStep(1)
        slider:SetObeyStepOnDrag(true)
        if slider.Low then slider.Low:SetText("0") end
        if slider.High then slider.High:SetText("1000") end
        if slider.Text then slider.Text:SetText("") end
        local input = CreateFrame("EditBox", nil, panel, "InputBoxTemplate")
        input:SetPoint("LEFT", slider, "RIGHT", 24, 0)
        input:SetSize(64, 24)
        input:SetAutoFocus(false)
        input:SetNumeric(true)
        input:SetMaxLetters(4)
        local function update(value)
            self.settings[key] = milliseconds(value, fallback)
            if self.gate then self.gate:Configure(self.active, self.settings.delayMs, self.settings.fadeMs) end
            self:RefreshSettings()
        end
        slider:SetScript("OnValueChanged", function(_, value)
            if not self.refreshing then update(value) end
        end)
        local function commit() update(input:GetText()) end
        input:SetScript("OnEnterPressed", function() commit(); input:ClearFocus() end)
        input:SetScript("OnEditFocusLost", commit)
        input:SetScript("OnEscapePressed", function() self:RefreshSettings(); input:ClearFocus() end)
        return slider, input
    end
    self.slider, self.input = timingControl("Ring appearance delay (ms)", -40, "delayMs", 50)
    self.fadeSlider, self.fadeInput = timingControl("Fade-in duration (ms; 0 disables fade)", -120, "fadeMs", 100)
    return y - 196
end

function feature:RefreshSettings()
    self.refreshing = true
    self.settings.delayMs = milliseconds(self.settings.delayMs)
    self.settings.fadeMs = milliseconds(self.settings.fadeMs, 100)
    self.checkbox:SetChecked(self.settings.enabled)
    self.checkbox:SetEnabled(self.available)
    self.slider:SetValue(self.settings.delayMs)
    self.input:SetText(tostring(self.settings.delayMs))
    self.fadeSlider:SetValue(self.settings.fadeMs)
    self.fadeInput:SetText(tostring(self.settings.fadeMs))
    self.refreshing = false
end

Toolkit:RegisterFeature(feature)
