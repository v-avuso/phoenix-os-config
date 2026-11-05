local _, Toolkit = ...
local Style = {}; Style.__index = Style
Toolkit.TooltipStyle = Style
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local function safe(frame)
    return frame and not frame:IsForbidden() and not frame:IsProtected()
        and not (frame.IsAnchoringSecret and frame:IsAnchoringSecret())
end
local function tuple(object, method)
    if not object[method] then return end
    local r,g,b,a = object[method](object)
    if public(r) and public(g) and public(b) and public(a) and r then return {r,g,b,a} end
end
local unpack = unpack or table.unpack

function Style.New(adapter, settings)
    local self = setmetatable({adapter=adapter,settings=settings,states={}},Style)
    local renderer = adapter:Bind()
    if renderer then
        if renderer.Init then renderer:Init() end
        hooksecurefunc(renderer,"Show",function()
            self:Chrome(renderer,true)
            if Toolkit.CreaturePreview then
                Toolkit.CreaturePreview.Foreground(renderer,self.enabled)
                Toolkit.CreaturePreview.Overflow(renderer,self.enabled and self.settings.previewOverflow~=false)
            end
        end)
        hooksecurefunc(renderer,"LoadTheme",function()
            for _,state in pairs(self.states) do if state.view then state.view:LoadTheme() end end
            self:Chrome(renderer,true)
        end)
    end
    if TooltipComparisonManager and TooltipComparisonManager.AnchorShoppingTooltips then
        hooksecurefunc(TooltipComparisonManager,"AnchorShoppingTooltips",function() self:Place() end)
    end
    -- Install setter hooks before the first tooltip call (especially pet GUIDs
    -- not present in a generic tooltip-data snapshot).
    if GameTooltip then self:Observe(GameTooltip,nil) end
    return self
end

function Style:Restore(frame)
    local state = self.states[frame]
    if not state or not safe(frame) then return end
    if state.texture then state.texture:Hide() end
    if state.chrome then state.chrome:Hide() end
    if state.owned then
        state.owned=false -- Release before restoring: our post-hooks must be inert.
        for border,alpha in pairs(state.borders or {}) do if safe(border) then border:SetAlpha(alpha) end end
        if frame.NineSlice and state.nine ~= nil then frame.NineSlice:SetAlpha(state.nine) end
        if state.backdrop and frame.SetBackdrop then
            frame:SetBackdrop(state.backdrop)
            if state.color then frame:SetBackdropColor(unpack(state.color)) end
            if state.border then frame:SetBackdropBorderColor(unpack(state.border)) end
        end
        if frame.Background and state.background ~= nil then frame.Background:SetShown(state.background) end
        state.owned=false
    end
end

-- ElvUI's SetTemplate creates two separate border frames, outside SetBackdrop.
-- Suppress only those known skin surfaces; retain annotations and other children.
function Style:HideBorders(frame,state)
    self.borderWatched=self.borderWatched or {}
    for _,key in ipairs({"iborder","oborder"}) do
        local border=frame[key]
        if border and border.IsForbidden and border.IsProtected and border.GetAlpha and border.SetAlpha and safe(border) then
            local alpha=border:GetAlpha()
            if public(alpha) then
                if state.borders[border]==nil then state.borders[border]=alpha end
                if not self.borderWatched[border] then
                    self.borderWatched[border]=true
                    hooksecurefunc(border,"SetAlpha",function(_,value)
                        if state.owned and self.enabled and self.settings.framing=="dialogueUI" and not self.settingBorders
                            and public(value) and safe(border) then
                            state.borders[border]=value
                            self.settingBorders=true;border:SetAlpha(0);self.settingBorders=false
                        end
                    end)
                end
                self.settingBorders=true;border:SetAlpha(0);self.settingBorders=false
            end
        end
    end
end

function Style:Chrome(frame, original, nativeSource)
    if not safe(frame) then return end
    if not self.enabled then self:Restore(frame);return end
    local renderer = self.adapter.renderer
    if not renderer or not renderer.Background then return end
    local dialogue = self.enabled and self.settings.framing == "dialogueUI"
    if original and dialogue then self:Restore(frame); return end
    if not original and not dialogue then self:Restore(frame); return end
    local state=self.states[frame] or {}; self.states[frame]=state
    state.nativeSource=nativeSource or state.nativeSource
    if not state.owned then
        state.nine=frame.NineSlice and frame.NineSlice:GetAlpha()
        if not public(state.nine) then return end
        state.backdrop=frame.GetBackdrop and frame:GetBackdrop()
        state.color=tuple(frame,"GetBackdropColor"); state.border=tuple(frame,"GetBackdropBorderColor")
        state.background=frame.Background and frame.Background:IsShown()
        if not public(state.background) then return end
        state.borders={}
        state.owned=true
    end
    if not original then self:HideBorders(frame,state) end
    if frame.NineSlice then frame.NineSlice:SetAlpha(0) end
    if state.backdrop and frame.SetBackdrop then
        self.settingBackdrop=true;frame:SetBackdrop(nil);self.settingBackdrop=false
    end
    if original then
        if frame.Background then frame.Background:Hide() end
        if not state.chrome then
            state.chrome=CreateFrame("Frame",nil,frame,"BackdropTemplate")
            state.chrome:SetAllPoints(frame); state.chrome:EnableMouse(false)
            state.chrome:SetFrameLevel(math.max(0,frame:GetFrameLevel()-1))
        end
        local source=state.nativeSource or GameTooltip
        local native=self.states[source]
        local backdrop=native and native.backdrop or (source and source.GetBackdrop and source:GetBackdrop())
        state.chrome:SetBackdrop(backdrop or {bgFile="Interface\\Tooltips\\UI-Tooltip-Background",edgeFile="Interface\\Tooltips\\UI-Tooltip-Border",tile=true,tileSize=16,edgeSize=16,insets={left=4,right=4,top=4,bottom=4}})
        local color=native and native.color or (source and tuple(source,"GetBackdropColor"))
        if color then state.chrome:SetBackdropColor(unpack(color)) else state.chrome:SetBackdropColor(0.05,0.05,0.05,0.95) end
        local border=native and native.border or (source and tuple(source,"GetBackdropBorderColor"))
        if border then state.chrome:SetBackdropBorderColor(unpack(border)) end
        state.chrome:Show()
    else
        if not state.texture then state.texture=frame:CreateTexture(nil,"BACKGROUND",nil,7);state.texture:SetAllPoints(frame) end
        state.texture:SetTexture(renderer.Background:GetTexture())
        state.texture:SetTextureSliceMargins(32,32,32,32); state.texture:SetTextureSliceMode(1)
        state.texture:Show()
    end
end

function Style:Release(source)
    local state=self.states[source]
    if not state or not state.active then return end
    state.active=false
    if state.view then state.view:Hide() end
    self:Place()
    if safe(source) and state.alpha ~= nil then
        self.writing=true;source:SetAlpha(state.alpha);self.writing=false
    end
end

-- Chain comparison panes against the actual rendered neighbor. Native shopping
-- anchors describe smaller Blizzard panes and cannot space our wider text views.
function Style:Place()
    if self.placing or not GameTooltip then return end
    self.placing=true
    local main=self.states[GameTooltip]
    local primary=main and main.active and main.view or (self.adapter.lease and self.adapter.renderer or GameTooltip)
    if main and main.active and main.view then
        main.view:ClearAllPoints();main.view:SetPoint("TOPLEFT",GameTooltip,"TOPLEFT",0,0)
    end
    local edge=GameTooltip:GetLeft()
    if not public(edge) or not edge then self.placing=false;return end
    local sides={left={},right={}}
    for source,state in pairs(self.states) do
        if source~=GameTooltip and state.active and state.view and safe(source) then
            local left=source:GetLeft()
            if public(left) and left then
                local side=left<edge and sides.left or sides.right
                side[#side+1]={source=source,state=state,left=left}
            end
        end
    end
    for side,entries in pairs(sides) do
        table.sort(entries,function(a,b) if side=="left" then return a.left>b.left end;return a.left<b.left end)
        local previous=primary
        local scale=1
        -- Keep a wide multi-pane group inside the viewport rather than allowing
        -- independent screen clamping to push the outer pane onto its neighbor.
        if UIParent and UIParent.GetWidth and primary.GetEffectiveScale then
            local parentScale=UIParent:GetEffectiveScale()
            local boundary=side=="left" and primary:GetLeft() or primary:GetRight()
            if public(boundary) and boundary then
                local available=side=="left" and boundary*primary:GetEffectiveScale()
                    or UIParent:GetWidth()*parentScale-boundary*primary:GetEffectiveScale()
                local width=0
                for _,entry in ipairs(entries) do
                    local view=entry.state.view
                    width=width+view:GetWidth()*view:GetEffectiveScale()/view:GetScale()
                end
                if available>0 and width>0 then scale=math.min(1,available/width) end
            end
        end
        for _,entry in ipairs(entries) do
            local view=entry.state.view
            if view.SetScale then view:SetScale(scale) end
            view:ClearAllPoints()
            view:SetPoint(side=="left" and "TOPRIGHT" or "TOPLEFT",previous,
                side=="left" and "TOPLEFT" or "TOPRIGHT",0,0)
            previous=view
        end
    end
    self.placing=false
end

function Style:Refresh(source)
    if not safe(source) then return end
    self:Chrome(source,false)
    local state=self.states[source]
    if not state then return end
    if not self.enabled or self.settings.appearance~="dialogueUI" or not source:IsShown() or not state.data then
        self:Release(source); return
    end
    local creature=Toolkit.CreaturePreview and Toolkit.CreaturePreview.Resolve(state.data,state.hint,self.settings)
    local item=state.data.type==Enum.TooltipDataType.Item
    if (not item and not creature) or (source==GameTooltip and not creature) then self:Release(source);return end
    local candidate=item and Toolkit.ItemComparison.Candidate(state.data)
    local link=creature and creature.key or (candidate and Toolkit.ItemComparison.Link(candidate))
    if not public(link) or not link then self:Release(source);return end
    local policy=Toolkit.ComparisonVisibility
    local limit=policy and policy:BodyLineLimit(source)
    local data,signature=Toolkit.DialogueTooltip.Snapshot(source,state.data,link,limit)
    if not data then self:Release(source);return end
    if not state.view then
        state.view=Toolkit.DialogueTooltip.CreateBody()
        if state.view then state.view:HookScript("OnSizeChanged",function() self:Place() end) end
    end
    if not state.view then return end
    if not state.active or state.signature~=signature then
        local allowed=not source.CompareHeader or self.settings.equippedPreviews~=false
        local retained=allowed and state.view.usePreviewModel and state.view.hyperlink==link
        state.view.previewAllowed=allowed
        state.view.creaturePreview=creature
        if retained then state.view.usePreviewModel=false end
        state.view:ClearLines()
        state.view.hyperlink=link
        state.view.reusePreview=retained
        if source.CompareHeader and source.CompareHeader.Label then
            local text=source.CompareHeader.Label:GetText()
            if public(text) and text then state.view:AddLeftLine(text,1,0.82,0,false,nil,3) end
        end
        state.view:ProcessTooltipDataLines(data.lines,1)
        state.view:Show(true)
        state.view.reusePreview=nil
        state.signature=signature
    end
    if not state.active then
        local alpha=source:GetAlpha()
        if not public(alpha) then return end
        state.alpha=alpha;state.active=true
    end
    self:Chrome(state.view,true,source)
    if Toolkit.CreaturePreview then
        Toolkit.CreaturePreview.Foreground(state.view,true)
        Toolkit.CreaturePreview.Overflow(state.view,self.settings.previewOverflow~=false)
    end
    self:Place(source,state)
    self.writing=true;source:SetAlpha(0);self.writing=false
end

function Style:Observe(source,data)
    if not safe(source) then return end
    if not self.adapter.renderer then return end
    -- Hand item hovers back before the singleton samples native opacity. Two
    -- renderers must never acquire an already-masked source from one another.
    if public(data) and data and (not canaccessallvalues or canaccessallvalues(data))
        and source==GameTooltip and data.type==Enum.TooltipDataType.Item then self:Release(source) end
    local state=self.states[source] or {};self.states[source]=state
    if state.data~=data then state.hint=nil end
    state.data = public(data) and (not canaccessallvalues or canaccessallvalues(data)) and data or nil
    if not state.watched then
        state.watched=true
        local function queue()
            if state.queued then return end
            state.queued=true
            C_Timer.After(0,function() state.queued=false;self:Refresh(source) end)
        end
        state.queue=queue
        if source.SetBackdrop then
            hooksecurefunc(source,"SetBackdrop",function(_,info)
                if state.owned and self.enabled and self.settings.framing=="dialogueUI" and not self.settingBackdrop
                    and safe(source) and public(info) and (not info or not canaccessallvalues or canaccessallvalues(info)) then
                    state.backdrop=info
                    self:Chrome(source,false)
                end
            end)
        end
        for _,entry in ipairs({{"SetBackdropColor","color"},{"SetBackdropBorderColor","border"}}) do
            if source[entry[1]] then
                local method,key=entry[1],entry[2]
                hooksecurefunc(source,method,function()
                    if state.owned and safe(source) then
                        state[key]=tuple(source,method=="SetBackdropColor" and "GetBackdropColor" or "GetBackdropBorderColor")
                    end
                end)
            end
        end
        for _,entry in ipairs({{"SetCompanionPet","pet"},{"SetMountBySpellID","mount"}}) do
            local method,kind=entry[1],entry[2]
            if source[method] then
                hooksecurefunc(source,method,function(_,id)
                    if not safe(source) then return end
                    state.hint=public(id) and {kind=kind,id=id,data=state.data} or nil
                    queue()
                end)
            end
        end
        if source.SetAction and Toolkit.CreaturePreview then
            hooksecurefunc(source,"SetAction",function(_,slot)
                if not safe(source) then return end
                state.hint,self.actionTrace=Toolkit.CreaturePreview.ActionHint(slot,state.data,source)
                queue()
            end)
        end
        local function shown()
            if state.active and source:IsShown() then
                self.writing=true;source:SetAlpha(0);self.writing=false
            end
            queue()
        end
        hooksecurefunc(source,"Show",shown)
        hooksecurefunc(source,"SetShown",shown)
        source:HookScript("OnShow",shown)
        source:HookScript("OnHide",queue)
        source:HookScript("OnTooltipCleared",function() state.data=nil;state.hint=nil;queue() end)
        hooksecurefunc(source,"SetAlpha",function(_,alpha)
            if state.active and not self.writing then
                if not public(alpha) then self:Release(source);return end
                state.alpha=alpha;self.writing=true;source:SetAlpha(0);self.writing=false
            end
        end)
    end
    self:Chrome(source,false)
    state.queue() -- Data refreshes can occur while the frame remains shown.
end

function Style:Configure(enabled)
    self.enabled=enabled
    local sources={}
    for frame,state in pairs(self.states) do
        if state.watched then sources[#sources+1]=frame end
        self:Release(frame); self:Restore(frame)
        if state.view then
            self:Restore(state.view)
            if Toolkit.CreaturePreview then
                Toolkit.CreaturePreview.Foreground(state.view,false)
                Toolkit.CreaturePreview.Overflow(state.view,false)
            end
        end
    end
    if enabled then for _,source in ipairs(sources) do self:Refresh(source) end end
    if self.adapter.renderer then
        self:Chrome(self.adapter.renderer,true)
        if Toolkit.CreaturePreview then
            Toolkit.CreaturePreview.Foreground(self.adapter.renderer,enabled)
            Toolkit.CreaturePreview.Overflow(self.adapter.renderer,enabled and self.settings.previewOverflow~=false)
        end
    end
end
