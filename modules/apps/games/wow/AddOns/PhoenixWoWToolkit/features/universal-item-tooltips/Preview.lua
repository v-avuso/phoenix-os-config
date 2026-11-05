local _, Toolkit = ...
local Preview = {}
Toolkit.CreaturePreview = Preview
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local function accessible(value)
    return value and public(value) and (not canaccessallvalues or canaccessallvalues(value))
end

-- Read only native action metadata; never inspect or alter secure button attributes.
function Preview.ActionHint(slot, data, source)
    if not public(slot) or type(slot)~="number" then return nil,"restricted action slot" end
    local kind,id,subType
    if GetActionInfo then kind,id,subType=GetActionInfo(slot) end
    if not public(kind) or not public(id) or not public(subType) then return nil,"restricted action identity" end
    local spell
    if kind=="summonpet" and type(id)=="string" then return {kind="pet",id=id,data=data},"summonpet GUID" end
    if kind=="spell" or (kind=="macro" and subType=="spell") then spell=id
    elseif kind=="macro" and subType~="item" and type(id)=="number" and GetMacroSpell then spell=GetMacroSpell(id) end
    if (not public(spell) or type(spell)~="number") and source and source.GetSpell then
        local name
        name,spell=source:GetSpell()
    end
    if public(spell) and type(spell)=="number" and spell>0 then
        return {kind="mount",id=spell,data=data},tostring(kind).." -> spell "..spell
    end
    return nil,tostring(kind)..": no public summon identity"
end

-- The base renderer initializes model frames at its own level. Keep our visible
-- models above that content, reapplying after show; restore owned state on disable.
function Preview.Foreground(view, enabled)
    local preview=view and view.PreviewModel
    if not preview then return end
    local frames={view.PreviewFrame,preview.Model1,preview.ModelScene}
    for _,frame in ipairs(frames) do
        if frame:IsForbidden() or frame:IsProtected() then return end
    end
    if enabled then
        if not preview.foreground then
            preview.foreground={}
            for _,frame in ipairs(frames) do
                preview.foreground[frame]={strata=frame:GetFrameStrata(),level=frame:GetFrameLevel()}
            end
            preview.foreground.layer=preview.Model1:GetModelDrawLayer()
        end
        for _,frame in ipairs(frames) do
            frame:SetFrameStrata("TOOLTIP");frame:SetFrameLevel(view:GetFrameLevel()+5)
        end
        preview.Model1:SetModelDrawLayer("OVERLAY")
    elseif preview.foreground then
        for _,frame in ipairs(frames) do
            local original=preview.foreground[frame]
            frame:SetFrameStrata(original.strata);frame:SetFrameLevel(original.level)
        end
        preview.Model1:SetModelDrawLayer(preview.foreground.layer)
        preview.foreground=nil
    end
end

function Preview.Resolve(data, hint, settings)
    if not accessible(data) then return end
    local types=Enum.TooltipDataType
    if hint and hint.data~=data then hint=nil end
    local kind, id=hint and hint.kind, hint and hint.id
    if not kind then
        if data.type==types.Spell or data.type==types.Mount then kind,id="mount",data.id
        elseif types.CompanionPet and data.type==types.CompanionPet then kind,id="pet",data.guid end
    end
    if not public(id) or not id then return end
    local display, animation
    if kind=="mount" and settings.mountSpellPreviews~=false and C_MountJournal
        and C_MountJournal.GetMountFromSpell and C_MountJournal.GetMountInfoExtraByID then
        if type(id)~="number" then return end
        local mount=C_MountJournal.GetMountFromSpell(id)
        if not public(mount) or type(mount)~="number" or mount<=0 then return end
        local isSelf
        display, _, _, isSelf=C_MountJournal.GetMountInfoExtraByID(mount)
        if not public(isSelf) then return end
        animation=isSelf and 618 or 0
    elseif kind=="pet" and settings.petSummonPreviews~=false and C_PetJournal and C_PetJournal.GetPetInfoByPetID then
        if type(id)~="string" then return end
        local species, _, _, _, _, creature=C_PetJournal.GetPetInfoByPetID(id)
        if not public(species) or not species then return end
        display,animation=creature,0
    end
    if not public(display) or type(display)~="number" or display<=0 then return end
    return {display=display,animation=animation,key=kind..":"..tostring(id)..":"..display}
end

-- Data/identity adapter only: upstream owns the model, camera-light defaults,
-- idle animation synchronization and turntable implementation.
function Preview.Display(view, creature)
    local model=view.PreviewModel
    model:SetCameraID(nil)
    model:UseModelCenterToTransform(false)
    model:SetModelSize(view.modelHeight,view.modelHeight)
    model:ResetPosition()
    model:SetDisplayInfo(creature.display)
    model:SetAnimation(creature.animation)
    model:SetOffsetY(0.5)
    model:SetUseTurntable(true)
    view.usePreviewModel=true
    view.PreviewFrame:Show()
end

-- Enlarge only the physical clipping viewport. Insets retain the old projection
-- rectangle; logical width/height, layout space, model scale and camera stay intact.
-- Pixel-size preservation is an in-client acceptance check, not proven by Lua fakes.
function Preview.Overflow(view, enabled)
    local preview=view and view.PreviewModel
    local model=preview and preview.Model1
    if not model or not model.SetViewInsets then return end
    if model:IsForbidden() or model:IsProtected() then return end
    local creature=view.usePreviewModel and preview.width==preview.height and not model.cameraID
        and not preview.ModelScene:IsShown()
    if enabled and creature then
        if not preview.overflowAnchor then preview.overflowAnchor=CreateFrame("Frame",nil,view.PreviewFrame) end
        local anchor=preview.overflowAnchor
        anchor:SetSize(preview.width,preview.height)
        anchor:ClearAllPoints();anchor:SetPoint(preview.point,preview.relativeTo,preview.relativePoint,preview.x,preview.y)
        model:ClearAllPoints();model:SetPoint("CENTER",anchor,"CENTER",0,0)
        model:SetSize(preview.width*3,preview.height*3)
        model:SetViewInsets(preview.width,preview.width,preview.height,preview.height)
        preview.overflow=true
    elseif preview.overflow then
        model:SetSize(preview.width,preview.height)
        model:ClearAllPoints();model:SetPoint(preview.point,preview.relativeTo,preview.relativePoint,preview.x,preview.y)
        model:SetViewInsets(0,0,0,0)
        preview.overflow=nil
    end
end
