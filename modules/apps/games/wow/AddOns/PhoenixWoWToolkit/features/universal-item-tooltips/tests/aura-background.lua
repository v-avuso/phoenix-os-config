local root=assert(arg[1]);local T={}
local function color(r,g,b,a) return {GetRGBA=function() return r,g,b,a end} end
CreateColor=color
hooksecurefunc=function(object,method,callback)
    local original=object[method]
    object[method]=function(...) original(...);callback(...) end
end
local calls,current=0
AuraContainerInbound={SetTooltipBackdrop=function(options) calls=calls+1;current=options end,
    SetTooltipTextureSlice=function(options) calls=calls+1;current=options end}
local original={backdropInfo={bgFile='provider-background'},centerColor=color(0.1,0.2,0.3,0.6)}
ElvUI={{GetModule=function() return {db={},SetAuraButtonTooltipStyle=function() AuraContainerInbound.SetTooltipBackdrop(original) end} end}}
assert(loadfile(root..'/features/universal-item-tooltips/AuraBackground.lua'))('PWT',T)
local aura=T.AuraTooltipBackground.New()
aura:Configure(true,95)
local r,g,b,a=current.centerColor:GetRGBA()
assert(r==0.1 and g==0.2 and b==0.3 and a==0.95 and current.backdropInfo==original.backdropInfo,
    'secure delegate preserves provider layout and RGB while applying opacity')
local _,_,_,oldAlpha=original.centerColor:GetRGBA();assert(oldAlpha==0.6,'never mutate provider options')
local texture={asset='provider-texture',color=color(0.5,0.6,0.7,0.4)}
AuraContainerInbound.SetTooltipTextureSlice(texture)
local _,_,_,alpha=current.color:GetRGBA();assert(alpha==0.95,'late provider style switch follows shared delegate')
aura:Configure(false,95);assert(current==texture,'disable restores latest provider style through delegate')
AuraContainerInbound.SetTooltipBackdrop(original);assert(current==original,'disabled hook is passive')
print('Aura background: native secure delegate, provider ownership, late styles and restoration passed (not client/combat proof)')
