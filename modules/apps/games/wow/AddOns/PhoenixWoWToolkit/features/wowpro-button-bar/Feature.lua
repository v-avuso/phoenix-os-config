local _, Toolkit = ...
local feature = {id = 'wowProButtonBar', section = 'WoW-Pro', optionsTab = 'Extensions',
    defaults = {enabled = true}, dependencies = {'WoWPro'}}

function feature:GetAvailability()
    return not not (WoWPro and type(WoWPro.HideAndSeek) == 'function')
end

function feature:Apply()
    if not self.running or InCombatLockdown() then return end
    local wp, db = _G.WoWPro, _G.WoWProDB
    local bar = wp and wp.ButtonBar
    if db and db.profile and db.profile.buttonbar == false and bar
        and type(wp.HideAndSeek) == 'function' then
        wp:HideAndSeek(bar, 'buttonbar', false)
        -- Match WoW-Pro's own settings callback, including its layout refresh.
        if type(wp.MainFrameLayout) == 'function' then wp.MainFrameLayout() end
        if type(wp.RowSizeSet) == 'function' then wp.RowSizeSet() end
    end
end

function feature:Schedule()
    self:Apply()
    -- WoW-Pro can initialize after PLAYER_ENTERING_WORLD while awaiting other add-ons.
    for _, delay in ipairs({2, 5}) do
        C_Timer.After(delay, function() self:Apply() end)
    end
end

local receiver = {}
function feature:Enable()
    self.running = true
    local ace = LibStub and LibStub('AceEvent-3.0', true)
    if ace and not self.listening then
        ace:Embed(receiver)
        receiver:RegisterMessage('WoWPro_PostLoadGuide', function()
            -- WoW-Pro completes its own layout after sending this message.
            C_Timer.After(0, function() feature:Apply() end)
        end)
        self.listening = true
    end
    self:Schedule()
end
function feature:Disable()
    self.running = false
    if self.listening then receiver:UnregisterMessage('WoWPro_PostLoadGuide'); self.listening = false end
end

local events = CreateFrame('Frame')
events:RegisterEvent('PLAYER_ENTERING_WORLD')
events:RegisterEvent('PLAYER_REGEN_ENABLED')
events:SetScript('OnEvent', function(_, event)
    if not feature.running then return end
    if event == 'PLAYER_ENTERING_WORLD' then feature:Schedule() else feature:Apply() end
end)

function feature:RegisterSettings(panel, y)
    self.checkbox = Toolkit.Options.Checkbox(panel, 'Fix hidden WoW-Pro button bar', y,
        self.settings, 'enabled', function() Toolkit:RefreshFeatures() end,
        'Keep the button bar hidden when it is disabled in WoW-Pro.')
    return y - 64
end
function feature:RefreshSettings()
    self.checkbox:SetChecked(self.settings.enabled)
    self.checkbox:SetEnabled(self.available)
end
Toolkit:RegisterFeature(feature)
