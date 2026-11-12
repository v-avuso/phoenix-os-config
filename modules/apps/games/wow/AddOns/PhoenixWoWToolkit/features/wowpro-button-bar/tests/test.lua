local root = assert(arg[1])
local T = {Options={}}
function T:RegisterFeature(f) self.feature=f end
function T:RefreshFeatures() end
T.Options.Checkbox=function() return {SetChecked=function() end} end
local events, timers, combat = {}, {}, false
CreateFrame=function() return {RegisterEvent=function(_,e) events[e]=true end,
    SetScript=function(_,_,fn) events.handler=fn end} end
C_Timer={After=function(delay,fn) timers[#timers+1]={delay=delay,fn=fn} end}
InCombatLockdown=function() return combat end
local shown,calls = true,0
WoWProDB={profile={buttonbar=false}}
WoWPro={ButtonBar={IsShown=function() return shown end}, HideAndSeek=function(_,bar,key,value)
    assert(key=='buttonbar' and value==false and not combat)
    assert(bar==WoWPro.ButtonBar); calls=calls+1; shown=false
end}
assert(loadfile(root..'/features/wowpro-button-bar/Feature.lua'))('PWT',T)
local f=T.feature; f.settings={enabled=true}
assert(f:GetAvailability())
f:Enable(); assert(calls==1 and not shown)
shown=true; WoWProDB.profile.buttonbar=true
for _,timer in ipairs(timers) do timer.fn() end
assert(calls==1 and shown, 'honor a later visible preference')
WoWProDB.profile.buttonbar=false; combat=true
events.handler(nil,'PLAYER_ENTERING_WORLD')
for _,timer in ipairs(timers) do timer.fn() end
assert(calls==1 and shown, 'defer protected changes during combat')
combat=false; events.handler(nil,'PLAYER_REGEN_ENABLED')
assert(calls==2 and not shown)
shown=true; f:Disable()
events.handler(nil,'PLAYER_ENTERING_WORLD')
for _,timer in ipairs(timers) do timer.fn() end
assert(calls==2 and shown, 'disabled feature and old timers must be inert')
WoWPro=nil; assert(not f:GetAvailability())
print('WoW-Pro: saved preference, delayed startup, combat deferral and disable passed')
