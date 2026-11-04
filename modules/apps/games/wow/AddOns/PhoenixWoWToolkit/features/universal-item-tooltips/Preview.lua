local _, Toolkit = ...
local Preview = {}
Toolkit.ItemPreview = Preview
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local WIDTH, HEIGHT = 96, 128

function Preview.Place(state, tooltip)
    if not state.preview or not state.link then return end
    -- A transparent child in reserved right padding, never an independently anchored window.
    state.preview:ClearAllPoints()
    state.preview:SetPoint("TOPRIGHT", tooltip, "TOPRIGHT", -10, -10)
end

local function loaded(state)
    if not state.link then return end
    local model = state.model
    if not state.held and state.loadedLink ~= state.link then
        state.loadedLink = state.link
        model:Undress()
        model:TryOn(state.link)
    end
    -- Applying a camera before SetUnit has finished loading is lost on model load.
    Model_ApplyUICamera(model, state.camera)
    model:SetAlpha(1)
end

function Preview.Show(state, tooltip, link)
    Preview.Hide(state)
    if AppearanceTooltipTooltip or not C_TransmogCollection or not C_TransmogCollection.GetItemInfo or not Model_ApplyUICamera
        or not tooltip.GetPadding or not tooltip.SetPadding then return end
    local id, _, _, slot = C_Item.GetItemInfoInstant(link)
    if not public(id) or not public(slot) or not id or not C_Item.IsDressableItemByID(id) then return end
    local appearance, source = C_TransmogCollection.GetItemInfo(link)
    if not public(appearance) or not public(source) or not appearance then return end
    local camera
    if source and C_TransmogCollection.GetAppearanceCameraIDBySource then
        camera = C_TransmogCollection.GetAppearanceCameraIDBySource(source)
    elseif C_TransmogCollection.GetAppearanceCameraID then
        camera = C_TransmogCollection.GetAppearanceCameraID(appearance)
    end
    -- No camera means no useful close-up. Keep the normal tooltip instead of an empty box.
    if not public(camera) or not camera or camera <= 0 then return end
    local right, bottom, left, top = tooltip:GetPadding()
    if not public(right) or not public(bottom) or not public(left) or not public(top) then return end
    if type(right) ~= "number" or type(bottom) ~= "number" then return end
    if not state.model then
        local model = CreateFrame("DressUpModel", nil, tooltip)
        model:SetSize(WIDTH, HEIGHT)
        model:SetAutoDress(false)
        model:EnableMouse(false)
        model:SetScript("OnModelLoaded", function() loaded(state) end)
        state.model, state.preview = model, model
    end
    local model = state.model
    state.link, state.camera, state.owner = link, camera, tooltip
    state.padding = { right, bottom, left, top }
    -- Native padding participates in normal tooltip sizing and comparison anchoring.
    tooltip:SetPadding(right + WIDTH + 12, bottom, left, top)
    state.held = slot == "INVTYPE_WEAPON" or slot == "INVTYPE_2HWEAPON" or slot == "INVTYPE_WEAPONMAINHAND"
        or slot == "INVTYPE_WEAPONOFFHAND" or slot == "INVTYPE_RANGED" or slot == "INVTYPE_RANGEDRIGHT"
        or slot == "INVTYPE_THROWN" or slot == "INVTYPE_HOLDABLE" or slot == "INVTYPE_SHIELD"
    model:SetAlpha(0)
    model:SetUseTransmogSkin(not state.held and slot ~= "INVTYPE_HEAD" and slot ~= "INVTYPE_HAND")
    model:Show()
    Preview.Place(state, tooltip)
    if state.held then
        model:SetItemAppearance(appearance)
    else
        -- Render the hovered armor's transmog surface instead of an undressed full player.
        model:SetUnit("player")
        model:Undress()
        model:TryOn(link)
    end
    local file = model:GetModelFileID()
    if public(file) and file and file ~= 0 then loaded(state) end
end

function Preview.Hide(state)
    state.link, state.loadedLink, state.camera = nil, nil, nil
    if state.preview then state.preview:Hide() end
    if state.padding then
        local right, bottom, left, top = state.owner:GetPadding()
        -- A later owner may have replaced padding; only remove our own reservation.
        if public(right) and right == state.padding[1] + WIDTH + 12
            and public(bottom) and public(left) and public(top) then
            state.owner:SetPadding(state.padding[1], bottom, left, top)
        end
        state.padding, state.owner = nil, nil
    end
end
