local _, Toolkit = ...
local Presentation = {}
local unpack = unpack or table.unpack
Toolkit.ItemPresentation = Presentation
local function public(value) return not (issecretvalue and issecretvalue(value)) end

-- Style the native content, rather than rebuilding it from a lossy list of item stats.
-- Per-region snapshots avoid changing shared Blizzard/ElvUI FontObjects.
function Presentation.Apply(state, tooltip)
    if not tooltip.GetLeftLine or not STANDARD_TEXT_FONT then return end
    state.fonts = state.fonts or {}
    for i = 1, tooltip:NumLines() do
        for _, side in ipairs({ "GetLeftLine", "GetRightLine" }) do
            local font = tooltip[side] and tooltip[side](tooltip, i)
            if font and font.GetFont and font.SetFont then
                local file, size, flags = font:GetFont()
                if public(file) and public(size) and public(flags) and file and size then
                    if not state.fonts[font] then state.fonts[font] = { file, size, flags } end
                    font:SetFont(STANDARD_TEXT_FONT, i == 1 and 16 or 14, "")
                end
            end
        end
    end
    if not state.background and tooltip.CreateTexture then
        state.background = tooltip:CreateTexture(nil, "BACKGROUND", nil, 7)
        state.background:SetAllPoints()
        state.background:SetTexture("Interface\\Tooltips\\UI-Tooltip-Background")
        state.background:SetVertexColor(0.06, 0.06, 0.06, 1)
    end
    if state.background then state.background:Show() end
    if tooltip.GetBackdropColor and tooltip.SetBackdropColor then
        if not state.backdrop then
            local r, g, b, a = tooltip:GetBackdropColor()
            if public(r) and public(g) and public(b) and public(a) and r and a then
                state.backdrop = { r, g, b, a }
            end
        end
        if state.backdrop then tooltip:SetBackdropColor(0.035, 0.035, 0.035, 1) end
    end
end

function Presentation.Restore(state, tooltip)
    for font, values in pairs(state.fonts or {}) do font:SetFont(unpack(values)) end
    state.fonts = nil
    if state.background then state.background:Hide() end
    if state.backdrop then tooltip:SetBackdropColor(unpack(state.backdrop)); state.backdrop = nil end
end
