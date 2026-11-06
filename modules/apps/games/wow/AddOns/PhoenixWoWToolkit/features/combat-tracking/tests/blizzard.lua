-- Run against an explicit, unmodified Blizzard_AuraContainer source directory.
-- This checks Lua contracts, NOT the client's forbidden partitions/secret values.
local source=assert(arg[2],'Blizzard source directory required')
local function copy(t)
 if type(t)~='table' then return t end
 local result={}; for k,v in pairs(t) do result[k]=copy(v) end; return result
end
function CreateFromMixins(...)
 local result={}; for _,m in ipairs({...}) do for k,v in pairs(m) do result[k]=v end end; return result
end
securecopy=copy
function MergeTable(a,b) for k,v in pairs(b) do a[k]=v end end
EnumUtil={IsValid=function(enum,v) for _,x in pairs(enum) do if x==v then return true end end end}
AuraContainerSortMethod={Default=0}; AuraContainerSortDirection={Normal=0}
CustomAuraContainerSlotDefaultOptions={sortMethod=0,sortDirection=0}
AuraUtil={IsValidFilterString=function(s) return s=='HELPFUL' or s=='HARMFUL|PLAYER' end}
function assertsafe(v) return v end
function assertf(v,...) assert(v,string.format(...)); return v end
ManagedAuraContainerInboundMixin={}; ManagedAuraContainerPrivateMixin={}
AuraContainerFlowLayoutInboundMixin={}; AuraContainerFlowLayoutPrivateMixin={}
AnchorUtil={FlowLayoutMixin={}}
AuraContainerUtil={GetAuraSortComparator=function() return function() end end}
assert(loadfile(source..'/Blizzard_CustomAuraContainer.lua'))('Blizzard_AuraContainer',{})
local optionsSeen,registered
local c=setmetatable({}, {__index=CustomAuraContainerSharedMixin})
function c:HasAuraSlot() return false end
function c:CreateAuraSlotFrame(options)
 optionsSeen=options; local button={}; options.initializeFrame(button); return button
end
function c:RegisterAuraSlot(_,description) registered=description end
function c:UpdateEventRegistrations() end
function c:UpdateAllAuras() end
local initialized=false
c:AddAuraSlot('test','HELPFUL',{candidateFilters={includeSpellIDs={[1308176]=true}},
 initializeFrame=function() initialized=true end})
assert(initialized and registered.candidateFilters.includeSpellIDs[1308176])
assert(optionsSeen.sortMethod==0 and registered.auraFrame)
AuraButtonPrivateMixin={}
assert(loadfile(source..'/Blizzard_CustomAuraButton.lua'))('Blizzard_AuraContainer',{})
secretwrap=function(value) return value end
local b={auraShownAnimations={}}
function b:IsShown() return self.shown end
function b:SetShown(value) self.shown=value end
CustomAuraButtonPrivateMixin.ApplyVisibility(b,'player',{})
assert(b.shown)
CustomAuraButtonPrivateMixin.ApplyVisibility(b,'player',nil)
assert(not b.shown,'Native assignment clearing must hide slot and its descendants')
-- Exercise the exact identity filter shipped by Blizzard; no copied implementation.
local util=assert(io.open(source..'/Blizzard_AuraContainerUtil.lua')):read('*a')
for _,name in ipairs({'CanApplyIdentityCandidateFilters','DoesAuraPassCandidateFilters'}) do
 local start=assert(util:find('function AuraContainerUtil.'..name,1,true))
 local finish=assert(util:find('\nend',start+1,true))+3
 assert(load(util:sub(start,finish)))()
end
Enum={SecrecyLevel={NeverSecret=0}}
C_Secrets={GetSpellAuraSecrecy=function() return 1 end}
UnitIsPlayerControlledOrGroupMember=function(unit) return unit=='player' end
UnitCanAssist=function(_,unit) return unit=='player' end
local aura={spellId=164812,isHarmful=true}
assert(AuraContainerUtil.DoesAuraPassCandidateFilters('nameplate1',aura,{includeSpellIDs={[164812]=true}}))
assert(not AuraContainerUtil.DoesAuraPassCandidateFilters('nameplate1',aura,{includeSpellIDs={[164815]=true}}))
assert(not AuraContainerUtil.DoesAuraPassCandidateFilters('player',aura,{includeSpellIDs={[164812]=true}}))
print('Combat Tracking Blizzard source: slot options, native visibility and identity filtering passed (not combat proof)')
