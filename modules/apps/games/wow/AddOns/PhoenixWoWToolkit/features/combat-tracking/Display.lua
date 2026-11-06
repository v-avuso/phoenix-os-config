local _, Toolkit = ...
local M = Toolkit.CombatTracking
local D = {}
M.Display = D

function D.Available()
    -- Mixin globals live in Blizzard's forbidden partition; probe the public native
    -- facility here, then the actual created container's inbound methods below.
    if not (C_AuraContainerUtil and C_AuraContainerUtil.ProcessCustomAuraButtonDurationBarOptions) then return false end
    if C_XMLUtil and C_XMLUtil.GetTemplateInfo and not C_XMLUtil.GetTemplateInfo('CustomAuraContainerTemplate') then return false end
    if D.supported==nil then
        local c=CreateFrame('AuraContainer',nil,UIParent,'CustomAuraContainerTemplate')
        D.supported=type(c.AddAuraSlot)=='function' and type(c.SetUnit)=='function' and type(c.SetEnabled)=='function'
        if c.SetEnabled then c:SetEnabled(false) end
        c:Hide()
    end
    return D.supported
end

local function container(parent,group)
    local c=CreateFrame('AuraContainer',nil,parent,'CustomAuraContainerTemplate')
    assert(type(c.AddAuraSlot)=='function', 'Phoenix Combat Tracking requires the 12.1 AuraSlot API')
    c:SetSize(1,1)
    c:SetPoint('TOPLEFT',parent,'TOPLEFT')
    group[#group+1]=c
    return c
end

local function slot(c,id,filter,initialize,key)
    c:AddAuraSlot(key or 'effect',filter,{
        candidateFilters={includeSpellIDs={[id]=true}},
        initializeFrame=initialize,
    })
end

function D.Stop(display)
    if not display then return end
    -- Only inbound configuration and our ordinary root; never query/modify aura buttons here.
    for _,c in ipairs(display.containers) do c:SetEnabled(false) end
    display.root:Hide()
end

local function theme()
    local E=ElvUI and ElvUI[1]
    return E and E.media and E.media.normFont or STANDARD_TEXT_FONT,
        E and E.media and E.media.normTex or 'Interface\\Buttons\\WHITE8X8'
end

function D.Bars(config,palette,validate)
    local display={root=CreateFrame('Frame',nil,UIParent),containers={},slotCount=0}
    display.root:SetSize(1,1)
    display.root:SetPoint('CENTER',UIParent,'CENTER',config.x,config.y)
    display.root:SetFrameStrata('MEDIUM')
    local font,themeTexture=theme()
    for barIndex,bar in ipairs(config.bars) do
        if bar.enabled then
            local style=M.Copy(config)
            for _,key in ipairs({"width","height","texture","fillAlpha","icon","label"}) do
                if bar[key]~=nil then style[key]=bar[key] end
            end
            local anchor=CreateFrame('Frame',nil,display.root)
            anchor:SetSize(style.width,style.height)
            anchor:SetPoint('CENTER',display.root,'CENTER',bar.x or 0,bar.y or -(barIndex-1)*(style.height+8))
            local c=container(anchor,display.containers)
            -- Lowest priority first. Each active slot has a full opaque backing,
            -- so higher layers cover every pixel of the lower layer, including its label.
            for i=#bar.effects,1,-1 do
                local effect=bar.effects[i]
                if effect.enabled and validate(effect.spellID) then
                    display.slotCount=display.slotCount+1
                    slot(c,effect.spellID,'HELPFUL',function(button)
                        button:SetSize(style.width,style.height)
                        button:SetPoint('TOPLEFT',anchor,'TOPLEFT')
                        button:SetFrameLevel(anchor:GetFrameLevel()+2+(#bar.effects-i)*3)
                        button:EnableMouse(false)
                        local backing=button:CreateTexture(nil,'BACKGROUND')
                        backing:SetAllPoints(); backing:SetColorTexture(.035,.035,.035,1)
                        local offset=style.icon and style.height or 0
                        local progress=CreateFrame('StatusBar',nil,button)
                        progress:SetPoint('TOPLEFT',button,'TOPLEFT',offset,0)
                        progress:SetPoint('BOTTOMRIGHT',button,'BOTTOMRIGHT')
                        progress:SetStatusBarTexture(style.texture=='theme' and themeTexture or style.texture)
                        local r,g,b=M.Color(effect,palette)
                        progress:SetStatusBarColor(r,g,b,style.fillAlpha)
                        button:SetDurationBar(progress)
                        if style.icon then
                            local icon=button:CreateTexture(nil,'ARTWORK')
                            icon:SetSize(style.height,style.height)
                            icon:SetPoint('LEFT',button,'LEFT')
                            button:SetIcon(icon)
                        end
                        if style.label then
                            local label=progress:CreateFontString(nil,'OVERLAY')
                            label:SetFont(font,math.min(14,style.height-4),'OUTLINE')
                            label:SetPoint('LEFT',progress,'LEFT',6,0)
                            label:SetPoint('RIGHT',progress,'RIGHT',-6,0)
                            label:SetJustifyH('LEFT')
                            label:SetWordWrap(false)
                            button:SetSpellName(label)
                        end
                    end,'effect-'..i)
                end
            end
        end
    end
    for _,c in ipairs(display.containers) do c:SetUnit('player'); c:SetEnabled(true) end
    return display
end

local function border(button,anchor,thickness,rgb)
    for _,side in ipairs({'TOP','BOTTOM','LEFT','RIGHT'}) do
        local t=button:CreateTexture(nil,'OVERLAY')
        t:SetColorTexture(rgb[1],rgb[2],rgb[3],1)
        if side=='TOP' or side=='BOTTOM' then
            t:SetPoint(side..'LEFT',anchor,side..'LEFT',-thickness,side=='TOP' and thickness or -thickness)
            t:SetPoint(side..'RIGHT',anchor,side..'RIGHT',thickness,side=='TOP' and thickness or -thickness)
            t:SetHeight(thickness)
        else
            t:SetPoint('TOP'..side,anchor,'TOP'..side,side=='LEFT' and -thickness or thickness,0)
            t:SetPoint('BOTTOM'..side,anchor,'BOTTOM'..side,side=='LEFT' and -thickness or thickness,0)
            t:SetWidth(thickness)
        end
    end
end

function D.Nameplate(anchor,unit,config,palette,validate)
    local display={root=CreateFrame('Frame',nil,UIParent),containers={},slotCount=0}
    display.root:SetAllPoints(anchor)
    display.root:SetFrameStrata(anchor:GetFrameStrata())
    display.root:SetFrameLevel(anchor:GetFrameLevel()+8)
    local effects={}
    for _,e in ipairs(config.highlights) do
        if e.enabled and validate(e.spellID) then effects[#effects+1]=e end
    end
    for index,rule in ipairs(M.Subsets(effects,palette)) do
        -- Parent visibility is the AND operation. Build children inside initializeFrame
        -- before Blizzard applies the outer button's access restrictions. No OnShow
        -- callbacks, visibility reads, aura queries, or secure snippets are involved.
        local function build(parent,depth)
            local c=container(parent,display.containers)
            display.slotCount=display.slotCount+1
            slot(c,rule.effects[depth].spellID,'HARMFUL|PLAYER',function(button)
                button:SetAllPoints(display.root)
                button:SetFrameLevel(display.root:GetFrameLevel()+index*4+depth)
                button:EnableMouse(false)
                if depth<#rule.effects then build(button,depth+1)
                else border(button,display.root,config.thickness,rule.rgb) end
            end)
        end
        build(display.root,1)
    end
    for _,c in ipairs(display.containers) do c:SetUnit(unit); c:SetEnabled(true) end
    return display
end
