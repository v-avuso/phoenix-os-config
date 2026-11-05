local _, Toolkit = ...
local Dialogue = {}
Toolkit.DialogueTooltip = Dialogue
local Adapter = {}; Adapter.__index = Adapter
local required = { "ProcessInfo", "ProcessTooltipData", "ShowItemComparison", "DisplayModel", "ShowHotkey", "GetHyperlink", "SetQuestItem" }
local function public(value) return not (issecretvalue and issecretvalue(value)) end
local function accessible(value) return public(value) and (not canaccessallvalues or canaccessallvalues(value)) end
local function safe(frame)
    return frame and not frame:IsForbidden() and not frame:IsProtected()
        and not (frame.IsAnchoringSecret and frame:IsAnchoringSecret())
end

function Dialogue.Find(version)
    if version ~= "1.0.7" then return nil, "unverified version" end
    local found
    local frame = EnumerateFrames()
    while frame do
        if safe(frame) then
            local matches = true
            for _, name in ipairs(required) do
                local value = frame[name]
                if not public(value) or type(value) ~= "function" then matches = false; break end
            end
            if matches then
                if found then return nil, "ambiguous renderer" end
                found = frame
            end
        end
        frame = EnumerateFrames(frame)
    end
    if not found then return nil, "renderer not found" end
    return found
end

-- Mirror public rendered text, including other add-ons' additions, rather than
-- asking Dialogue UI to obtain a fresh body that omits native post-processors.
function Dialogue.Snapshot(source, data, link)
    if not safe(source) or not data or not accessible(data) or type(data.lines) ~= "table"
        or not accessible(data.lines) or not source.GetLeftLine then return end
    local lines, signature = {}, { link }
    local count = source:NumLines()
    if not public(count) or count == 0 then return end
    for i = 1, count do
        local row = { wrapText = true }
        for _, side in ipairs({ "Left", "Right" }) do
            local font = source["Get" .. side .. "Line"](source, i)
            if font then
                local shown = font:IsShown()
                if not public(shown) then return end
                if shown then
                    local text = font:GetText()
                    if not public(text) then return end
                    if text then
                        local r, g, b, a = font:GetTextColor()
                        if not public(r) or not public(g) or not public(b) or not public(a) then return end
                        local key = side == "Left" and "left" or "right"
                        row[key .. "Text"], row[key .. "Color"] = text, CreateColor(r, g, b, a)
                    end
                end
            end
        end
        row.leftText = row.leftText or " "
        lines[i] = row
    end
    -- Native processing supplies semantic lineIndex values: preserve coin rows
    -- without parsing localized sell-price text or guessing which row it occupies.
    for _, original in ipairs(data.lines) do
        if not accessible(original) then return end
        local index, price = original.lineIndex, original.price
        if not public(index) or not public(price) then return end
        if price and price > 0 and index and lines[index] then lines[index].price = price end
    end
    for _, row in ipairs(lines) do
        local r, g, b, rr, rg, rb
        if row.leftColor then r, g, b = row.leftColor:GetRGB() end
        if row.rightColor then rr, rg, rb = row.rightColor:GetRGB() end
        for _, value in ipairs({ row.leftText, row.rightText or "", r or 1, g or 1, b or 1,
            rr or 1, rg or 1, rb or 1, row.price or 0 }) do signature[#signature + 1] = tostring(value) end
    end
    return { type = Enum.TooltipDataType.Item, hyperlink = link, guid = data.guid, overrideItemLevel = data.overrideItemLevel,
        dataInstanceID = data.dataInstanceID, isItem = true, lines = lines }, table.concat(signature, "\0")
end

function Dialogue.New()
    return setmetatable({ watched = {}, pending = {}, renders = 0, reuses = 0, releases = 0 }, Adapter)
end

function Adapter:Sample(lease)
    if self.lease ~= lease then return end
    local function read(frame, method)
        if not safe(frame) or not frame[method] then return "n/a" end
        local value = frame[method](frame)
        return public(value) and tostring(value) or "restricted"
    end
    self.sample = "source shown=" .. read(lease.source, "IsShown") .. " alpha=" .. read(lease.source, "GetAlpha")
        .. "; renderer shown=" .. read(self.renderer, "IsShown") .. " alpha=" .. read(self.renderer, "GetAlpha")
        .. " effective=" .. read(self.renderer, "GetEffectiveAlpha")
        .. "; preview shown=" .. read(self.renderer and self.renderer.PreviewFrame, "IsShown")
end

function Adapter:RestorePending(source)
    local alpha = self.pending[source]
    if alpha and safe(source) then
        local current = source:GetAlpha()
        if not public(current) then return end
        self.pending[source] = nil
        if current == 0 then source:SetAlpha(alpha) end
    end
end

function Adapter:Mask()
    local lease = self.lease
    if not lease or not safe(lease.source) then return false end
    local alpha = lease.source:GetAlpha()
    if not public(alpha) then self:Release(true, "native alpha restricted"); return false end
    if alpha ~= 0 then
        lease.alpha = alpha
        self.writing = true; lease.source:SetAlpha(0); self.writing = false
    end
    return true
end

function Adapter:Release(skipNativeRestore, reason)
    local lease = self.lease
    if not lease then return end
    self:Sample(lease)
    self.releases, self.lastRelease = self.releases + 1, reason or "released"
    self.lease = nil
    if not skipNativeRestore then
        if safe(lease.source) then
            self.writing = true; lease.source:SetAlpha(lease.alpha); self.writing = false
        else self.pending[lease.source] = lease.alpha end
    end
    if safe(self.renderer) and public(self.renderer.owner) and public(self.renderer:GetHyperlink())
        and self.renderer.owner == lease.owner and self.renderer:GetHyperlink() == lease.link then
        self.writing = true; self.renderer:Hide(); self.writing = false
    end
end

function Adapter:Bind()
    local version = C_AddOns.IsAddOnLoaded("DialogueUI") and C_AddOns.GetAddOnMetadata("DialogueUI", "Version") or false
    if self.checked and self.version == version then return self.renderer end
    self:Release()
    self.checked, self.version = true, version
    local renderer, reason = Dialogue.Find(version)
    self.renderer, self.reason = renderer, reason
    if not renderer then return end
    -- 1.0.7's Show always dresses the model again, even for a text-only refresh.
    -- Reuse only our same-item preview; upstream/quest calls retain the original path.
    local displayModel = renderer.DisplayModel
    renderer.DisplayModel = function(view, ...)
        local lease = self.lease
        if self.rendering and not self.refreshModel and lease and lease.preview
            and view.owner == lease.owner and view:GetHyperlink() == lease.link
            and view.PreviewModel and not view.PreviewModel.hasModel then
            view.usePreviewModel = true
            view.PreviewFrame:Show()
            return
        end
        return displayModel(view, ...)
    end
    hooksecurefunc(renderer, "SetOwner", function()
        if self.lease and not self.writing then self:Release(false, "Dialogue UI owner changed") end
    end)
    renderer:HookScript("OnHide", function() if not self.writing then self:Release(false, "Dialogue UI hidden") end end)
    hooksecurefunc(renderer, "ProcessTooltipData", function()
        if self.rendering or (self.lease and renderer.owner == self.lease.owner) then
            -- The still-active native tooltip owns data updates and annotation refresh.
            renderer:UnregisterEvent("TOOLTIP_DATA_UPDATE")
        end
    end)
    hooksecurefunc(renderer, "Layout", function() if self.lease then self:Place() end end)
    if TooltipComparisonManager and TooltipComparisonManager.AnchorShoppingTooltips then
        hooksecurefunc(TooltipComparisonManager, "AnchorShoppingTooltips", function() if self.lease then self:Place() end end)
    end
    if DialogueUIAPI and DialogueUIAPI.AddItemTooltipProcessorExternal then
        DialogueUIAPI.AddItemTooltipProcessorExternal(function(actual)
            if actual ~= renderer then self.reason = "renderer identity changed"; self:Release() end
        end)
    end
    return renderer
end

function Adapter:Place()
    local lease = self.lease
    if not lease or not safe(lease.source) or not safe(self.renderer) then return end
    local source, anchor = lease.source, "TOPLEFT"
    local left, right = source:GetLeft(), source:GetRight()
    if not public(left) or not public(right) then self:Release(); return end
    for _, comparison in ipairs(source.shoppingTooltips or {}) do
        if safe(comparison) and comparison:IsShown() then
            local edge = comparison:GetLeft()
            if not public(edge) then self:Release(); return end
            if edge and right and edge >= right - 1 then anchor = "TOPRIGHT" end
        end
    end
    self.renderer:ClearAllPoints()
    self.renderer:SetPoint(anchor, source, anchor, 0, 0)
end

function Adapter:Watch(source)
    if self.watched[source] then return end
    self.watched[source] = true
    source:HookScript("OnHide", function()
        if self.lease and self.lease.source == source then self:Release(false, "native tooltip hidden") end
    end)
    source:HookScript("OnTooltipCleared", function()
        local lease = self.lease
        if lease and lease.source == source then
            local serial = self.serial
            C_Timer.After(0, function()
                if self.lease == lease and self.serial == serial then self:Release(false, "native clear without render") end
            end)
        end
    end)
    source:HookScript("OnSizeChanged", function() if self.lease and self.lease.source == source then self:Place() end end)
    hooksecurefunc(source, "SetAlpha", function(_, alpha)
        if not self.writing then self.pending[source] = nil end -- A new writer owns its intent.
        if not self.writing and self.lease and self.lease.source == source then
            if not public(alpha) or not safe(source) then self:Release(true); return end
            self.lease.alpha = alpha
            self.writing = true; source:SetAlpha(0); self.writing = false
            -- Native alpha is intentionally masked. Its fade/reset values must
            -- never drive the replacement's opacity or restart its animation.
        end
    end)
    -- Every Show refresh is observable, including Show on an already-visible tooltip.
    local function refresh()
        local data = safe(source) and source.GetPrimaryTooltipData and source:GetPrimaryTooltipData()
        if self.request then self.request(source, data) end
    end
    source:HookScript("OnShow", refresh)
    hooksecurefunc(source, "Show", refresh)
    hooksecurefunc(source, "SetShown", function(_, shown)
        if not public(shown) then self:Release(true, "native visibility restricted")
        elseif shown then refresh()
        elseif self.lease and self.lease.source == source then self:Release(false, "native tooltip hidden") end
    end)
end

function Adapter:Show(source, data, link, force)
    self:RestorePending(source)
    local renderer = self:Bind()
    if not renderer or not safe(source) or not safe(renderer) or source ~= GameTooltip then
        if self.lease and self.lease.source == source then self:Release() end
        return false
    end
    -- The first client trial uses upstream's single-slot comparison path.
    -- Do not inherit its incomplete combined-weapon arithmetic or self comparisons.
    for slot = 1, 19 do
        local equipped = GetInventoryItemLink("player", slot)
        if not public(equipped) or equipped == link then
            self.status = "equipped/restricted item: native fallback"; self:Release(); return false
        end
    end
    if data.overrideItemLevel ~= nil then
        self.status = "override item level: native fallback"; self:Release(); return false
    end
    local info = C_TooltipComparison.GetItemComparisonInfo(Toolkit.ItemComparison.Candidate(data))
    if info and (not accessible(info) or info.method ~= Enum.TooltipComparisonMethod.Single) then
        self.status = "combined/paired comparison: native fallback"; self:Release(); return false
    end
    local owner = source:GetOwner()
    if not public(owner) or not owner or owner:IsForbidden() then self:Release(); return false end
    local currentOwner, currentLink = renderer.owner, renderer:GetHyperlink()
    if not public(currentOwner) or not public(currentLink) then self:Release(); return false end
    local ours = self.lease and currentOwner == self.lease.owner and currentLink == self.lease.link
    if renderer:IsShown() and not ours then self.status = "Dialogue UI tooltip busy"; return false end
    local snapshot, signature = Dialogue.Snapshot(source, data, link)
    if not snapshot then self.status = "native body inaccessible or unsupported"; self:Release(); return false end
    self.serial = (self.serial or 0) + 1
    if ours and self.lease.owner == owner and self.lease.signature == signature and not force then
        self.reuses = self.reuses + 1
        self.status = "unchanged hover"; self:Place(); return self:Mask()
    end
    self:Watch(source)
    local alpha = self.lease and self.lease.source == source and self.lease.alpha or source:GetAlpha()
    if not public(alpha) then self:Release(); return false end
    self.writing = true
    renderer:SetOwner(owner, "ANCHOR_NONE")
    self.rendering = true
    self.refreshModel = force
    renderer:ClearLines()
    local rendered = renderer:ProcessTooltipData(snapshot)
    if rendered then renderer:Show(true) end -- Global hover is immediate; quest delay is unchanged.
    self.rendering, self.writing, self.refreshModel = false, false, false
    if not rendered or not renderer:IsShown() then self:Release(); return false end
    self.lease = { source = source, owner = owner, link = link, alpha = alpha, signature = signature, data = data,
        preview = renderer.usePreviewModel }
    self:Place()
    if not self.lease then return false end
    if not self:Mask() then return false end
    self.renders = self.renders + 1
    local lease = self.lease
    self:Sample(lease)
    C_Timer.After(0.35, function() self:Sample(lease) end)
    self.status = "native body rendered by Dialogue UI"
    return true
end
