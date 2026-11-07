local _, Toolkit = ...
local M = {}
Toolkit.CombatTracking = M

function M.Copy(value)
    if type(value) ~= 'table' then return value end
    local copy = {}; for k,v in pairs(value) do copy[k] = M.Copy(v) end
    return copy
end

function M.HSV(h,s,v)
    local sector = (h % 360) / 60
    local c, x = v*s, v*s*(1-math.abs(sector%2-1))
    local rgb = {{c,x,0},{x,c,0},{0,c,x},{0,x,c},{x,0,c},{c,0,x}}
    local t, m = rgb[math.floor(sector)+1], v-c
    return t[1]+m,t[2]+m,t[3]+m
end

function M.ParseHex(text)
    if type(text) ~= 'string' then return end
    return text:match('^#?(%x%x%x%x%x%x)$') and text:gsub('#',''):upper() or nil
end

function M.Color(effect,palette)
    local hex = M.ParseHex(effect.hex)
    if hex then return tonumber(hex:sub(1,2),16)/255,tonumber(hex:sub(3,4),16)/255,tonumber(hex:sub(5,6),16)/255 end
    return M.HSV(effect.hue or 315,effect.saturation or palette.saturation,effect.value or palette.value)
end

function M.NextHue(assigned)
    local best, distance = 315,-1
    for _,h in ipairs({315,190,45,135,265,10}) do
        local nearest=360
        for _,a in ipairs(assigned) do nearest=math.min(nearest,math.abs((h-a+180)%360-180)) end
        if nearest>distance then best,distance=h,nearest end
    end
    return best
end

function M.AssignedHue(effect,palette)
    if not M.ParseHex(effect.hex) then return effect.hue or 315 end
    local r,g,b=M.Color(effect,palette)
    local hi,lo=math.max(r,g,b),math.min(r,g,b)
    local delta=hi-lo
    if delta==0 then return effect.hue or 315 end
    local h=hi==r and ((g-b)/delta)%6 or hi==g and (b-r)/delta+2 or (r-g)/delta+4
    return (h*60)%360
end

local function effect(id,hue) return {spellID=id,hue=hue,enabled=true} end
local function bar(name,effects) return {name=name,enabled=true,effects=effects} end
M.presets = {
    [104] = {bars={{name='Incarnation / Dream Conduit',enabled=true,
        effects={effect(102558,190),effect(1308176,45)},
        width=65,height=6,icon=false,label=false,anchorPlayer=true}}},
    [102] = {bars={bar('Eclipse',{effect(48517,45),effect(48518,190)})},
        highlights={effect(164812,315),effect(164815,190)}},
    [105] = {bars={bar('Healing procs',{effect(16870,135),effect(114108,45)})}},
    [103] = {},
}
M.specNames = {[104]='Guardian',[102]='Balance',[105]='Restoration',[103]='Feral'}
M.base = {barsEnabled=true,platesEnabled=true,width=65,height=6,x=0,y=-180,
    icon=false,label=false,anchorPlayer=true,fillAlpha=1,texture='theme',
    thickness=3,bars={},highlights={}}
M.classDefaults = {highlights={effect(164812,315)}}

function M.Initialize(db)
    db.palette = db.palette or {saturation=.75,value=.95}
    db.global,db.druid,db.specs = db.global or {}, db.druid or {}, db.specs or {}
    db.classes=db.classes or {}
end

function M.Key(value)
    if type(value)~='table' then return type(value)..':'..tostring(value) end
    local keys={}; for k in pairs(value) do keys[#keys+1]=k end
    table.sort(keys,function(a,b) return tostring(a)<tostring(b) end)
    local parts={}
    for _,k in ipairs(keys) do parts[#parts+1]=M.Key(k)..'='..M.Key(value[k]) end
    return '{'..table.concat(parts,';')..'}'
end

local function overlay(result,values)
    for k,v in pairs(values or {}) do result[k]=M.Copy(v) end
end

-- Lists replace inherited lists atomically; scalar presentation options inherit individually.
function M.Resolve(db,spec,scope,class)
    class=class or 'DRUID'
    local result=M.Copy(M.base); overlay(result,db.global)
    if scope=='global' then return result end
    if class=='DRUID' then
        overlay(result,M.classDefaults); overlay(result,db.druid)
    else overlay(result,db.classes[class]) end
    if scope=='class' or scope=='druid' then return result end
    if class=='DRUID' then overlay(result,M.presets[spec]) end
    overlay(result,db.specs[tostring(spec)])
    return result
end

function M.Subsets(effects,palette)
    local enabled={}
    for _,e in ipairs(effects) do if e.enabled and #enabled<3 then enabled[#enabled+1]=e end end
    local rules={}
    for mask=1,2^#enabled-1 do
        local rule={effects={},rgb={0,0,0},mask=mask}
        for i,e in ipairs(enabled) do
            if mask % 2^i >= 2^(i-1) then
                rule.effects[#rule.effects+1]=e
                local r,g,b=M.Color(e,palette)
                rule.rgb[1]=rule.rgb[1]+r; rule.rgb[2]=rule.rgb[2]+g; rule.rgb[3]=rule.rgb[3]+b
            end
        end
        for i=1,3 do rule.rgb[i]=rule.rgb[i]/#rule.effects end
        rules[#rules+1]=rule
    end
    table.sort(rules,function(a,b)
        if #a.effects==#b.effects then return a.mask<b.mask end
        return #a.effects<#b.effects
    end)
    return rules
end

function M.ValidSpell(id)
    return type(id)=='number' and id>0 and id==math.floor(id) and C_Spell and C_Spell.GetSpellInfo(id) ~= nil
end
