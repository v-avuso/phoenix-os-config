local _, Toolkit = ...
local feature = {
    id = "opieHideActive",
    section = "OPie Quick Actions",
    defaults = {enabled = true},
    dependencies = {"OPie"},
}

function feature:GetAvailability()
    return OPie and type(OPie.SetPhoenixHideActive) == "function" or false
end

function feature:Apply(enabled)
    if OPie:SetPhoenixHideActive(enabled) then return end
    if not self.combatWatcher then
        self.combatWatcher = CreateFrame("Frame")
        self.combatWatcher:SetScript("OnEvent", function(frame)
            frame:UnregisterEvent("PLAYER_REGEN_ENABLED")
            if self:GetAvailability() then self:Apply(self.settings.enabled) end
        end)
    end
    self.combatWatcher:RegisterEvent("PLAYER_REGEN_ENABLED")
end

function feature:Enable()
    self:Apply(true)
end

function feature:Disable()
    if self:GetAvailability() then self:Apply(false) end
end

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Enable hidden quick actions", y,
        self.settings, "enabled", function()
            Toolkit:RefreshFeatures()
            self:RefreshSettings()
        end, "Use slices marked hide-active when you release the ring binding at its center.")
    return y - 64
end

function feature:RefreshSettings()
    self.checkbox:SetChecked(self.settings.enabled)
    self.checkbox:SetEnabled(self.available)
end

Toolkit:RegisterFeature(feature)
