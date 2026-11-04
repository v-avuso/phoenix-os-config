local _, Toolkit = ...
local feature = {
    id = "objectiveTracker",
    section = "Objective Tracker",
    defaults = { enabled = true, hideGlobalHeader = true, hideSectionMinimizeButtons = true },
    elements = {},
    containers = {},
    headers = {},
}

function feature:GetAvailability()
    -- The feature waits for Blizzard's tracker instead of forcing its add-on to load.
    return true
end

local function canChange(object)
    if not InCombatLockdown() then return true end
    while object do
        if object.IsProtected and object:IsProtected() then return false end
        object = object.GetParent and object:GetParent()
    end
    return true
end

function feature:Enforce(entry)
    if not canChange(entry.object) then return end
    local suppress = self.running and self.settings[entry.key]
    local object = entry.object
    if suppress and not entry.captured then
        if entry.alpha then entry.restore = object:GetAlpha() else entry.restore = object:IsShown() end
        entry.captured = true
    end
    if not entry.captured then return end
    self.mutating = true
    if entry.alpha then
        if suppress then object:SetAlpha(0) else object:SetAlpha(entry.restore) end
    elseif suppress then
        object:Hide() -- Also removes the global button's clickable region.
    else
        object:SetShown(entry.restore)
    end
    self.mutating = false
    if not suppress then entry.captured = false end
end

function feature:Watch(object, key, alpha)
    if not object or self.elements[object] then return end
    local entry = { object = object, key = key, alpha = alpha }
    self.elements[object] = entry
    local function requested(value)
        if self.mutating or not entry.captured then return end
        -- Preserve the latest Blizzard/skin request, not a hard-coded alpha or Show().
        entry.restore = value
        self:Enforce(entry)
    end
    if alpha then
        hooksecurefunc(object, "SetAlpha", function(_, value) requested(value) end)
    else
        hooksecurefunc(object, "Show", function() requested(true) end)
        hooksecurefunc(object, "Hide", function() requested(false) end)
        hooksecurefunc(object, "SetShown", function(_, shown) requested(shown) end)
    end
end

function feature:ObserveContainer(container, visited)
    if not container or visited[container] then return end
    visited[container] = true
    if not self.containers[container] then
        self.containers[container] = true
        -- Post-hooks preserve Blizzard/skin methods and their input/collapse handlers.
        for _, method in ipairs({ "Update", "AddModule" }) do
            if type(container[method]) == "function" then
                hooksecurefunc(container, method, function() self:Apply() end)
            end
        end
        if container.HookScript then
            container:HookScript("OnShow", function() self:Apply() end)
        end
    end
    local function visit(module)
        if not module or module == ObjectiveTrackerFrame then return end
        local header = module.Header
        if header and header ~= ObjectiveTrackerFrame.Header then
            local button = header.MinimizeButton
            -- Custom modules may omit this control; don't guess at other buttons.
            if button and button.GetAlpha and button.SetAlpha then
                self:Watch(button, "hideSectionMinimizeButtons", true)
            end
        end
        if module.ForEachModule or module.modules or module.MODULES then
            self:ObserveContainer(module, visited)
        end
    end
    if type(container.ForEachModule) == "function" then
        container:ForEachModule(visit)
    else
        for _, module in pairs(container.modules or container.MODULES or {}) do visit(module) end
    end
end

function feature:Apply()
    if self.applying then return end
    self.applying = true
    local tracker = ObjectiveTrackerFrame
    if self.running and tracker then
        local header = tracker.Header
        if header then
            if not self.headers[header] then
                self.headers[header] = true
                -- Blizzard's dirty closure may retain Update from before our hook.
                -- That path still calls Header:Show() before laying out modules.
                hooksecurefunc(header, "Show", function() self:Apply() end)
            end
            for _, key in ipairs({ "Text", "Background", "MinimizeButton" }) do
                local element = header[key]
                if element and element.IsShown and element.Hide then
                    self:Watch(element, "hideGlobalHeader", false)
                end
            end
        end
        self:ObserveContainer(tracker, {})
    end
    -- Include detached/replaced controls so disabling also restores those we owned.
    for _, entry in pairs(self.elements) do self:Enforce(entry) end
    self.applying = false
end

function feature:Enable()
    self.running = true
    if not self.events then
        self.events = CreateFrame("Frame")
        for _, event in ipairs({ "ADDON_LOADED", "PLAYER_ENTERING_WORLD", "PLAYER_REGEN_ENABLED" }) do
            self.events:RegisterEvent(event)
        end
        self.events:SetScript("OnEvent", function() self:Apply() end)
    end
    self:Apply()
end

function feature:Disable()
    self.running = false
    self:Apply()
    -- Hooks remain inert; the combat-end event completes any protected restoration.
end

function feature:RegisterSettings(panel, y)
    self.globalCheckbox = Toolkit.Options.Checkbox(panel, "Hide Objective Tracker Global Header", y,
        self.settings, "hideGlobalHeader", function() self:Apply() end,
        "Hide All Objectives and its button; keep section headings and spacing.")
    self.sectionsCheckbox = Toolkit.Options.Checkbox(panel, "Hide Section Minimize Buttons", y - 64,
        self.settings, "hideSectionMinimizeButtons", function() self:Apply() end,
        "Keep section buttons clickable in their original positions while invisible.")
    return y - 128
end

function feature:RefreshSettings()
    self.globalCheckbox:SetChecked(self.settings.hideGlobalHeader)
    self.sectionsCheckbox:SetChecked(self.settings.hideSectionMinimizeButtons)
end

Toolkit:RegisterFeature(feature)
