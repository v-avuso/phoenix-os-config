local _,Toolkit=...
local M=Toolkit.CombatTracking
local F=M.feature

-- Feature-local editor. Changes are saved immediately; Apply rebuilds displays once,
-- outside combat. Previews never read the state of a live secure aura frame.
local function button(panel,text,x,y,fn,width)
    local b=CreateFrame('Button',nil,panel,'UIPanelButtonTemplate')
    b:SetSize(width or 100,24); b:SetPoint('TOPLEFT',x,y); b:SetText(text)
    b:SetScript('OnClick',fn); return b
end
local function input(panel,label,value,x,y,fn,width)
    local l=panel:CreateFontString(nil,'ARTWORK','GameFontHighlightSmall')
    l:SetPoint('TOPLEFT',x,y); l:SetText(label)
    local edit=CreateFrame('EditBox',nil,panel,'InputBoxTemplate')
    edit:SetSize(width or 120,24); edit:SetPoint('TOPLEFT',x,y-18)
    edit:SetAutoFocus(false); edit:SetText(tostring(value or ''))
    edit:SetScript('OnEscapePressed',function(self) self:ClearFocus(); self:SetText(tostring(value or '')) end)
    edit:SetScript('OnEnterPressed',function(self)
        if fn(self:GetText())~=false then self:ClearFocus() else self:HighlightText() end
    end)
    return edit
end
local function dropdown(panel,label,items,selected,y,changed)
    Toolkit.Options.Text(panel,label,y,'GameFontHighlightSmall')
    local d=CreateFrame('DropdownButton',nil,panel,'WowStyle1DropdownTemplate')
    d:SetPoint('TOPLEFT',24,y-20); d:SetWidth(350)
    d:SetupMenu(function(_,menu)
        for _,entry in ipairs(items) do
            menu:CreateRadio(entry[2],function() return selected==entry[1] end,
                function() changed(entry[1]) end)
        end
    end)
    for _,entry in ipairs(items) do if entry[1]==selected then d:OverrideText(entry[2]) end end
end
function F:RebuildEditor()
    Toolkit.optionsDirty=true
    if Toolkit.scroll then
        local offset=Toolkit.scroll:GetVerticalScroll()
        Toolkit:BuildOptions()
        Toolkit.scroll:SetVerticalScroll(offset)
    end
end
local function number(text,min,max)
    local n=tonumber(text)
    if not n or n~=n or n<min or n>max then return end
    return n
end
function F:RegisterSettings(panel,y)
    self:Initialize()
    local spec=self:Spec()
    local scope=self.editScope or 'spec'
    local config=M.Resolve(self.settings,spec,scope)
    local overrides=scope=='global' and self.settings.global or scope=='druid' and self.settings.druid
    if not overrides then
        local key=tostring(spec)
        self.settings.specs[key]=self.settings.specs[key] or {}
        overrides=self.settings.specs[key]
    end
    local function save(key,value) overrides[key]=M.Copy(value); self:RebuildEditor() end
    self.enableCheckbox=Toolkit.Options.Checkbox(panel,'Enable Druid combat tracking (experimental)',y,
        self.settings,'enabled',function() Toolkit:RefreshFeatures() end,
        'Uses the matching specialization preset; other classes are unaffected.')
    y=y-64
    self.statusLabel=Toolkit.Options.Text(panel,'',y,'GameFontHighlightSmall'); y=y-32
    Toolkit.Options.Text(panel,'Profiles',y,'GameFontNormal'); y=y-26
    dropdown(panel,'Edit inherited defaults or specialization overrides',{
        {'global','Global defaults'},{'druid','Druid defaults'},
        {'spec',(M.specNames[spec] or 'Current specialization')..' overrides'},
    },scope,y,function(value) self.editScope=value; self:RebuildEditor() end)
    y=y-62
    button(panel,'Reset to inherited',24,y,function()
        for k in pairs(overrides) do overrides[k]=nil end
        self:RebuildEditor()
    end,160)
    button(panel,'Apply changes',200,y,function() self:RequestApply(); self:RefreshSettings() end,130)
    y=y-40
    Toolkit.Options.Text(panel,'Aura Bars',y,'GameFontNormal'); y=y-28
    local function check(label,key)
        Toolkit.Options.Checkbox(panel,label..(overrides[key]==nil and ' (inherited)' or ' (override)'),
            y,config,key,function() save(key,config[key]) end)
        y=y-36
    end
    check('Show priority aura bars','barsEnabled')
    check('Show aura icons','icon'); check('Show aura labels','label')
    local function numeric(label,key,min,max)
        input(panel,label..(overrides[key]==nil and ' (inherited)' or ' (override)'),config[key],24,y,function(text)
            local n=number(text,min,max); if not n then return false end
            save(key,n)
        end)
        y=y-56
    end
    numeric('Width (40–1000)', 'width',40,1000)
    numeric('Height (2–100)', 'height',2,100)
    numeric('Horizontal offset from center','x',-4000,4000)
    numeric('Vertical offset from center','y',-2000,2000)
    numeric('Fill opacity (0–1; backing stays opaque)','fillAlpha',0,1)
    dropdown(panel,'Bar texture',{{'theme','ElvUI / ToxiUI texture'},
        {'Interface\\Buttons\\WHITE8X8','Flat'}},config.texture,y,function(v) save('texture',v) end)
    y=y-64
    Toolkit.Options.Text(panel,'Priority lists ('..(overrides.bars==nil and 'inherited' or 'override')..')',y,'GameFontHighlightSmall')
    y=y-28

    local function effectsEditor(effects,changed,max)
        for index,e in ipairs(effects) do
            local info=C_Spell and C_Spell.GetSpellInfo(e.spellID)
            local name=info and info.name or 'Unavailable spell'
            local r,g,b=M.Color(e,self.settings.palette)
            local swatch=panel:CreateTexture(nil,'ARTWORK')
            swatch:SetSize(16,16); swatch:SetPoint('TOPLEFT',24,y)
            swatch:SetColorTexture(r,g,b,1)
            Toolkit.Options.Text(panel,'      '..index..'. '..name,y,'GameFontHighlightSmall')
            y=y-24
            Toolkit.Options.Checkbox(panel,'Enabled',y,e,'enabled',function() changed() end)
            button(panel,'Up',145,y,function()
                if index>1 then effects[index],effects[index-1]=effects[index-1],effects[index]; changed() end
            end,55)
            button(panel,'Down',205,y,function()
                if index<#effects then effects[index],effects[index+1]=effects[index+1],effects[index]; changed() end
            end,55)
            button(panel,'Remove',265,y,function() table.remove(effects,index); changed() end,80)
            y=y-40
            input(panel,'Aura spell ID',e.spellID,24,y,function(text)
                local id=number(text,1,100000000)
                if not id or not M.ValidSpell(id) then return false end
                e.spellID=id; changed()
            end)
            input(panel,'Hue (0–359)',e.hue,180,y,function(text)
                local hue=number(text,0,359); if not hue then return false end
                e.hue=hue; e.hex=nil; changed()
            end)
            input(panel,'Hex override (blank = palette)',e.hex,335,y,function(text)
                local hex=M.ParseHex(text)
                if text~='' and not hex then return false end
                e.hex=hex; changed()
            end,180)
            y=y-62
        end
        if not max or #effects<max then
            button(panel,'Add effect',24,y,function()
                local hues={}; for _,e in ipairs(effects) do hues[#hues+1]=M.AssignedHue(e,self.settings.palette) end
                effects[#effects+1]={spellID=1126,enabled=true,hue=M.NextHue(hues)}
                changed()
            end,110)
            y=y-36
        end
    end
    for index,bar in ipairs(config.bars) do
        local function changed() save('bars',config.bars) end
        input(panel,'Bar name',bar.name,24,y,function(text)
            if #text<1 or #text>80 then return false end
            bar.name=text; changed()
        end,260)
        button(panel,'Remove bar',310,y-18,function() table.remove(config.bars,index); changed() end,110)
        y=y-60
        Toolkit.Options.Checkbox(panel,'Enable this bar',y,bar,'enabled',changed); y=y-40
        for _,fields in ipairs({{{'width','Width',40,1000},{'height','Height',2,100},{'fillAlpha','Fill opacity',0,1}},
            {{'x','Horizontal offset',-4000,4000},{'y','Vertical offset',-2000,2000}}}) do
            for column,field in ipairs(fields) do
                input(panel,field[2]..' (blank = inherited)',bar[field[1]],24+(column-1)*175,y,function(text)
                    local n=text~='' and number(text,field[3],field[4]) or nil
                    if text~='' and not n then return false end
                    bar[field[1]]=n; changed()
                end,145)
            end
            y=y-56
        end
        local appearance={icon=bar.icon==nil and config.icon or bar.icon,
            label=bar.label==nil and config.label or bar.label,anchorPlayer=bar.anchorPlayer}
        for _,entry in ipairs({{'icon','Show icon'},{'label','Show label'},
            {'anchorPlayer','Anchor beneath ElvUI player power bar'}}) do
            Toolkit.Options.Checkbox(panel,entry[2],y,appearance,entry[1],function()
                bar[entry[1]]=appearance[entry[1]]; changed()
            end)
            y=y-34
        end
        dropdown(panel,'Bar texture',{{'inherit','Inherited texture'},{'theme','ElvUI / ToxiUI texture'},
            {'Interface\\Buttons\\WHITE8X8','Flat'}},bar.texture or 'inherit',y,function(v)
                bar.texture=v~='inherit' and v or nil; changed()
            end)
        y=y-62
        button(panel,'Reset bar appearance',24,y,function()
            for _,key in ipairs({'width','height','x','y','fillAlpha','icon','label','texture','anchorPlayer'}) do bar[key]=nil end
            changed()
        end,175)
        y=y-38
        effectsEditor(bar.effects,changed)
        y=y-12
    end
    button(panel,'Add bar',24,y,function()
        config.bars[#config.bars+1]={name='New aura bar',enabled=true,effects={}}
        save('bars',config.bars)
    end,110)
    y=y-46
    Toolkit.Options.Text(panel,'Nameplate Highlights',y,'GameFontNormal'); y=y-28
    check('Highlight player-applied debuffs','platesEnabled')
    numeric('Border thickness (1–12)','thickness',1,12)
    Toolkit.Options.Text(panel,'Debuff list ('..(overrides.highlights==nil and 'inherited' or 'override')..')',y,'GameFontHighlightSmall')
    y=y-28
    effectsEditor(config.highlights,function() save('highlights',config.highlights) end,3)
    Toolkit.Options.Text(panel,'Borders combine active colors; health-bar threat coloring is preserved.',y,'GameFontHighlightSmall')
    y=y-42
    Toolkit.Options.Text(panel,'Color Palette (account-wide)',y,'GameFontNormal'); y=y-30
    for _,entry in ipairs({{'saturation','Saturation (%)'},{'value','Value (%)'}}) do
        input(panel,entry[2],self.settings.palette[entry[1]]*100,24,y,function(text)
            local n=number(text,0,100); if not n then return false end
            self.settings.palette[entry[1]]=n/100; self:RebuildEditor()
        end)
        y=y-56
    end
    self:RefreshSettings()
    return y-20
end

function F:RefreshSettings()
    if self.enableCheckbox then self.enableCheckbox:SetChecked(self.settings.enabled) end
    if self.statusLabel then
        self.statusLabel:SetText(self.pending and 'Changes queued until combat ends.'
            or 'Save fields with Enter. Apply changes when ready. /pwtcombat shows diagnostics.')
    end
end
