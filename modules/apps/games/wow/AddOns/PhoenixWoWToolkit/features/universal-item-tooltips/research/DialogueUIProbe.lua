-- Research-only proof. Not listed in the TOC; never changes installed Dialogue UI.
local Probe = {}
local required = { "ProcessInfo", "ShowItemComparison", "DisplayModel", "ShowHotkey", "GetHyperlink", "SetQuestItem" }
local function public(value) return not (issecretvalue and issecretvalue(value)) end

function Probe.Find(version)
    if version ~= "1.0.7" then return nil, "unverified version" end
    local found
    local frame = EnumerateFrames()
    while frame do
        if not frame:IsForbidden() and not frame:IsProtected() then
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

-- Only lease an idle singleton or continue the same lease. Quest UI always wins.
function Probe.Show(renderer, owner, link, previous)
    if not renderer or renderer:IsForbidden() or renderer:IsProtected()
        or (renderer.IsAnchoringSecret and renderer:IsAnchoringSecret()) then return nil, "unsafe renderer" end
    if not public(link) or type(link) ~= "string" or link == "" then return nil, "invalid link" end
    local currentOwner, currentLink = renderer.owner, renderer:GetHyperlink()
    if not public(owner) or not owner or not public(currentOwner) or not public(currentLink) then
        return nil, "inaccessible state"
    end
    local ours = previous and previous.renderer == renderer and currentOwner == previous.owner
        and currentLink == previous.link
    if renderer:IsShown() and not ours then return nil, "renderer busy" end
    if ours and renderer:IsShown() and previous.owner == owner and previous.link == link then
        return previous, "unchanged" -- Do not restart model loading or the native fade on refresh.
    end
    renderer:SetOwner(owner, "ANCHOR_NONE")
    renderer:SetPoint("BOTTOMLEFT", owner, "TOPRIGHT", 0, 2)
    renderer:ProcessInfo({ getterName = "GetHyperlink", getterArgs = { link }, isItem = true })
    if not renderer:IsShown() or renderer:GetHyperlink() ~= link then return nil, "no item data" end
    return { renderer = renderer, owner = owner, link = link }
end

function Probe.Release(lease)
    if not lease or lease.renderer:IsForbidden() or lease.renderer:IsProtected() then return end
    local owner, link = lease.renderer.owner, lease.renderer:GetHyperlink()
    if public(owner) and public(link) and owner == lease.owner and link == lease.link then lease.renderer:Hide() end
end

return Probe
