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
local layouts, rowSizes, messageHandler = 0,0,nil
local ace={Embed=function(_,target)
    function target:RegisterMessage(_,handler) messageHandler=handler end
    function target:UnregisterMessage() messageHandler=nil end
end}
LibStub=function(name) assert(name=='AceEvent-3.0'); return ace end
WoWProDB={profile={buttonbar=false}}
WoWPro={ButtonBar={IsShown=function() return shown end}, HideAndSeek=function(_,bar,key,value)
    assert(key=='buttonbar' and value==false and not combat)
    assert(bar==WoWPro.ButtonBar); calls=calls+1; shown=false
end, MainFrameLayout=function() layouts=layouts+1 end, RowSizeSet=function() rowSizes=rowSizes+1 end}
assert(loadfile(root..'/features/wowpro-button-bar/Feature.lua'))('PWT',T)
local f=T.feature; f.settings={enabled=true}
assert(f:GetAvailability())
f:Enable(); assert(calls==1 and not shown)
assert(layouts==1 and rowSizes==1,'Mirror WoW-Pro settings refresh even if the bar was already hidden')
assert(messageHandler, 'Subscribe to WoW-Pro guide-load notifications')
messageHandler(); timers[#timers].fn()
assert(calls==2 and layouts==2 and rowSizes==2, 'Refresh after guide initialization')
shown=true; WoWProDB.profile.buttonbar=true
for _,timer in ipairs(timers) do timer.fn() end
assert(calls==2 and shown, 'honor a later visible preference')
WoWProDB.profile.buttonbar=false; combat=true
events.handler(nil,'PLAYER_ENTERING_WORLD')
for _,timer in ipairs(timers) do timer.fn() end
assert(calls==2 and shown, 'defer protected changes during combat')
combat=false; events.handler(nil,'PLAYER_REGEN_ENABLED')
assert(calls==3 and not shown)
shown=true; f:Disable()
events.handler(nil,'PLAYER_ENTERING_WORLD')
for _,timer in ipairs(timers) do timer.fn() end
assert(calls==3 and shown and not messageHandler, 'disabled feature and old timers must be inert')
WoWPro=nil; assert(not f:GetAvailability())
print('WoW-Pro: saved preference, delayed startup, combat deferral and disable passed')
