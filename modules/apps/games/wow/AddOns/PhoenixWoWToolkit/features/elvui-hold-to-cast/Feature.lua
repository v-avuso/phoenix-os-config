-- Adapted from ElvUI HoldToCastFix 1.9.0, MIT; see LICENSE in this directory.
local _, Toolkit = ...
local feature = {
    id = "elvuiHoldToCast", section = "ElvUI", optionsTab = "Extensions",
    defaults = { enabled = false }, dependencies = { "ElvUI", "HoldToCastFix" },
}
local main = CreateFrame("Frame", nil, UIParent, "SecureFrameTemplate")
local others = CreateFrame("Frame", nil, UIParent)
local state = CreateFrame("Frame", nil, UIParent, "SecureHandlerStateTemplate")
local events = CreateFrame("Frame")
local prefixes = { "ACTIONBUTTON", "MULTIACTIONBAR3BUTTON", "MULTIACTIONBAR4BUTTON",
    "MULTIACTIONBAR2BUTTON", "MULTIACTIONBAR1BUTTON", "MULTIACTIONBAR5BUTTON",
    "MULTIACTIONBAR6BUTTON", "MULTIACTIONBAR7BUTTON" }
local controllerEvents = { "UPDATE_BONUS_ACTIONBAR", "UPDATE_SHAPESHIFT_FORM", "UPDATE_OVERRIDE_ACTIONBAR" }
local addedEvents = {}
state:SetFrameRef("bindingFrame", main)
state:SetAttribute("_onstate-pwtpage", [[
    local page = tonumber(newstate)
    if not page or page <= 0 then
        local owner = self:GetFrameRef("bindingFrame")
        if owner then owner:ClearBindings() end
    end
    self:CallMethod("OnSecureStateChanged")
]])

local function pagingConditions()
    local conditions = "[overridebar] 0; [vehicleui] 0; [possessbar] 0; "
    local e = ElvUI and ElvUI[1]
    local paging = e and e.db and e.db.actionbar and e.db.actionbar.bar1 and e.db.actionbar.bar1.paging
    local custom = paging and paging[e.myclass]
    if custom and custom ~= "" then
        custom = custom:gsub("[\n\r]", ""):gsub("(%[([^%]]-)%])%s*(%d+)", function(bracket, inner, page)
            if inner:find("mod:") and not inner:find("bonusbar") and not inner:find("bar:")
                and not inner:find("shapeshift") and not inner:find("overridebar")
                and not inner:find("vehicleui") and not inner:find("possessbar") then
                return bracket .. " -" .. page
            end
        end)
        conditions = conditions .. custom .. " "
    end
    if GetTempShapeshiftBarIndex then
        local page = GetTempShapeshiftBarIndex()
        if type(page) == "number" then conditions = conditions .. "[shapeshift] " .. page .. "; " end
    end
    return conditions .. "[bar:2] 2; [bar:3] 3; [bar:4] 4; [bar:5] 5; [bar:6] 6; [bonusbar:5] 11; 1"
end

function feature:GetAvailability()
    if not C_AddOns or not C_AddOns.IsAddOnLoaded or not C_AddOns.IsAddOnLoaded("ElvUI") then return false end
    if C_AddOns.IsAddOnLoaded("HoldToCastFix") then return false end
    local e = ElvUI and ElvUI[1]
    return e and e.private and e.private.actionbar and e.private.actionbar.enable
        and not e.IsGamepadActive and type(e.GetModule) == "function"
end

function feature:Apply()
    if InCombatLockdown() then self.pending = true; return end
    self.pending = false
    if self.driver then UnregisterStateDriver(state, "pwtpage"); self.driver = false end
    ClearOverrideBindings(main)
    ClearOverrideBindings(others)
    local controller = _G.ActionBarController
    if not self.running then
        if controller then
            for event in pairs(addedEvents) do controller:UnregisterEvent(event) end
        end
        addedEvents = {}
        return
    end
    if controller and controller.IsEventRegistered then
        for _, event in ipairs(controllerEvents) do
            if not controller:IsEventRegistered(event) then
                controller:RegisterEvent(event)
                addedEvents[event] = true
            end
        end
    end
    for index, prefix in ipairs(prefixes) do
        local owner = index == 1 and main or others
        for i = 1, 12 do
            local command = prefix .. i
            for _, key in ipairs({GetBindingKey(command)}) do
                if key ~= "" then SetOverrideBinding(owner, true, key, command) end
            end
        end
    end
    self.paged = false
    self.driver = true
    RegisterStateDriver(state, "pwtpage", pagingConditions())
end

function state:OnSecureStateChanged()
    local page = tonumber(self:GetAttribute("state-pwtpage")) or 0
    if page <= 0 then
        feature.paged = true
    elseif feature.paged then
        feature.paged = false
        feature:Apply()
    end
end

function feature:Enable()
    self.running = true
    if not self.hooked then
        local module = ElvUI[1]:GetModule("ActionBars", true)
        if module and type(module.HandleBinds) == "function" then
            hooksecurefunc(module, "HandleBinds", function() if feature.running then feature:Apply() end end)
            self.hooked = true
        end
    end
    self:Apply()
end

function feature:Disable() self.running = false; self:Apply() end
events:RegisterEvent("PLAYER_REGEN_ENABLED")
events:RegisterEvent("PLAYER_ENTERING_WORLD")
events:SetScript("OnEvent", function(_, event)
    if event == "PLAYER_REGEN_ENABLED" and feature.pending then feature:Apply()
    elseif event == "PLAYER_ENTERING_WORLD" and feature.running then feature:Apply() end
end)

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, "Fix ElvUI hold-to-cast", y,
        self.settings, "enabled", function() Toolkit:RefreshFeatures() end,
        "Use Blizzard's press-and-hold casting on supported ElvUI bars.")
    return y - 64
end
function feature:RefreshSettings() self.checkbox:SetChecked(self.settings.enabled) end
Toolkit:RegisterFeature(feature)
