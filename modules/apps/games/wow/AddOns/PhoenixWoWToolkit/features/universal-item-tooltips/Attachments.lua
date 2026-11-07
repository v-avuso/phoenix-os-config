local _, Toolkit = ...
local Attachments = {}; Attachments.__index = Attachments
Toolkit.TooltipAttachments = Attachments
local function safe(frame)
    return frame and not frame:IsForbidden() and not frame:IsProtected()
        and not (frame.IsAnchoringSecret and frame:IsAnchoringSecret())
end
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local unpack = unpack or table.unpack
function Attachments.New()
    return setmetatable({frames={}}, Attachments)
end
function Attachments:Apply(frame)
    local state=self.frames[frame]
    if self.writing or not self.view or not safe(frame) or not safe(self.view)
        or frame:GetParent()~=state.source then return end
    if not state.owned then
        local ignore=frame:IsIgnoringParentAlpha()
        if not public(ignore) then return end
        state.ignore, state.owned=ignore,true
        state.strata, state.level=frame:GetFrameStrata(),frame:GetFrameLevel()
    end
    self.writing=true
    frame:SetIgnoreParentAlpha(true)
    frame:SetFrameStrata(self.view:GetFrameStrata())
    frame:SetFrameLevel(self.view:GetFrameLevel()+5)
    if frame:IsShown() and state.point and state.point[2]==state.source then
        frame:ClearAllPoints()
        frame:SetPoint(state.point[1],self.view,state.point[3],state.point[4] or 0,state.point[5] or 0)
    end
    self.writing=false
end
function Attachments:Follow(source,view)
    self.view=view
    if not safe(source) or not source.GetChildren then return end
    for _,frame in ipairs({source:GetChildren()}) do
        if safe(frame) and frame.GetObjectType and frame:GetObjectType()=="GameTooltip"
            and frame.IsIgnoringParentAlpha and frame.SetIgnoreParentAlpha then
            local state=self.frames[frame]
            if not state then
                state={source=source};self.frames[frame]=state
                if self.onObserve then self.onObserve(frame) end
                local function capture()
                    if self.writing or not safe(frame) then return end
                    if frame:GetNumPoints()==1 then
                        local point={frame:GetPoint(1)}
                        for _,value in ipairs(point) do if not public(value) then return end end
                        if point[2]~=self.view then state.point=point end
                    end
                    self:Apply(frame)
                end
                frame:HookScript("OnShow",capture)
                hooksecurefunc(frame,"SetPoint",capture)
                capture()
            end
            self:Apply(frame)
        end
    end
end
function Attachments:Release()
    self.view=nil
    self.writing=true
    for frame,state in pairs(self.frames) do
        if state.owned and safe(frame) then
            frame:SetIgnoreParentAlpha(state.ignore)
            frame:SetFrameStrata(state.strata);frame:SetFrameLevel(state.level)
            if state.point then frame:ClearAllPoints();frame:SetPoint(unpack(state.point)) end
            state.owned=false
        end
    end
    self.writing=false
end
