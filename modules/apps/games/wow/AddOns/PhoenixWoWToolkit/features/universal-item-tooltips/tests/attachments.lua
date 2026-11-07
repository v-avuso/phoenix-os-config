local root=assert(arg[1])
local T={}
local function frame(kind,parent)
    local f={kind=kind,parent=parent,alpha=1,ignore=false,points={},shown=false,level=2,strata='TOOLTIP',scripts={}}
    function f:IsForbidden() return self.forbidden or false end
    function f:IsProtected() return self.protected or false end
    function f:GetParent() return self.parent end
    function f:GetObjectType() return self.kind end
    function f:IsIgnoringParentAlpha() return self.ignore end
    function f:SetIgnoreParentAlpha(value) self.ignore=value end
    function f:GetFrameLevel() return self.level end
    function f:SetFrameLevel(value) self.level=value end
    function f:GetFrameStrata() return self.strata end
    function f:SetFrameStrata(value) self.strata=value end
    function f:SetPoint(...) self.points={...} end
    function f:GetPoint() return table.unpack(self.points) end
    function f:GetNumPoints() return #self.points>0 and 1 or 0 end
    function f:ClearAllPoints() self.points={} end
    function f:IsShown() return self.shown end
    function f:HookScript(event,fn) self.scripts[event]=fn end
    function f:Show() self.shown=true;if self.scripts.OnShow then self.scripts.OnShow(self) end end
    function f:Hide() self.shown=false end
    function f:GetEffectiveAlpha() return self.alpha*((self.parent and not self.ignore) and self.parent.alpha or 1) end
    return f
end
hooksecurefunc=function(object,name,callback)
    local original=object[name]
    object[name]=function(...) original(...);callback(...) end
end
assert(loadfile(root..'/features/universal-item-tooltips/Attachments.lua'))('PWT',T)
local source,view=frame('GameTooltip'),frame('Frame')
source.alpha=0;view.level=10
local extra=frame('GameTooltip',source)
extra:SetPoint('TOP',source,'BOTTOM',0,0)
local chained=frame('GameTooltip',source);chained:SetPoint('TOP',extra,'BOTTOM',0,0)
local unrelated=frame('Frame',source)
local forbidden=frame('GameTooltip',source);forbidden.forbidden=true
function source:GetChildren() return extra,chained,unrelated,forbidden end
local bridge=T.TooltipAttachments.New()
bridge:Follow(source,view)
extra:Show();chained:Show()
assert(chained.points[2]==extra and chained:GetEffectiveAlpha()==1,'preserve provider panel chains rather than overlapping attachments')
assert(extra:GetEffectiveAlpha()==1,'TSM-style attached panel survives native parent masking')
assert(extra.points[2]==view and extra.level>view.level,'panel follows rendered body, above its skin')
extra:Hide();assert(not extra:IsShown(),'provider keeps modifier visibility control')
extra:Show();bridge:Release()
assert(extra.points[2]==source,'modifier hide/show never captures our own anchor as provider intent')
bridge:Follow(source,view)
extra:SetPoint('BOTTOM',source,'TOP',0,0);extra:Show()
assert(extra.points[1]=='BOTTOM' and extra.points[2]==view,'provider top-side placement follows rendered view')
assert(not unrelated.ignore and not forbidden.ignore,'skip non-tooltips and inaccessible frames')
bridge:Release()
assert(not extra.ignore and extra.points[2]==source and extra.level==2,'disable restores parent-alpha, anchor and layering')
extra:SetPoint('TOP',source,'BOTTOM',0,0)
assert(extra.points[2]==source,'passive hooks inert after release')
bridge:Follow(source,view);extra:Show();bridge:Release()
assert(not extra.ignore,'repeated activations restore correctly')
print('Attached tooltip panels: inherited alpha, provider visibility, placement, repeated activation and restoration passed')
