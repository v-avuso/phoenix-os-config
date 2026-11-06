-- A compositor model, NOT a replacement for Blizzard's secure execution or GPU tests.
local root,T = assert(arg[1]),{}
assert(loadfile(root..'/features/combat-tracking/Model.lua'))('PWT',T)
local objects,active={},{}
local methods={}
local function object(parent,kind)
 local o=setmetatable({parent=parent,kind=kind,level=parent and parent.level or 0,shown=true},{__index=methods})
 objects[#objects+1]=o; return o
end
function methods:SetSize() end
function methods:SetWidth() end
function methods:SetHeight() end
function methods:SetPoint() end
function methods:SetAllPoints() end
function methods:SetFrameLevel(n) self.level=n end
function methods:GetFrameLevel() return self.level end
function methods:SetFrameStrata() end
function methods:GetFrameStrata() return 'MEDIUM' end
function methods:EnableMouse() end
function methods:SetFont() end
function methods:SetJustifyH() end
function methods:SetWordWrap() end
function methods:CreateTexture() return object(self,'texture') end
function methods:CreateFontString() return object(self,'text') end
function methods:SetColorTexture(...) self.color={...} end
function methods:SetStatusBarTexture() end
function methods:SetStatusBarColor() end
function methods:SetDurationBar(bar) self.duration=bar end
function methods:SetIcon() end
function methods:SetSpellName() end
function methods:Hide() self.shown=false end
function methods:SetUnit(unit) self.unit=unit end
function methods:SetEnabled(enabled) self.enabled=enabled end
function methods:AddAuraSlot(_,filter,options)
 local button=object(self,'slot'); button.effect=next(options.candidateFilters.includeSpellIDs)
 button.filter=filter; options.initializeFrame(button)
 self.button=button
end
UIParent=object(nil,'root'); STANDARD_TEXT_FONT='font'
CreateFrame=function(kind,_,parent) return object(parent,kind) end
C_AuraContainerUtil={ProcessCustomAuraButtonDurationBarOptions=function() end}
assert(loadfile(root..'/features/combat-tracking/Display.lua'))('PWT',T)
local M,D=T.CombatTracking,T.CombatTracking.Display
local db={}; M.Initialize(db)
local config=M.Resolve(db,104)
local display=D.Bars(config,db.palette,function() return true end)
assert(#display.containers==1 and display.slotCount==2,'Share one native event/parse owner per bar')
local function visible(o)
 if not o.shown then return false end
 if o.kind=='slot' and not active[o.effect] then return false end
 if o.kind=='AuraContainer' and not o.enabled then return false end
 return not o.parent or visible(o.parent)
end
local function top(kind)
 local found
 for _,o in ipairs(objects) do
  if o.kind==kind and visible(o) and (not found or found.level<o.level) then found=o end
 end
 return found
end
assert(not top('slot'))
active[1308176]=true; assert(top('slot').effect==1308176)
active[1308399]=true; assert(top('slot').effect==1308399)
active[1308399]=nil; assert(top('slot').effect==1308176,'Expiry reveals lower active bar')
active[1308176]=nil; assert(not top('slot'))
D.Stop(display)
config=M.Resolve(db,102)
local plates=D.Nameplate(UIParent,'nameplate1',config,db.palette,function() return true end)
assert(#plates.containers==4,'Two effects need two singleton slots and a two-slot AND chain')
local function topBorder()
 local found
 for _,o in ipairs(objects) do
  if o.kind=='texture' and o.parent.kind=='slot' and visible(o) then
   if not found or o.parent.level>found.parent.level then found=o end
  end
 end
 return found
end
assert(not topBorder())
active[164812]=true; local mf=topBorder(); assert(mf)
active[164815]=true; local combined=topBorder(); assert(combined and combined~=mf)
local r,g,b=M.Color(config.highlights[1],db.palette)
local rr,gg,bb=M.Color(config.highlights[2],db.palette)
assert(math.abs(combined.color[1]-(r+rr)/2)<.00001)
active[164812]=nil; assert(topBorder() and topBorder()~=combined)
active[164815]=nil; assert(not topBorder())
D.Stop(plates)
config.highlights[#config.highlights+1]={spellID=3,hue=45,enabled=true}
local three=D.Nameplate(UIParent,'nameplate1',config,db.palette,function() return true end)
assert(#three.containers==12,'Three effects require twelve fixed slots, not pooled permutations')
local ids={164812,164815,3}
for mask=0,7 do
 local sums,n={0,0,0},0
 for i,id in ipairs(ids) do
  active[id]=mask%2^i>=2^(i-1) or nil
  if active[id] then
   n=n+1
   local r,g,b=M.Color(config.highlights[i],db.palette)
   sums[1]=sums[1]+r; sums[2]=sums[2]+g; sums[3]=sums[3]+b
  end
 end
 local border=topBorder()
 if n==0 then assert(not border) else
  assert(border)
  for i=1,3 do assert(math.abs(border.color[i]-sums[i]/n)<.00001,'Incorrect three-effect composite') end
 end
end
D.Stop(three)
print('Combat Tracking compositor model: priority/fallback, hide-none and all two/three-effect subsets passed (not combat proof)')
