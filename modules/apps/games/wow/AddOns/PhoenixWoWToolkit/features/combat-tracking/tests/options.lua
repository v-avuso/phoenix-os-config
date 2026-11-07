local root,T=assert(arg[1]),{Options={}}
assert(loadfile(root..'/features/combat-tracking/Model.lua'))('PWT',T)
local M=T.CombatTracking
local F={settings={enabled=true},editScope='spec'}; M.feature=F
function F:Initialize() M.Initialize(self.settings) end
function F:Spec() return 104 end
function F:Class() return 'DRUID' end
UnitClass=function() return 'Druid','DRUID' end
function F:RequestApply() self.applied=true end
function T:RefreshFeatures() end
local widgets,lastLabel={},nil
local function widget(kind)
 local w={kind=kind,scripts={}}
 function w:SetSize() end
 function w:SetPoint() end
 function w:SetWidth() end
 function w:SetHeight() end
 function w:SetAutoFocus() end
 function w:SetColorTexture() end
 function w:SetText(text) self.text=text end
 function w:SetScript(name,fn) self.scripts[name]=fn end
 function w:ClearFocus() end
 function w:HighlightText() end
 function w:GetText() return self.text end
 function w:SetChecked(v) self.checked=v end
 function w:SetupMenu(fn) self.menu=fn end
 function w:OverrideText() end
 function w:CreateFontString()
  local label=widget('label')
  function label:SetText(text) self.text=text; lastLabel=text end
  return label
 end
 function w:CreateTexture() return widget('texture') end
 w.label=lastLabel; widgets[#widgets+1]=w
 return w
end
CreateFrame=function(kind) return widget(kind) end
function T.Options.Text(_,text) local w=widget('label'); w.text=text; return w end
function T.Options.Checkbox(_,text,_,settings,key,changed)
 local w=widget('check'); w.text=text
 w.scripts.OnClick=function() settings[key]=not settings[key]; changed() end
 return w
end
C_Spell={GetSpellInfo=function(id) if id>0 and id<2000000 then return {name='Spell '..id} end end}
local panel=widget('panel')
T.scroll={GetVerticalScroll=function() return 500 end,SetVerticalScroll=function(_,v) assert(v==500) end}
function T:BuildOptions() widgets={}; F:RegisterSettings(panel,0) end
assert(loadfile(root..'/features/combat-tracking/Options.lua'))('PWT',T)
T:BuildOptions()
local function find(kind,text)
 for _,w in ipairs(widgets) do if w.kind==kind and (w.text==text or w.label==text) then return w end end
 error('Missing '..kind..': '..text)
end
local function enter(label,text)
 local w=find('EditBox',label); w.text=text; w.scripts.OnEnterPressed(w)
end
local function click(text) local w=find('Button',text); w.scripts.OnClick(w) end
enter('Width (40–1000) (inherited)','-5')
assert(F.settings.specs['104'].width==nil,'Reject out-of-range dimensions')
enter('Width (40–1000) (inherited)','321')
assert(F.settings.specs['104'].width==321)
enter('Hex override (blank = palette)','#123abc')
assert(F.settings.specs['104'].bars[1].effects[1].hex=='123ABC')
enter('Hue (0–359)','190')
assert(not F.settings.specs['104'].bars[1].effects[1].hex)
click('Add effect'); assert(#F.settings.specs['104'].bars[1].effects==3)
local old=F.settings.specs['104'].bars[1].effects[1].spellID
click('Down'); assert(F.settings.specs['104'].bars[1].effects[2].spellID==old)
click('Remove'); assert(#F.settings.specs['104'].bars[1].effects==2)
click('Add bar'); assert(#F.settings.specs['104'].bars==2)
click('Apply changes'); assert(F.applied)
click('Reset to inherited')
assert(next(F.settings.specs['104'])==nil)
assert(M.Resolve(F.settings,104).bars[1].effects[1].spellID==102558)
function F:Spec() return 62 end
function F:Class() return 'MAGE' end
UnitClass=function() return 'Mage','MAGE' end
T:BuildOptions()
find('check','Enable combat tracking (experimental)')
local labels={}
for _,w in ipairs(widgets) do
 if w.kind=='DropdownButton' then
  w.menu(nil,{CreateRadio=function(_,label) labels[label]=true end})
 end
end
assert(labels['Mage defaults'] and not labels['Druid defaults'],'Editor must follow the current class')
print('Combat Tracking editor: input validation, colors, list CRUD/reorder, apply and reset passed')
