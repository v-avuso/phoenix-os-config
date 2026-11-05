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
        hooksecurefunc(renderer,"Show",function() self:Chrome(renderer,true) end)
        hooksecurefunc(renderer,"LoadTheme",function()
            for _,state in pairs(self.states) do if state.view then state.view:LoadTheme() end end
            self:Chrome(renderer,true)
        end)
    end
    return self
end

function Style:Restore(frame)
    local state = self.states[frame]
    if not state or not safe(frame) then return end
    if state.texture then state.texture:Hide() end
    if state.chrome then state.chrome:Hide() end
    if state.owned then
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
        state.owned=true
    end
    if frame.NineSlice then frame.NineSlice:SetAlpha(0) end
    if state.backdrop and frame.SetBackdrop then frame:SetBackdrop(nil) end
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
    if safe(source) and state.alpha ~= nil then
        self.writing=true;source:SetAlpha(state.alpha);self.writing=false
    end
end

function Style:Place(source,state)
    if not state.view or not state.active then return end
    local anchor="TOPLEFT"
    if source.CompareHeader and GameTooltip then
        local left, edge=source:GetLeft(),GameTooltip:GetLeft()
        if public(left) and public(edge) and left and edge and left<edge then anchor="TOPRIGHT" end
    end
    state.view:ClearAllPoints();state.view:SetPoint(anchor,source,anchor,0,0)
end

function Style:Refresh(source)
    if not safe(source) then return end
    self:Chrome(source,false)
    local state=self.states[source]
    if not state then return end
    if not self.enabled or self.settings.appearance~="dialogueUI" or source==GameTooltip or not source:IsShown()
        or not state.data or state.data.type~=Enum.TooltipDataType.Item then self:Release(source); return end
    local candidate=Toolkit.ItemComparison.Candidate(state.data)
    local link=candidate and Toolkit.ItemComparison.Link(candidate)
    if not public(link) or not link then self:Release(source);return end
    local policy=Toolkit.ComparisonVisibility
    local limit=policy and policy:BodyLineLimit(source)
    local data,signature=Toolkit.DialogueTooltip.Snapshot(source,state.data,link,limit)
    if not data then self:Release(source);return end
    if not state.view then state.view=Toolkit.DialogueTooltip.CreateBody() end
    if not state.view then return end
    if not state.active or state.signature~=signature then
        state.view:ClearLines()
        if source.CompareHeader and source.CompareHeader.Label then
            local text=source.CompareHeader.Label:GetText()
            if public(text) and text then state.view:AddLeftLine(text,1,0.82,0,false,nil,3) end
        end
        state.view:ProcessTooltipDataLines(data.lines,1)
        state.view:Show(true)
        state.signature=signature
    end
    if not state.active then
        local alpha=source:GetAlpha()
        if not public(alpha) then return end
        state.alpha=alpha;state.active=true
    end
    self:Chrome(state.view,true,source)
    self:Place(source,state)
    self.writing=true;source:SetAlpha(0);self.writing=false
end

function Style:Observe(source,data)
    if not safe(source) then return end
    if not self.adapter.renderer then return end
    local state=self.states[source] or {};self.states[source]=state
    state.data = public(data) and (not canaccessallvalues or canaccessallvalues(data)) and data or nil
    if not state.watched then
        state.watched=true
        local function queue()
            if state.queued then return end
            state.queued=true
            C_Timer.After(0,function() state.queued=false;self:Refresh(source) end)
        end
        state.queue=queue
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
        source:HookScript("OnTooltipCleared",function() state.data=nil;queue() end)
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
        if state.view then self:Restore(state.view) end
    end
    if enabled then for _,source in ipairs(sources) do self:Refresh(source) end end
    if self.adapter.renderer then self:Chrome(self.adapter.renderer,true) end
end
