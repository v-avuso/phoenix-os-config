local addonName, Toolkit = ...
Toolkit.apiVersion = 1
Toolkit.features, Toolkit.byID = {}, {}
_G.PhoenixWoWToolkit = Toolkit

function Toolkit:InitializeFeature(feature)
    local db = PhoenixWoWToolkitDB.features
    if type(db[feature.id]) ~= "table" then db[feature.id] = {} end
    feature.settings = db[feature.id]
    for key, value in pairs(feature.defaults) do
        if type(feature.settings[key]) ~= type(value) then feature.settings[key] = value end
    end
end

function Toolkit:RegisterFeature(feature)
    assert(type(feature.id) == "string" and not self.byID[feature.id], "Unique feature id required")
    self.features[#self.features + 1], self.byID[feature.id] = feature, feature
    if self.initialized then
        self:InitializeFeature(feature)
        self:RefreshFeatures()
        self.optionsDirty = true
    end
    return feature
end

function Toolkit:RefreshFeatures()
    for _, feature in ipairs(self.features) do
        local available, reason = feature:GetAvailability()
        feature.available, feature.reason = available, reason
        local wanted = available and feature.settings.enabled
        if wanted and not feature.active then
            feature:Enable()
            feature.active = true
        elseif not wanted and feature.active then
            feature:Disable()
            feature.active = false
        end
    end
end

local events = CreateFrame("Frame")
events:RegisterEvent("ADDON_LOADED")
events:RegisterEvent("PLAYER_LOGIN")
events:SetScript("OnEvent", function(_, event, loadedName)
    if event == "ADDON_LOADED" and loadedName == addonName then
        if type(PhoenixWoWToolkitDB) ~= "table" then PhoenixWoWToolkitDB = {} end
        if type(PhoenixWoWToolkitDB.features) ~= "table" then PhoenixWoWToolkitDB.features = {} end
        for _, feature in ipairs(Toolkit.features) do Toolkit:InitializeFeature(feature) end
        Toolkit.initialized = true
        Toolkit:RefreshFeatures()
        Toolkit:CreateOptions()
        SlashCmdList.PHOENIXWOWTOOLKIT = function() Settings.OpenToCategory(Toolkit.category:GetID()) end
        SLASH_PHOENIXWOWTOOLKIT1 = "/pwt"
    elseif Toolkit.initialized then
        local refresh = event == "PLAYER_LOGIN"
        for _, feature in ipairs(Toolkit.features) do
            for _, dependency in ipairs(feature.dependencies or {}) do
                if dependency == loadedName then refresh = true end
            end
        end
        if refresh then Toolkit:RefreshFeatures() end
    end
end)
