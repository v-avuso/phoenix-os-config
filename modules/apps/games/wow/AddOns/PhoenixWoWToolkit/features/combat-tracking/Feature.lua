local _, Toolkit = ...
local M,D = Toolkit.CombatTracking,Toolkit.CombatTracking.Display
local feature = {id='combatTracking',section='Combat Tracking',defaults={enabled=true},
    dependencies={'Blizzard_AuraContainer','Plater','ElvUI','ElvUI_ToxiUI'}}
M.feature=feature
Toolkit:RegisterFeature(feature)

function feature:GetAvailability()
    local _,class=UnitClass('player')
    if class~='DRUID' then return false,'Druid only' end
    if not D.Available() then return false,'Requires the Retail 12.1 AuraContainer API' end
    return true
end

function feature:Spec()
    local getSpec=C_SpecializationInfo and C_SpecializationInfo.GetSpecialization or GetSpecialization
    local getInfo=C_SpecializationInfo and C_SpecializationInfo.GetSpecializationInfo or GetSpecializationInfo
    local index=getSpec()
    return index and getInfo(index) or 0
end

function feature:Initialize()
    M.Initialize(self.settings)
    self.plates=self.plates or {}
end

function feature:RequestApply()
    self.pending=true
    if not InCombatLockdown() then self:Apply() end
end

function feature:Apply()
    if InCombatLockdown() then self.pending=true; return end
    self:Initialize()
    local config=M.Resolve(self.settings,self:Spec())
    local key=M.Key({config,self.settings.palette,self.running==true})
    if key==self.appliedKey then self.pending=false; return end
    self.appliedKey=key
    D.Stop(self.bars); self.bars=nil
    for _,entry in pairs(self.plates) do D.Stop(entry.display) end
    self.plates={}
    self.pending=false
    self.config=config
    if not self.running then return end
    if self.config.barsEnabled then self.bars=D.Bars(self.config,self.settings.palette,M.ValidSpell) end
    if self.config.platesEnabled and C_NamePlate then
        for _,plate in ipairs(C_NamePlate.GetNamePlates()) do
            local unit=plate.namePlateUnitToken
            if unit then self:AddPlate(unit) end
        end
    end
end

local function usable(frame)
    return frame and not frame:IsForbidden() and not frame:IsProtected()
end

function feature:AddPlate(unit)
    if not self.running or not self.config or not self.config.platesEnabled then return end
    if not C_NamePlate then return end
    local plate=C_NamePlate.GetNamePlateForUnit(unit)
    if not usable(plate) then return end
    -- Plater documents unitFrame.healthBar. Blizzard uses UnitFrame.healthBar.
    -- No profile changes, aura hooks, or writes to the provider's health bar.
    local frame=plate.unitFrame or plate.UnitFrame
    local health=frame and (frame.healthBar or frame.HealthBarsContainer and frame.HealthBarsContainer.healthBar)
    if not usable(health) then return end
    local previous=self.plates[plate]
    if previous and previous.health==health then
        previous.unit=unit
        for _,c in ipairs(previous.display.containers) do c:SetUnit(unit); c:SetEnabled(true) end
        previous.display.root:Show()
        return
    end
    if previous then D.Stop(previous.display) end
    self.plates[plate]={unit=unit,health=health,
        display=D.Nameplate(health,unit,self.config,self.settings.palette,M.ValidSpell)}
end

function feature:RemovePlate(unit)
    for _,entry in pairs(self.plates or {}) do
        if entry.unit==unit then D.Stop(entry.display); entry.unit=nil end
    end
end

function feature:Enable()
    self.running=true; self:RequestApply()
end
function feature:Disable()
    self.running=false; self:RequestApply()
end

local events=CreateFrame('Frame')
for _,event in ipairs({'PLAYER_REGEN_ENABLED','PLAYER_SPECIALIZATION_CHANGED','PLAYER_ENTERING_WORLD',
    'SPELLS_CHANGED','TRAIT_CONFIG_UPDATED','NAME_PLATE_UNIT_ADDED','NAME_PLATE_UNIT_REMOVED'}) do
    events:RegisterEvent(event)
end
events:SetScript('OnEvent',function(_,event,unit)
    if not feature.settings then return end
    if event=='NAME_PLATE_UNIT_ADDED' then feature:AddPlate(unit)
    elseif event=='NAME_PLATE_UNIT_REMOVED' then feature:RemovePlate(unit)
    elseif event=='PLAYER_REGEN_ENABLED' then
        if feature.pending then feature:Apply() end
    elseif feature.running then feature:RequestApply() end
end)

SLASH_PWTCOMBAT1='/pwtcombat'
SlashCmdList.PWTCOMBAT=function()
    print('PWT combat: prototype-v1; spec='..tostring(feature:Spec())..'; active='..tostring(feature.running==true)
        ..'; pending='..tostring(feature.pending==true))
    local count,slots=0,feature.bars and feature.bars.slotCount or 0
    for _,entry in pairs(feature.plates or {}) do
        if entry.unit then count=count+1; slots=slots+entry.display.slotCount end
    end
    print('PWT combat: nameplates='..count..'; configured slots='..slots..'; no live aura values sampled')
end
