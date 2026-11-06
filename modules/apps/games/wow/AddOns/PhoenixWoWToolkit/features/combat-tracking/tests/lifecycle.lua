local root,T=assert(arg[1]),{}
assert(loadfile(root..'/features/combat-tracking/Model.lua'))('PWT',T)
local M=T.CombatTracking
local builds,stops,handler=0,0
local function display() return {root={Show=function() end},containers={}} end
M.Display={Available=function() return true end,
 Bars=function(config) builds=builds+1; assert(config.bars); return display() end,
 Nameplate=function() builds=builds+1; return display() end,
 Stop=function(d) if d then stops=stops+1 end end}
local combat,spec,class=false,104,'DRUID'
UnitClass=function() return 'Druid',class end
GetSpecialization=function() return 1 end
GetSpecializationInfo=function() return spec end
InCombatLockdown=function() return combat end
C_Spell={GetSpellInfo=function() return {name='A spell'} end}
CreateFrame=function() return {RegisterEvent=function() end,SetScript=function(_,_,fn) handler=fn end} end
SlashCmdList={}
local health={IsForbidden=function() return false end,IsProtected=function() return false end}
local plate={unitFrame={healthBar=health},IsForbidden=health.IsForbidden,IsProtected=health.IsProtected}
C_NamePlate={GetNamePlateForUnit=function() return plate end,GetNamePlates=function() return {} end}
function T:RegisterFeature(f) self.feature=f end
assert(loadfile(root..'/features/combat-tracking/Feature.lua'))('PWT',T)
local F=T.feature; F.settings={enabled=true}
assert(F:GetAvailability())
class='MAGE'; assert(not F:GetAvailability()); class='DRUID'
F:Enable(); assert(builds==1)
handler(nil,'SPELLS_CHANGED'); assert(builds==1,'Unchanged events must not allocate more displays')
plate.unitFrame.healthBar=nil; plate.unitFrame.Health=health -- Installed ElvUI contract.
F:AddPlate('nameplate1'); assert(builds==2)
F:RemovePlate('nameplate1'); F:AddPlate('nameplate2'); assert(builds==2,'Recycle plate displays')
combat=true; F.settings.global.width=300; F:RequestApply()
assert(F.pending and builds==2 and stops==1,'Combat edits must not rebuild or stop active displays')
combat=false; handler(nil,'PLAYER_REGEN_ENABLED')
assert(not F.pending and builds==3)
spec=103; handler(nil,'PLAYER_SPECIALIZATION_CHANGED','player')
assert(#F.config.bars==0)
F:Disable(); assert(not F.running)
local before=builds; F:AddPlate('nameplate3'); assert(builds==before)
F:Enable()
local saved=M.Key(F.settings)
SlashCmdList.PWTCOMBAT('test')
assert(F.testBars and M.Key(F.settings)==saved,'Reference test must not alter SavedVariables')
F:Disable(); assert(not F.testBars,'Disabling must also remove the reference display')
print('Combat Tracking lifecycle: class gate, spec changes, combat queue, plate reuse and disable passed')
