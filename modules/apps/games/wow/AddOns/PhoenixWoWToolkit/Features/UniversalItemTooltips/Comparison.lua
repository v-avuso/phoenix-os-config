local _, Toolkit = ...
local Comparison = {}
Toolkit.ItemComparison = Comparison

local function public(value) return not (issecretvalue and issecretvalue(value)) end
local function accessible(value) return public(value) and (not canaccessallvalues or canaccessallvalues(value)) end
local function link(item)
    if not item or not accessible(item) then return end
    if public(item.hyperlink) and type(item.hyperlink) == "string" then return item.hyperlink end
    if public(item.guid) and item.guid and C_Item.GetItemLinkByGUID then return C_Item.GetItemLinkByGUID(item.guid) end
end
local function itemLevel(item, hyperlink)
    if public(item.overrideItemLevel) and type(item.overrideItemLevel) == "number" then return item.overrideItemLevel end
    if hyperlink and C_Item.GetDetailedItemLevelInfo then
        local level = C_Item.GetDetailedItemLevelInfo(hyperlink)
        if public(level) and type(level) == "number" then return level end
    end
end

function Comparison.Candidate(data)
    if not data or not accessible(data) or not public(data.overrideItemLevel) then return end
    if public(data.guid) and data.guid then
        return { guid = data.guid, overrideItemLevel = data.overrideItemLevel }
    elseif public(data.hyperlink) and type(data.hyperlink) == "string" and data.hyperlink ~= "" then
        return { hyperlink = data.hyperlink, overrideItemLevel = data.overrideItemLevel }
    end
end

function Comparison.Link(item) return link(item) end

function Comparison.Groups(data)
    local candidate = Comparison.Candidate(data)
    if not candidate then return {} end
    local candidateLink = link(candidate)
    if not public(candidateLink) or not candidateLink then return {} end
    -- Do not present character-sheet equipment as a proposed replacement.
    for slot = 1, 19 do
        local equippedLink = GetInventoryItemLink("player", slot)
        if public(equippedLink) and equippedLink == candidateLink then return {} end
    end
    local info = C_TooltipComparison.GetItemComparisonInfo(candidate)
    if not info or not accessible(info) or not info.item or not info.additionalItems then return {} end
    local methods, groups = Enum.TooltipComparisonMethod, {}
    local paired = info.method == methods.WithBagMainHandItem or info.method == methods.WithBagOffHandItem
    local function add(equipped, partner)
        local oldLink, pairedLink = link(equipped), link(partner)
        if not public(oldLink) or not oldLink or (partner and (not public(pairedLink) or not pairedLink)) then return end
        local delta = C_TooltipComparison.GetItemComparisonDelta(candidate, equipped, partner, paired)
        if not delta or not accessible(delta) then return end
        local rows = {}
        if info.method == methods.Single then
            local newLevel, oldLevel = itemLevel(candidate, candidateLink), itemLevel(equipped, oldLink)
            if newLevel and oldLevel and newLevel ~= oldLevel then
                local difference = newLevel - oldLevel
                rows[#rows + 1] = (difference > 0 and "|cff20ff20+" or "|cffff4040")
                    .. string.format("%g Item Level|r", difference)
            end
        end
        for _, row in ipairs(delta) do
            if not public(row) or type(row) ~= "string" then return end
            rows[#rows + 1] = row -- Preserve Blizzard's signs, localization and colors.
        end
        if #rows > 0 then groups[#groups + 1] = { equipped = oldLink, partner = pairedLink, paired = paired, rows = rows } end
    end
    if info.method == methods.Single then
        add(info.item)
        for _, item in ipairs(info.additionalItems) do add(item) end
    elseif info.method == methods.WithBothHands or paired then
        if info.additionalItems[1] then add(info.item, info.additionalItems[1]) end
    end -- Unknown methods get the native tooltip, without guessed arithmetic.
    return groups
end
