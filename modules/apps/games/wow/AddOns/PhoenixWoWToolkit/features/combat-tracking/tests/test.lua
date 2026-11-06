local root = assert(arg[1])
local T = {}
assert(loadfile(root..'/features/combat-tracking/Model.lua'))('PWT', T)
local M = T.CombatTracking
local function near(a,b) assert(math.abs(a-b)<0.00001) end
local r,g,b = M.HSV(0,1,1); near(r,1); near(g,0); near(b,0)
r,g,b = M.HSV(190,.75,.95); near(r,.2375); near(g,.83125); near(b,.95)
assert(M.NextHue({315}) == 135)
assert(M.NextHue({315,135}) == 45)
assert(M.ParseHex('#ff0080') == 'FF0080' and not M.ParseHex('oops'))
local db = {}; M.Initialize(db)
local guardian = M.Resolve(db,104)
assert(guardian.bars[1].effects[1].spellID == 102558)
assert(guardian.bars[1].effects[2].spellID == 1308176)
assert(guardian.bars[1].effects[1].hue==190 and guardian.bars[1].effects[2].hue==45)
assert(guardian.bars[1].width==65 and guardian.bars[1].height==6)
assert(guardian.bars[1].icon==false and guardian.bars[1].label==false)
assert(guardian.bars[1].anchorPlayer==true)
assert(#M.Resolve(db,103).bars == 0, 'Feral must not inherit Guardian bars')
db.global.width=300; db.druid.width=310; db.specs['104']={width=320}
assert(M.Resolve(db,104).width==320 and M.Resolve(db,102).width==310)
db.specs['104'].width=nil; assert(M.Resolve(db,104).width==310)
local effects = {{spellID=1,hue=315,enabled=true},{spellID=2,hue=190,enabled=true},
 {spellID=3,hue=45,enabled=true}}
local rules = M.Subsets(effects,db.palette)
assert(#rules==7 and #rules[7].effects==3)
for mask=0,7 do
 local last
 for _,rule in ipairs(rules) do
  local match=true
  for _,effect in ipairs(rule.effects) do
   local bit=2^(effect.spellID-1)
   if mask % (bit*2) < bit then match=false end
  end
  if match then last=rule end
 end
 if mask==0 then assert(not last) else
  local count=0; for i=0,2 do if mask % (2^(i+1))>=2^i then count=count+1 end end
  assert(#last.effects==count,'Most specific matching composite must cover simpler borders')
 end
end
local manual={spellID=9,enabled=true,hex='12ABEF',hue=10}
near(M.AssignedHue({hex='00FF00',hue=10},db.palette),120)
r,g,b=M.Color(manual,db.palette); near(r,18/255); near(g,171/255); near(b,239/255)
db.palette.saturation=.1
local rr,gg,bb=M.Color(manual,db.palette); near(r,rr); near(g,gg); near(b,bb)
guardian.bars[1].effects[1].spellID=1
assert(M.Resolve(db,104).bars[1].effects[1].spellID==102558,'Resolved config must not alias defaults')
print('Combat Tracking: palette, inheritance, independent defaults and all seven composites passed')
