local _, Toolkit = ...
local Preview = {}
Toolkit.CreaturePreview = Preview
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local function accessible(value)
    return value and public(value) and (not canaccessallvalues or canaccessallvalues(value))
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
