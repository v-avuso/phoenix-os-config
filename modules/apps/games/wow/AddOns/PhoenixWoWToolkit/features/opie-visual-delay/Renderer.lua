local _, Toolkit = ...
local Adapter = {}
Toolkit.OPieDelay = Adapter
local function public(value) return not (issecretvalue and issecretvalue(value)) end

local function ordinary(frame)
    return frame and type(frame.IsForbidden) == "function" and type(frame.IsProtected) == "function"
        and not frame:IsForbidden() and not frame:IsProtected()
end

-- OPie 8.10.2 creates one unnamed FULLSCREEN/100 frame with its pointer texture.
-- Discover once, before adding hooks; never guess if the result is ambiguous.
function Adapter.Find()
    if not UIParent or not OPie or not OPie.HUM then return nil, "OPie not initialized" end
    local proxy, tip = OPieVisualElementsProxy, OPie.HUM.NotGameTooltip
    if not ordinary(proxy) or not ordinary(tip) or type(tip.IsOwned) ~= "function"
        or type(tip.SetOwner) ~= "function" or proxy:GetParent() ~= UIParent then
        return nil, "Unexpected proxy/tooltip structure"
    end
    local pointer = GetFileIDFromPath("Interface\\AddOns\\OPie\\gfx\\pointer")
    local function isPointer(texture)
        if not public(texture) then return false end
        if type(texture) == "string" then
            return texture:gsub("\\", "/"):lower():gsub("%.tga$", "") == "interface/addons/opie/gfx/pointer"
        end
        return pointer ~= nil and texture == pointer
    end
    local mains, cores = {}, {}
    -- Parenting is not an identity: other UI add-ons can reparent the input frame.
    -- Observe only its public identity; never mutate this protected button.
    local frame = EnumerateFrames()
    while frame do
        if not frame:IsForbidden() then
            local name = frame:GetName()
            if public(name) and type(name) == "string" and name:match("^OPieRT%-%x%x%x%x%x%x%x%x%-%x%x%x%x$")
                and frame:IsObjectType("Button") and frame:IsProtected()
                and type(frame.NotifyState) == "function" then
                cores[#cores + 1] = frame
            end
        end
        frame = EnumerateFrames(frame)
    end
    for _, frame in ipairs({ UIParent:GetChildren() }) do
        if not frame:IsForbidden() then
            local name = frame:GetName()
            if public(name) and ordinary(frame) and not name then
                local strata, level = frame:GetFrameStrata(), frame:GetFrameLevel()
                local w, h = frame:GetSize()
                if public(strata) and public(level) and public(w) and public(h)
                    and strata == "FULLSCREEN" and level == 100 and math.abs(w - 150) < 0.05 and math.abs(h - 150) < 0.05 then
                    for _, region in ipairs({ frame:GetRegions() }) do
                        if region:IsObjectType("Texture") then
                            local texture = region:GetTexture()
                            if isPointer(texture) then
                                mains[#mains + 1] = frame
                                break
                            end
                        end
                    end
                end
            end
        end
    end
    if #mains ~= 1 or #cores ~= 1 then return nil, ("Unexpected renderer/notification structure (visuals=%d, notifications=%d)"):format(#mains, #cores) end
    return { main = mains[1], proxy = proxy, tip = tip, core = cores[1] }
end

function Adapter.Bind(view)
    local gate = { view = view, serial = 0, enabled = false, hidden = false, open = false,
        alpha = { [view.main] = view.main:GetAlpha(), [view.proxy] = view.proxy:GetAlpha() } }
    gate.tipAlpha = view.tip:GetAlpha()

    function gate:Write(frame, alpha)
        -- Do not attempt a protected mutation or catch/suppress a client error.
        if not ordinary(frame) then return end
        self.writing = true
        frame:SetAlpha(alpha)
        self.writing = false
    end

    function gate:Tooltip()
        if self.hidden and view.tip:IsOwned(view.proxy) then
            self.tipSuppressed = true
            self:Write(view.tip, 0)
        elseif self.tipSuppressed then
            self.tipSuppressed = false
            self:Write(view.tip, self.tipAlpha)
        end
    end

    function gate:Restore()
        for frame, alpha in pairs(self.alpha) do self:Write(frame, alpha) end
        self:Tooltip()
    end

    function gate:RevealAfter(delay)
        self.serial = self.serial + 1
        local serial = self.serial
        C_Timer.After(delay, function()
            if self.enabled and self.open and serial == self.serial then
                self.hidden = false
                self:Restore()
            end
        end)
    end

    function gate:Start()
        self.serial = self.serial + 1
        self.open, self.openedAt = true, GetTime()
        self.hidden = self.delayMs > 0
        if self.hidden then
            self:Write(view.main, 0)
            self:Write(view.proxy, 0)
            self:Tooltip()
            self:RevealAfter(self.delayMs / 1000)
        else
            self:Restore()
        end
    end

    function gate:Configure(enabled, delayMs)
        self.serial = self.serial + 1 -- Invalidates callbacks even on disable/re-enable.
        self.enabled, self.delayMs = enabled, delayMs
        if not enabled then
            self.hidden = false
            self:Restore()
        elseif self.open then
            if self.hidden then
                local remaining = self.openedAt + delayMs / 1000 - GetTime()
                if remaining > 0 then self:RevealAfter(remaining)
                else self.hidden = false; self:Restore() end
            elseif delayMs == 0 then
                self:Restore()
            end
        elseif delayMs == 0 then
            self.hidden = false
            self:Restore()
        end
    end

    for _, frame in ipairs({ view.main, view.proxy }) do
        hooksecurefunc(frame, "SetAlpha", function(_, alpha)
            if gate.writing then return end
            gate.alpha[frame] = alpha
            if gate.hidden then gate:Write(frame, 0) end
        end)
    end
    hooksecurefunc(view.tip, "SetAlpha", function(_, alpha)
        if gate.writing then return end
        gate.tipAlpha = alpha
        gate:Tooltip()
    end)
    for _, method in ipairs({ "Show", "SetOwner" }) do
        hooksecurefunc(view.tip, method, function() gate:Tooltip() end)
    end
    -- Read-only observer of the existing visual notification. No WrapScript,
    -- secure attributes, bindings, action selection or original function replacement.
    hooksecurefunc(view.core, "NotifyState", function(_, state)
        if state == "close" then
            gate.open = false
            gate.serial = gate.serial + 1
            -- Keep a cancelled, still-hidden ring hidden throughout native fade-out.
        elseif state == "open" then
            if gate.enabled then gate:Start()
            else gate.open, gate.openedAt = true, GetTime() end
        elseif gate.enabled and state == "switch" and not gate.open then
            gate:Start()
        end -- A nested switch preserves an existing deadline or visible ring.
    end)
    return gate
end
