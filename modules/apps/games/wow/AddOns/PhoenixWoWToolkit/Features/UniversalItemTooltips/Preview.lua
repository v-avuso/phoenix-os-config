local _, Toolkit = ...
local Preview = {}
Toolkit.ItemPreview = Preview

function Preview.Show(state, tooltip, link)
    if AppearanceTooltipTooltip then return end -- An installed preview owner wins.
    local id = C_Item.GetItemInfoInstant(link)
    if issecretvalue and issecretvalue(id) then return end
    if not id or not C_Item.IsDressableItemByID(id) then return end
    if not state.preview then
        local panel = CreateFrame("Frame", nil, tooltip, "BackdropTemplate")
        panel:SetSize(110, 150)
        panel:SetPoint("TOPLEFT", tooltip, "TOPRIGHT", 4, 0)
        panel:SetClampedToScreen(true)
        panel:EnableMouse(false)
        panel:SetBackdrop({ bgFile = "Interface\\Tooltips\\UI-Tooltip-Background", edgeFile = "Interface\\Tooltips\\UI-Tooltip-Border", tile = true, tileSize = 16, edgeSize = 16, insets = { left = 4, right = 4, top = 4, bottom = 4 } })
        panel:SetBackdropColor(0.04, 0.04, 0.06, 0.95)
        local model = CreateFrame("DressUpModel", nil, panel)
        model:SetPoint("TOPLEFT", 4, -4); model:SetPoint("BOTTOMRIGHT", -4, 4)
        model:SetAutoDress(false)
        model:EnableMouse(false)
        model:SetScript("OnModelLoaded", function()
            if state.link and state.loadedLink ~= state.link then
                state.loadedLink = state.link
                model:Undress(); model:TryOn(state.link)
            end
        end)
        state.preview, state.model = panel, model
    end
    state.link, state.loadedLink = link, nil
    state.model:SetUnit("player")
    state.model:Undress()
    state.model:TryOn(link)
    state.model:SetFacing(0.35)
    if C_TransmogCollection and Model_ApplyUICamera then
        local appearance = C_TransmogCollection.GetItemInfo(link)
        if issecretvalue and issecretvalue(appearance) then return end
        local camera = appearance and C_TransmogCollection.GetAppearanceCameraID(appearance)
        if not (issecretvalue and issecretvalue(camera)) and camera and camera > 0 then Model_ApplyUICamera(state.model, camera) end
    end
    state.preview:Show()
end

function Preview.Hide(state)
    state.link, state.loadedLink = nil, nil
    if state.preview then state.preview:Hide() end
end
