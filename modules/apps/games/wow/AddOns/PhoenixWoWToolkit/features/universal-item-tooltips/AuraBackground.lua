local _, Toolkit = ...
local Aura = {}; Aura.__index=Aura
Toolkit.AuraTooltipBackground=Aura
function Aura.New() return setmetatable({},Aura) end
function Aura:Apply()
    local native=self.native
    if not native then return end
    local options=native.options
    if self.enabled then
        local color=options[native.colorKey]
        if not color or not color.GetRGBA then return end
        local r,g,b=color:GetRGBA()
        if issecretvalue and (issecretvalue(r) or issecretvalue(g) or issecretvalue(b)) then return end
        local copy={};for key,value in pairs(options) do copy[key]=value end
        copy[native.colorKey]=CreateColor(r,g,b,self.opacity/100)
        options=copy
    end
    self.writing=true
    self.inbound[native.method](options)
    self.writing=false
end
function Aura:Configure(enabled,opacity)
    self.enabled=enabled;self.opacity=math.max(0,math.min(100,tonumber(opacity) or 95))
    local inbound=AuraContainerInbound
    if not inbound then return end
    if not self.inbound then
        self.inbound=inbound
        for _,entry in ipairs({{"SetTooltipBackdrop","centerColor"},{"SetTooltipNineSlice","centerColor"},{"SetTooltipTextureSlice","color"}}) do
            local method,colorKey=entry[1],entry[2]
            if inbound[method] then
                hooksecurefunc(inbound,method,function(options)
                    if self.writing or type(options)~="table"
                        or (issecretvalue and issecretvalue(options))
                        or (canaccessallvalues and not canaccessallvalues(options)) then return end
                    self.native={method=method,colorKey=colorKey,options=options}
                    if self.enabled then self:Apply() end
                end)
            end
        end
        -- Obtain the active provider's current style through its own entry point.
        -- Without a known baseline, leave the secure tooltip untouched.
        local engine=ElvUI and ElvUI[1]
        local provider=engine and engine.GetModule and engine:GetModule("Tooltip",true)
        if provider and provider.db and provider.SetAuraButtonTooltipStyle then provider:SetAuraButtonTooltipStyle() end
    end
    self:Apply()
end
