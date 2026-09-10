-- EmberLoot 0.2.0 —— Emberveil 掉落浏览器（AtlasLoot 式：副本→首领→掉落表）
-- 客户端：Emberveil UE5（1.12.1 / Lua 5.1 API）。零第三方库，OneJudge 同款 pcall 风格。
--
-- 数据（data.lua 生成）：
--   EL_Zones[zid]     = {"NameEn","名字Zh", 玩家人数上限, {cid,...}}
--   EL_Creatures[cid] = {"NameEn","名字Zh", 等级, rank, {zid,...}}
--   EL_Drops[cid]     = { {entry,chance,group,min,max,questFlag}, ... }
--   EL_Items[entry]   = {"NameEn","名字Zh", quality, "icon_纹理名"[, detail 表]}
--   detail（0.2.0 新增，来自 database.emberveil.org /api/proxy/items）：
--     il=item等级 rl=需求等级 c/class sc/subclass inv=装备位 b=绑定(1拾取2装备3使用)
--     st={{"Agility",5},...} rs={{"Fire",8},...} dg={{min,max,"Physical"},...}
--     ar=护甲 bl=格挡 dl=攻速ms mc=最大持有 bp/sp=买/卖价(铜) du=耐久 re=随机附魔
--     spx={{"装备：","NameEn","名Zh","descEn","descZh"},...} dx_en/dx_zh=灰字描述 set_en/set_zh
--
-- 命令：/el 或 /emberloot 开关窗口；/el zh|en 切语言；/el fav 只看收藏。
-- 交互：左列点副本→首领；右列始终是物品表；Shift+点物品=收藏；聊天框打开时点物品=插链接；
--       悬停物品=属性 tooltip（缓存物品用客户端原生，其余用数据库自绘）；小地图按钮可拖拽、点击开关窗口。

local VERSION = "0.2.0"

-- ============================================================ 配置

local function cfgReady()
    if type(EL_Config) ~= "table" then EL_Config = {} end
    local c = EL_Config
    if c.lang == nil then c.lang = "zh" end
    if type(c.fav) ~= "table" then c.fav = {} end
    if c.x == nil then c.x = 0 end
    if c.y == nil then c.y = 0 end
    if c.quality == nil then c.quality = 0 end  -- 0 = 全部品质，1..4 = 至少该品质
    return c
end

-- ============================================================ 词表（key 即中文）

local EN_WORDS = {
    ["收藏"] = "Fav", ["返回"] = "Back", ["品质:全部"] = "Quality: All",
    ["组"] = "grp", ["任务"] = "Q", ["全部"] = "All",
    ["%d 个副本"] = "%d instances", ["%d 个首领"] = "%d bosses",
    ["%d 件物品"] = "%d items", ["%d 条掉落"] = "%d drops",
    ["品质 "] = "Quality ", ["掉落自"] = "Dropped by",
    ["输入 /el 打开掉落浏览器"] = "type /el to open the loot browser",
    ["游戏内未见过该物品"] = "Not seen in game yet (uncached)",
    ["个副本 / "] = " instances / ", [" 件物品"] = " items",
    ["已加载"] = "loaded",
    ["搜索物品名..."] = "search item name...",
    ["点击打开掉落浏览器"] = "click to open the loot browser",
    ["出售价格"] = "Sell Price",
    ["套装"] = "Set",
    ["随机附魔"] = "Random enchantment",
    ["每秒伤害"] = "DPS",
    ["伤害"] = "Damage",
}
local function L(key)
    local c = cfgReady()
    if c.lang == "en" and EN_WORDS[key] then return EN_WORDS[key] end
    return key
end

-- ============================================================ 品质颜色 / 工具

local QUALITY_HEX = {
    [0] = "#9d9d9d", [1] = "#ffffff", [2] = "#1eff00", [3] = "#0070dd",
    [4] = "#a335ee", [5] = "#ff8000", [6] = "#e5cc80",
}
local QUALITY_NAME = {
    zh = { [0] = "粗糙", "普通", "优秀", "稀有", "史诗", "传说", "神器" },
    en = { [0] = "Poor", "Common", "Uncommon", "Rare", "Epic", "Legendary", "Artifact" },
}

local function hexToRGB(hex)
    if type(hex) ~= "string" or string.len(hex) < 7 then return 1, 1, 1 end
    local r = tonumber(string.sub(hex, 2, 3), 16) or 255
    local g = tonumber(string.sub(hex, 4, 5), 16) or 255
    local b = tonumber(string.sub(hex, 6, 7), 16) or 255
    return r / 255, g / 255, b / 255
end

local function qColor(q)
    return hexToRGB(QUALITY_HEX[q] or "#ffffff")
end

-- ============================================================ 数据访问

local function itemName(entry, lang)
    local it = EL_Items and EL_Items[entry]
    if not it then return nil end
    if lang == "en" then return it[1] end
    return it[2] or it[1]
end

local function creatureName(cid, lang)
    local c = EL_Creatures and EL_Creatures[cid]
    if not c then return nil end
    if lang == "en" then return c[1] end
    return c[2] or c[1]
end

local function zoneName(zid, lang)
    local z = EL_Zones and EL_Zones[zid]
    if not z then return nil end
    if lang == "en" then return z[1] end
    return z[2] or z[1]
end

local function itemCached(entry)
    local ok, name = pcall(GetItemInfo, entry)
    return ok and name ~= nil
end

-- entry -> {cid,...}（全部掉落来源）
local sourcesCache = nil
local function getSources(entry)
    if not sourcesCache then
        sourcesCache = {}
        for cid, rows in pairs(EL_Drops or {}) do
            for _, r in ipairs(rows) do
                local e = r[1]
                if not sourcesCache[e] then sourcesCache[e] = {} end
                table.insert(sourcesCache[e], cid)
            end
        end
    end
    return sourcesCache[entry] or {}
end

-- ============================================================ 物品属性词典（detail 枚举 -> 双语文案）

local T_CLASS = {
    [0] = {"Consumable", "消耗品"}, [1] = {"Container", "容器"},
    [2] = {"Weapon", "武器"}, [4] = {"Armor", "护甲"},
    [5] = {"Reagent", "试剂"}, [6] = {"Projectile", "弹药"},
    [7] = {"Quiver", "箭袋"}, [9] = {"Recipe", "配方"},
    [11] = {"Trade Goods", "商品"}, [12] = {"Quest", "任务"},
    [13] = {"Key", "钥匙"}, [15] = {"Miscellaneous", "杂项"},
}
local T_SUB_WEAPON = {
    [0] = {"Axe", "斧"}, [1] = {"Two-Handed Axe", "双手斧"}, [2] = {"Bow", "弓"},
    [3] = {"Gun", "枪械"}, [4] = {"Mace", "锤"}, [5] = {"Two-Handed Mace", "双手锤"},
    [6] = {"Polearm", "长柄武器"}, [7] = {"Sword", "剑"}, [8] = {"Two-Handed Sword", "双手剑"},
    [10] = {"Staff", "法杖"}, [13] = {"Fist Weapon", "拳套"}, [14] = {"Miscellaneous", "杂项"},
    [15] = {"Dagger", "匕首"}, [16] = {"Thrown", "投掷武器"}, [17] = {"Crossbow", "弩"},
    [18] = {"Wand", "魔杖"}, [19] = {"Fishing Pole", "鱼竿"},
}
local T_SUB_ARMOR = {
    [0] = {"Miscellaneous", "杂项"}, [1] = {"Cloth", "布甲"}, [2] = {"Leather", "皮甲"},
    [3] = {"Mail", "锁甲"}, [4] = {"Plate", "板甲"}, [6] = {"Shield", "盾牌"},
    [7] = {"Libram", "圣契"}, [8] = {"Idol", "神像"}, [9] = {"Totem", "图腾"},
}
local T_INV = {
    [0] = {"Non-equippable", "非装备"}, [1] = {"Head", "头部"}, [2] = {"Neck", "颈部"},
    [3] = {"Shoulder", "肩部"}, [4] = {"Shirt", "衬衣"}, [5] = {"Chest", "胸部"},
    [6] = {"Waist", "腰部"}, [7] = {"Legs", "腿部"}, [8] = {"Feet", "脚"},
    [9] = {"Wrist", "手腕"}, [10] = {"Hands", "手"}, [11] = {"Finger", "手指"},
    [12] = {"Trinket", "饰品"}, [13] = {"One-Hand", "单手"}, [14] = {"Shield", "盾牌"},
    [15] = {"Ranged", "远程"}, [16] = {"Back", "背部"}, [17] = {"Two-Hand", "双手"},
    [18] = {"Bag", "背包"}, [19] = {"Tabard", "战袍"}, [20] = {"Robe", "长袍"},
    [21] = {"Main Hand", "主手"}, [22] = {"Off Hand", "副手"},
    [23] = {"Held in Off-hand", "副手物品"}, [24] = {"Ammo", "弹药"},
    [25] = {"Thrown", "投掷"}, [26] = {"Ranged", "远程"}, [28] = {"Relic", "圣物"},
}
local T_BOND = {
    [1] = {"Binds when picked up", "拾取后绑定"},
    [2] = {"Binds when equipped", "装备后绑定"},
    [3] = {"Binds when used", "装备时绑定"},
}
local T_BOND_RAW = {
    ["Quest Item"] = {"Quest Item", "任务物品"},
}
local T_STAT = {
    Agility = {"Agility", "敏捷"}, Strength = {"Strength", "力量"},
    Stamina = {"Stamina", "耐力"}, Intellect = {"Intellect", "智力"},
    Spirit = {"Spirit", "精神"}, Health = {"Health", "生命值"},
    Mana = {"Mana", "法力值"},
    Defense = {"Defense", "防御技能"}, DefenseSkill = {"Defense", "防御技能"},
    SpellDamage = {"Spell Damage", "法术伤害"}, SpellPower = {"Spell Damage", "法术伤害"},
    Healing = {"Healing", "治疗效果"}, HealingPower = {"Healing", "治疗效果"},
    HitRating = {"Melee Hit", "近战命中"}, CritRating = {"Melee Crit", "近战爆击"},
    HasteRating = {"Haste", "急速"},
    ArcaneResistance = {"Arcane Resistance", "奥术抗性"},
    FireResistance = {"Fire Resistance", "火焰抗性"},
    FrostResistance = {"Frost Resistance", "冰霜抗性"},
    NatureResistance = {"Nature Resistance", "自然抗性"},
    ShadowResistance = {"Shadow Resistance", "暗影抗性"},
}
local T_RES = {
    Holy = {"Holy Resistance", "神圣抗性"}, Fire = {"Fire Resistance", "火焰抗性"},
    Nature = {"Nature Resistance", "自然抗性"}, Frost = {"Frost Resistance", "冰霜抗性"},
    Shadow = {"Shadow Resistance", "暗影抗性"}, Arcane = {"Arcane Resistance", "奥术抗性"},
}
local T_DMG = {
    Physical = {"Damage", "伤害"}, Holy = {"Holy Damage", "神圣伤害"},
    Fire = {"Fire Damage", "火焰伤害"}, Nature = {"Nature Damage", "自然伤害"},
    Frost = {"Frost Damage", "冰霜伤害"}, Shadow = {"Shadow Damage", "暗影伤害"},
    Arcane = {"Arcane Damage", "奥术伤害"},
}
local T_TRIGGER = {
    ["装备："] = {"Equip: ", "装备："},
    ["击中时可能："] = {"Chance on hit: ", "击中时可能："},
    ["使用："] = {"Use: ", "使用："},
    ["装备"] = {"Equip: ", "装备："},
}

local function pick2(map, key)
    local v = map[key]
    if type(v) == "table" then return v end
    return { tostring(key), tostring(key) }
end

local function fmtMoney(c, en)
    c = tonumber(c) or 0
    local g = math.floor(c / 10000); c = c % 10000
    local s = math.floor(c / 100); c = c % 100
    local parts = {}
    if g > 0 then parts[#parts + 1] = g .. (en and "g" or "金") end
    if s > 0 then parts[#parts + 1] = s .. (en and "s" or "银") end
    if c > 0 or #parts == 0 then parts[#parts + 1] = c .. (en and "c" or "铜") end
    return table.concat(parts, " ")
end

local function dpsOf(det)
    if not det.dg or not det.dl or det.dl <= 0 then return nil end
    local sum = 0
    for _, d in ipairs(det.dg) do sum = sum + (d[1] + d[2]) / 2 end
    return sum / (det.dl / 1000)
end

-- entry -> { {text,r,g,b}, ... }：纯函数便于测试；OnEnter 只负责展示
local function itemTooltipLines(entry, lang)
    local out = {}
    local function add(t, r, g, b) out[#out + 1] = { text = t, r = r, g = g, b = b } end
    local it = EL_Items and EL_Items[entry]
    if not it then return out end
    local en = (lang == "en")
    local r, g, b = qColor(it[3])
    add(itemName(entry, lang) or ("item" .. entry), r, g, b)
    local det = it[5]
    if type(det) ~= "table" then
        add(L("品质 ") .. (QUALITY_NAME[lang][it[3]] or tostring(it[3])), 0.8, 0.8, 0.8)
        local srcs = getSources(entry)
        if srcs[1] then
            add(L("掉落自") .. ": " .. (creatureName(srcs[1], lang) or "?"), 0.6, 0.6, 0.6)
        end
        add(L("游戏内未见过该物品"), 0.5, 0.5, 0.5)
        return out
    end
    -- 唯一 / 绑定
    if det.mc and det.mc > 1 then
        add(L("唯一"), 1, 0.1, 0.1)
    end
    if type(det.b) == "number" then
        local bd = pick2(T_BOND, det.b)
        add(en and bd[1] or bd[2], 1, 1, 1)
    elseif type(det.b) == "string" then
        local raw = T_BOND_RAW[det.b]
        add(raw and (en and raw[1] or raw[2]) or det.b, 1, 1, 1)
    end
    -- 类别 / 装备位
    if det.c then
        local cls = pick2(T_CLASS, det.c)
        local sub = nil
        if det.c == 2 then sub = T_SUB_WEAPON[det.sc]
        elseif det.c == 4 then sub = T_SUB_ARMOR[det.sc] end
        local inv = (det.inv and det.inv > 0) and T_INV[det.inv] or nil
        if sub then
            add(en and sub[1] or sub[2], 1, 1, 1)
        elseif det.c ~= 2 then
            add(en and cls[1] or cls[2], 1, 1, 1)
        end
        if inv then
            add(en and inv[1] or inv[2], 1, 1, 1)
        end
    end
    -- 伤害/攻速/DPN 或 护甲
    if det.dg and det.dg[1] then
        for _, d in ipairs(det.dg) do
            local sk = pick2(T_DMG, d[3])
            add(d[1] .. " - " .. d[2] .. " " .. (en and sk[1] or sk[2]), 1, 1, 1)
        end
        local dps = dpsOf(det)
        if dps then
            add((en and "DPS " or "") .. string.format("%.1f", dps)
                .. (en and "" or " " .. "每秒伤害"), 1, 1, 1)
        end
        if det.dl then
            local spd = det.dl / 1000
            add((en and "Speed " or "速度 ") .. string.format("%.2f", spd), 1, 1, 1)
        end
    elseif det.ar then
        add(en and (det.ar .. " Armor") or ("护甲值 " .. det.ar), 1, 1, 1)
    end
    if det.bl then
        add(en and (det.bl .. " Block") or ("格挡值 " .. det.bl), 1, 1, 1)
    end
    -- 属性
    for _, sv in ipairs(det.st or {}) do
        local st = pick2(T_STAT, sv[1])
        add("+" .. sv[2] .. " " .. (en and st[1] or st[2]), 1, 1, 1)
    end
    -- 抗性
    for _, sv in ipairs(det.rs or {}) do
        local rs = pick2(T_RES, sv[1])
        add("+" .. sv[2] .. " " .. (en and rs[1] or rs[2]), 1, 1, 1)
    end
    -- 耐久 / 需求等级 / 物品等级
    if det.du then
        add(en and ("Durability " .. det.du .. " / " .. det.du)
            or ("耐久度 " .. det.du .. " / " .. det.du), 1, 1, 1)
    end
    if det.rl and det.rl > 0 then
        add(L("需要等级 ") .. det.rl, 1, 1, 1)
    end
    if det.il then
        add(en and ("Item Level " .. det.il) or ("物品等级 " .. det.il), 1, 1, 1)
    end
    -- 法术/触发
    for _, s in ipairs(det.spx or {}) do
        local trig = T_TRIGGER[s[1]]
        local prefix = trig and (en and trig[1] or trig[2]) or (s[1] or "")
        local nm = en and s[2] or s[3]
        local ds = en and s[4] or s[5]
        if ds and ds ~= "" then
            if nm and nm ~= "" and nm ~= ds then
                add(nm, 0.6, 0.6, 0.6)
            end
            add(prefix .. ds, 0.25, 1, 0.01)
        elseif nm and nm ~= "" then
            add(prefix .. nm, 0.25, 1, 0.01)
        end
    end
    -- 套装 / 随机附魔
    if det.set_zh or det.set_en then
        add(L("套装") .. ": " .. (en and (det.set_en or det.set_zh) or (det.set_zh or det.set_en)), 0.6, 0.8, 1)
    end
    if det.re then
        add("«" .. L("随机附魔") .. "»", 0.25, 1, 0.01)
    end
    -- 灰字描述
    if det.dx_zh or det.dx_en then
        add(en and (det.dx_en or det.dx_zh) or (det.dx_zh or det.dx_en), 1, 0.96, 0.41)
    end
    -- 出售价格 + 掉落来源
    if det.sp then
        add(L("出售价格") .. ": " .. fmtMoney(det.sp, en), 0.85, 0.85, 0.85)
    end
    local srcs = getSources(entry)
    if srcs[1] then
        add(L("掉落自") .. ": " .. (creatureName(srcs[1], lang) or "?"), 0.6, 0.6, 0.6)
    end
    return out
end

-- ============================================================ 主窗口状态

local frame, statusBar, langBtn, favBtn, qBtn, searchBox, backBtn, titleText
local navScroll, navRows          -- 左列
local itemScroll, itemRows        -- 右列
local viewMode = "browse"         -- browse | search | fav
local curZone, curCreature = nil, nil
local searchResults = nil
local ROW_H = 18
local NAV_VISIBLE, ITEM_VISIBLE = 23, 23
local navOffset, itemOffset = 0, 0   -- 自管滚动偏移（客户端 FauxScrollFrame_Update 对无滚动条模板崩溃）
local navCount, itemCount = 0, 0
local refresh   -- 前向声明：行工厂的 OnClick 闭包引用它（local 必须在闭包创建处可见）
local toggle    -- 前向声明：小地图按钮 OnClick 引用

-- ============================================================ 滚动（自管，无滚动条依赖）

local function clampOff(off, n, visible)
    local mx = n - visible
    if mx < 0 then mx = 0 end
    if off > mx then off = mx end
    if off < 0 then off = 0 end
    return off
end

local function resetOffsets()
    navOffset, itemOffset = 0, 0
end

local function wheelStep(delta, which)
    delta = tonumber(delta) or 0
    if which == "nav" then
        navOffset = clampOff(navOffset - delta, navCount, NAV_VISIBLE)
    else
        itemOffset = clampOff(itemOffset - delta, itemCount, ITEM_VISIBLE)
    end
    if refresh then refresh() end
end

local function wheelify(f, which)
    pcall(f.EnableMouseWheel, f, true)
    f:SetScript("OnMouseWheel", function()
        wheelStep(arg1, which)
    end)
end

-- ============================================================ 行工厂

local function highlightify(row)
    pcall(row.SetHighlightTexture, row, "Interface\\QuestFrame\\UI-QuestTitleHighlight")
    local ok, hl = pcall(row.GetHighlightTexture, row)
    if ok and hl then
        pcall(hl.SetAlpha, hl, 0.35)
    end
end

local function makeNavRow(idx)
    local row = CreateFrame("Button", "EmberLootNav" .. idx, frame)
    row:SetHeight(ROW_H)
    highlightify(row)
    local name = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    name:SetPoint("LEFT", row, "LEFT", 4, 0)
    name:SetPoint("RIGHT", row, "RIGHT", -4, 0)
    name:SetJustifyH("LEFT")
    row.name = name
    row:SetScript("OnClick", function()
        if viewMode ~= "browse" then return end
        if row.navType == "zone" then
            curZone = row.zid
            curCreature = nil
            resetOffsets()
            refresh()
        elseif row.navType == "back" then
            curZone, curCreature = nil, nil
            resetOffsets()
            refresh()
        elseif row.navType == "creature" then
            curCreature = row.cid
            itemOffset = 0
            refresh()
        end
    end)
    wheelify(row, "nav")
    return row
end

local function makeItemRow(idx)
    local row = CreateFrame("Button", "EmberLootItem" .. idx, frame)
    row:SetHeight(ROW_H)
    highlightify(row)
    local icon = row:CreateTexture(nil, "ARTWORK")
    icon:SetWidth(ROW_H - 4); icon:SetHeight(ROW_H - 4)
    icon:SetPoint("LEFT", row, "LEFT", 2, 0)
    icon:SetTexture("Interface\\Icons\\INV_Misc_QuestionMark")
    local name = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    name:SetPoint("LEFT", icon, "RIGHT", 4, 0)
    name:SetPoint("RIGHT", row, "RIGHT", -120, 0)
    name:SetJustifyH("LEFT")
    local meta = row:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    meta:SetPoint("RIGHT", row, "RIGHT", -2, 0)
    meta:SetTextColor(0.75, 0.75, 0.75)
    meta:SetJustifyH("RIGHT")
    row.icon, row.name, row.meta = icon, name, meta
    row:SetScript("OnEnter", function()
        local e = row.entry
        if not e then return end
        GameTooltip:SetOwner(row, "ANCHOR_RIGHT")
        local shown = false
        if itemCached(e) then
            shown = pcall(GameTooltip.SetHyperlink, GameTooltip, "item:" .. e)
        end
        if not shown then
            pcall(GameTooltip.ClearLines, GameTooltip)
            for _, ln in ipairs(itemTooltipLines(e, cfgReady().lang)) do
                GameTooltip:AddLine(ln.text, ln.r, ln.g, ln.b)
            end
        end
        pcall(GameTooltip.Show, GameTooltip)
    end)
    row:SetScript("OnLeave", function() pcall(GameTooltip.Hide, GameTooltip) end)
    row:SetScript("OnClick", function()
        local e = row.entry
        if not e then return end
        if IsShiftKeyDown() then
            local c = cfgReady()
            if c.fav[e] then c.fav[e] = nil else c.fav[e] = true end
            refresh()
        elseif ChatFrame1EditBox and ChatFrame1EditBox:IsVisible() then
            local nm = itemName(e, cfgReady().lang) or ("item" .. e)
            local link = string.format("|Hitem:%d|h[%s]|h|r", e, nm)
            pcall(ChatEdit_InsertLink, link)
        end
    end)
    wheelify(row, "item")
    return row
end

-- ============================================================ 行填充

local function setItemRow(row, d)
    local entry = d.entry
    row.entry = entry
    local it = EL_Items and EL_Items[entry]
    if not it then
        row.name:SetText("?" .. tostring(entry))
        row.name:SetTextColor(1, 1, 1)
        row.meta:SetText("")
        pcall(row.icon.SetTexture, row.icon, "Interface\\Icons\\INV_Misc_QuestionMark")
        return
    end
    local lang = cfgReady().lang
    local r, g, b = qColor(it[3])
    row.name:SetText(itemName(entry, lang) or "?")
    row.name:SetTextColor(r, g, b)
    local bits = {}
    if d.chance and d.chance > 0 then
        bits[#bits + 1] = string.format("%.0f%%", d.chance)
    end
    if d.max and d.min and d.max > 1 then
        bits[#bits + 1] = "x" .. d.min .. "-" .. d.max
    elseif d.min and d.min > 1 then
        bits[#bits + 1] = "x" .. d.min
    end
    if d.group and d.group > 0 then
        bits[#bits + 1] = L("组")
    end
    if d.quest then
        bits[#bits + 1] = L("任务")
    end
    if cfgReady().fav[entry] then
        bits[#bits + 1] = "*"
    end
    if d.srcName then
        bits[#bits + 1] = "|cff707070← " .. d.srcName .. "|r"
    end
    row.meta:SetText(table.concat(bits, " "))
    -- 图标：物品缓存优先（GetItemInfo 第 9 个返回值 = texture），否则数据库图标名，
    -- 都失败退问号。SetTexture 成功返回 1、失败 nil，pcall 后取第二个值判断
    local rets = { pcall(GetItemInfo, entry) }
    local set = false
    if rets[1] and type(rets[9]) == "string" and rets[9] ~= "" then
        local okr, r = pcall(row.icon.SetTexture, row.icon, rets[9])
        set = okr and r ~= nil and r ~= false
    end
    if not set then
        local okr, r = pcall(row.icon.SetTexture, row.icon, "Interface\\Icons\\" .. (it[4] or ""))
        set = okr and r ~= nil and r ~= false
    end
    if not set then
        pcall(row.icon.SetTexture, row.icon, "Interface\\Icons\\INV_Misc_QuestionMark")
    end
end

local function applyFilter(rows)
    local qmin = cfgReady().quality or 0
    if qmin <= 0 then return rows end
    local out = {}
    for _, d in ipairs(rows) do
        local it = EL_Items and EL_Items[d.entry]
        if it and (it[3] or 0) >= qmin then out[#out + 1] = d end
    end
    return out
end

-- ============================================================ 装配数据

local function creatureHasDrops(cid)
    return EL_Drops and EL_Drops[cid] and #EL_Drops[cid] > 0
end

local function getBossList(zid)
    local z = EL_Zones and EL_Zones[zid]
    if not z or type(z[4]) ~= "table" then return {} end
    local out = {}
    for _, cid in ipairs(z[4]) do
        if creatureHasDrops(cid) and EL_Creatures and EL_Creatures[cid] then
            out[#out + 1] = cid
        end
    end
    table.sort(out, function(a, b)
        local ca, cb = EL_Creatures[a], EL_Creatures[b]
        if (ca[4] or 0) ~= (cb[4] or 0) then return (ca[4] or 0) > (cb[4] or 0) end
        return (ca[3] or 0) > (cb[3] or 0)
    end)
    return out
end

local function zoneLootRows(zid)
    -- 聚合整个副本的物品：按品质降序、同名来源合并取最高掉率
    local best = {}
    for _, cid in ipairs(getBossList(zid)) do
        for _, r in ipairs(EL_Drops[cid] or {}) do
            local e = r[1]
            local cur = best[e]
            if (not cur) or r[2] > cur.chance then
                best[e] = { entry = e, chance = r[2], group = r[3], min = r[4], max = r[5],
                            quest = r[6] == 1, srcCid = cid }
            end
        end
    end
    local rows = {}
    for _, d in pairs(best) do rows[#rows + 1] = d end
    table.sort(rows, function(a, b)
        local qa = (EL_Items[a.entry] or {})[3] or 0
        local qb = (EL_Items[b.entry] or {})[3] or 0
        if qa ~= qb then return qa > qb end
        if (a.chance or 0) ~= (b.chance or 0) then return (a.chance or 0) > (b.chance or 0) end
        return (a.entry or 0) < (b.entry or 0)
    end)
    return rows
end

local function creatureLootRows(cid)
    local rows = {}
    for _, r in ipairs(EL_Drops[cid] or {}) do
        rows[#rows + 1] = { entry = r[1], chance = r[2], group = r[3], min = r[4],
                            max = r[5], quest = r[6] == 1 }
    end
    return rows
end

local function buildZoneNav()
    local lang = cfgReady().lang
    local out = {}
    for zid, z in pairs(EL_Zones or {}) do
        local bosses = getBossList(zid)
        if #bosses > 0 then
            out[#out + 1] = { zid = zid, name = zoneName(zid, lang), limit = z[3], bosses = #bosses }
        end
    end
    table.sort(out, function(a, b)
        if (a.limit or 0) ~= (b.limit or 0) then return (a.limit or 0) > (b.limit or 0) end
        return (a.name or "") < (b.name or "")
    end)
    return out
end

local function buildSearch(q)
    q = string.lower(q or "")
    if q == "" then return nil end
    local out = {}
    for entry, it in pairs(EL_Items or {}) do
        local a, b = string.lower(it[1] or ""), string.lower(it[2] or "")
        if string.find(a, q, 1, true) or string.find(b, q, 1, true) then
            out[#out + 1] = entry
        end
    end
    table.sort(out, function(x, y) return x < y end)
    if #out > 500 then
        local trim = {}
        for i = 1, 500 do trim[i] = out[i] end
        out = trim
    end
    return out
end

-- ============================================================ 刷新

local function updateScroll(_, n, visible, which)
    if which == "nav" then
        navOffset = clampOff(navOffset, n, visible)
        return navOffset
    else
        itemOffset = clampOff(itemOffset, n, visible)
        return itemOffset
    end
end

refresh = function()
    if not frame then return end
    local c = cfgReady()
    local lang = c.lang
    titleText:SetText("EmberLoot " .. VERSION)
    langBtn:SetText(lang == "zh" and "中" or "EN")
    favBtn:SetText(L("收藏"))
    qBtn:SetText(c.quality == 0 and L("品质:全部")
        or L("品质:") .. (QUALITY_NAME[lang][c.quality] or c.quality))
    backBtn:SetText(L("返回"))
    backBtn:Show()
    searchBox:SetText(searchBox:GetText())  -- 保持输入

    local leftRows = {}   -- {navType="zone"|"creature"|"back", ...}
    local rightRows = {}  -- {entry, chance, group, min, max, quest, srcCid}

    if viewMode == "browse" then
        if curZone == nil then
            for _, z in ipairs(buildZoneNav()) do
                leftRows[#leftRows + 1] = { navType = "zone", zid = z.zid, name = z.name,
                    limit = z.limit, bosses = z.bosses }
            end
            backBtn:Hide()
            statusBar:SetText(string.format(L("%d 个副本"), #leftRows))
        else
            leftRows[#leftRows + 1] = { navType = "back", name = "« " .. L("返回") }
            for _, cid in ipairs(getBossList(curZone)) do
                leftRows[#leftRows + 1] = { navType = "creature", cid = cid }
            end
            local rows
            if curCreature then
                rows = creatureLootRows(curCreature)
                statusBar:SetText((creatureName(curCreature, lang) or "?") .. " — "
                    .. string.format(L("%d 条掉落"), #rows))
            else
                rows = zoneLootRows(curZone)
                statusBar:SetText((zoneName(curZone, lang) or "?") .. " — "
                    .. string.format(L("%d 件物品"), #rows))
            end
            rightRows = rows
        end
    else
        -- search / fav：左列保持 zone 导航，右列放结果
        if curZone == nil then
            for _, z in ipairs(buildZoneNav()) do
                leftRows[#leftRows + 1] = { navType = "zone", zid = z.zid, name = z.name,
                    limit = z.limit, bosses = z.bosses }
            end
        else
            leftRows[#leftRows + 1] = { navType = "back", name = "« " .. L("返回") }
            for _, cid in ipairs(getBossList(curZone)) do
                leftRows[#leftRows + 1] = { navType = "creature", cid = cid }
            end
        end
        local src = (viewMode == "fav") and (function()
            local t = {}
            for entry in pairs(c.fav) do
                if EL_Items and EL_Items[entry] then t[#t + 1] = entry end
            end
            table.sort(t, function(a, b) return a < b end)
            return t
        end)() or (searchResults or {})
        for _, entry in ipairs(src) do
            rightRows[#rightRows + 1] = { entry = entry, chance = nil }
        end
        statusBar:SetText((viewMode == "fav" and L("收藏") or L("搜索")) .. " — "
            .. string.format(L("%d 条"), #rightRows))
    end

    -- ---- 左列渲染
    local navItems = {}
    for _, d in ipairs(leftRows) do
        local row = navItems
        navItems[#navItems + 1] = d
    end
    local nLeft = #leftRows
    navCount = nLeft
    local offLeft = updateScroll(navScroll, nLeft, NAV_VISIBLE, "nav")
    while #navRows < NAV_VISIBLE do navRows[#navRows + 1] = makeNavRow(#navRows + 1) end
    for i = 1, NAV_VISIBLE do
        local row = navRows[i]
        local d = leftRows[offLeft + i]
        if d then
            row:Show()
            if d.navType == "zone" then
                local limitTxt = d.limit and (d.limit .. (lang == "zh" and "人" or "p")) or ""
                row.name:SetText(d.name .. " |cff808080" .. limitTxt .. " · " .. d.bosses
                    .. (lang == "zh" and "首领" or " bosses") .. "|r")
                row.name:SetTextColor(1, 0.9, 0.6)
            elseif d.navType == "creature" then
                local cc = EL_Creatures[d.cid]
                local mark = (cc[4] or 0) >= 2 and "|cff00c0ff*|r " or ""
                row.name:SetText(mark .. (creatureName(d.cid, lang) or "?")
                    .. " |cff808080L" .. (cc[3] or "?") .. "|r")
                if curCreature == d.cid then
                    row.name:SetTextColor(0.6, 1, 0.6)
                else
                    row.name:SetTextColor(1, 1, 0.85)
                end
            else
                row.name:SetText(d.name)
                row.name:SetTextColor(0.9, 0.9, 0.9)
            end
            row.navType = d.navType
            row.zid = d.zid
            row.cid = d.cid
        else
            row:Hide()
        end
    end

    -- ---- 右列渲染
    rightRows = applyFilter(rightRows)
    local nRight = #rightRows
    itemCount = nRight
    local offRight = updateScroll(itemScroll, nRight, ITEM_VISIBLE, "item")
    while #itemRows < ITEM_VISIBLE do itemRows[#itemRows + 1] = makeItemRow(#itemRows + 1) end
    for i = 1, ITEM_VISIBLE do
        local row = itemRows[i]
        local d = rightRows[offRight + i]
        if d then
            row:Show()
            if not d.srcName then
                local srcs = getSources(d.entry)
                if viewMode ~= "browse" or not curCreature then
                    local srcCid = d.srcCid or srcs[1]
                    if srcCid then
                        d.srcName = creatureName(srcCid, lang)
                    end
                end
            end
            setItemRow(row, d)
        else
            row:Hide()
        end
    end
end

-- ============================================================ 建窗

local function makeBtn(text, w)
    local b = CreateFrame("Button", nil, frame, "UIPanelButtonTemplate")
    b:SetWidth(w or 34); b:SetHeight(22)
    b:SetText(text)
    return b
end

local function buildUI()
    if frame then return end
    frame = CreateFrame("Frame", "EmberLootFrame", UIParent)
    frame:SetWidth(720); frame:SetHeight(540)
    frame:SetPoint("CENTER", UIParent, "CENTER", cfgReady().x or 0, cfgReady().y or 0)
    frame:SetMovable(true)
    frame:EnableMouse(true)
    frame:RegisterForDrag("LeftButton")
    frame:SetScript("OnDragStart", function() pcall(frame.StartMoving, frame) end)
    frame:SetScript("OnDragStop", function()
        pcall(frame.StopMovingOrSizing, frame)
        local _, _, _, x, y = frame:GetPoint()
        local c = cfgReady()
        c.x, c.y = x, y
    end)
    frame:SetBackdrop({
        bgFile = "Interface\\DialogFrame\\UI-DialogBox-Background",
        edgeFile = "Interface\\DialogFrame\\UI-DialogBox-Border",
        tile = true, tileSize = 32, edgeSize = 32,
        insets = { left = 11, right = 12, top = 12, bottom = 11 },
    })
    frame:SetBackdropColor(0, 0, 0, 1)
    pcall(frame.SetFrameStrata, frame, "HIGH")

    titleText = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalLarge")
    titleText:SetPoint("TOP", frame, "TOP", 0, -16)

    local closeBtn = CreateFrame("Button", nil, frame, "UIPanelCloseButton")
    closeBtn:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -6, -6)

    langBtn = makeBtn("中", 34)
    langBtn:SetPoint("TOPRIGHT", frame, "TOPRIGHT", -32, -28)
    langBtn:SetScript("OnClick", function()
        local c = cfgReady()
        c.lang = (c.lang == "zh") and "en" or "zh"
        refresh()
    end)

    favBtn = makeBtn(L("收藏"), 60)
    favBtn:SetPoint("RIGHT", langBtn, "LEFT", -6, 0)
    favBtn:SetScript("OnClick", function()
        viewMode = (viewMode == "fav") and "browse" or "fav"
        resetOffsets()
        refresh()
    end)

    qBtn = makeBtn(L("品质:全部"), 100)
    qBtn:SetPoint("RIGHT", favBtn, "LEFT", -6, 0)
    qBtn:SetScript("OnClick", function()
        local c = cfgReady()
        c.quality = ((c.quality or 0) + 1) % 5
        itemOffset = 0
        refresh()
    end)

    searchBox = CreateFrame("EditBox", "EmberLootSearchBox", frame, "InputBoxTemplate")
    searchBox:SetWidth(170); searchBox:SetHeight(20)
    searchBox:SetPoint("TOPLEFT", frame, "TOPLEFT", 26, -30)
    searchBox:SetAutoFocus(false)
    searchBox:SetScript("OnEnterPressed", function()
        searchResults = buildSearch(searchBox:GetText())
        viewMode = searchResults and "search" or "browse"
        itemOffset = 0
        refresh()
        searchBox:ClearFocus()
    end)
    searchBox:SetScript("OnEscapePressed", function() searchBox:ClearFocus() end)

    backBtn = makeBtn(L("返回"), 52)
    backBtn:SetPoint("TOPLEFT", frame, "TOPLEFT", 26, -58)
    backBtn:SetScript("OnClick", function()
        if viewMode ~= "browse" then
            viewMode = "browse"
        elseif curCreature then
            curCreature = nil
            itemOffset = 0
        else
            curZone = nil
            resetOffsets()
        end
        refresh()
    end)

    -- 左列滚动区（无滚动条模板；滚轮由 wheelify 自管，防客户端 FauxScrollFrame 崩溃）
    navScroll = CreateFrame("ScrollFrame", "EmberLootNavScroll", frame, "FauxScrollFrameTemplateLight")
    navScroll:SetPoint("TOPLEFT", frame, "TOPLEFT", 26, -84)
    navScroll:SetWidth(230); navScroll:SetHeight(NAV_VISIBLE * ROW_H)
    wheelify(navScroll, "nav")

    -- 右列滚动区
    itemScroll = CreateFrame("ScrollFrame", "EmberLootItemScroll", frame, "FauxScrollFrameTemplateLight")
    itemScroll:SetPoint("TOPLEFT", frame, "TOPLEFT", 276, -84)
    itemScroll:SetWidth(416); itemScroll:SetHeight(ITEM_VISIBLE * ROW_H)
    wheelify(itemScroll, "item")

    -- 分隔线
    local sep = frame:CreateTexture(nil, "ARTWORK")
    sep:SetTexture("Interface\\Tooltips\\UI-Tooltip-Background")
    sep:SetVertexColor(0.5, 0.4, 0.2, 0.55)
    sep:SetPoint("TOPLEFT", frame, "TOPLEFT", 266, -84)
    sep:SetPoint("BOTTOMRIGHT", frame, "BOTTOMRIGHT", -264, 30)

    -- 行定位锚（行建在 frame 上，锚到各滚动区顶部，按行距铺开）
    navRows, itemRows = {}, {}
    for i = 1, NAV_VISIBLE do
        local row = makeNavRow(i)
        row:SetWidth(224)
        row:SetPoint("TOPLEFT", navScroll, "TOPLEFT", 2, -((i - 1) * ROW_H))
        row:Hide()
        navRows[i] = row
    end
    for i = 1, ITEM_VISIBLE do
        local row = makeItemRow(i)
        row:SetWidth(410)
        row:SetPoint("TOPLEFT", itemScroll, "TOPLEFT", 2, -((i - 1) * ROW_H))
        row:Hide()
        itemRows[i] = row
    end

    statusBar = frame:CreateFontString(nil, "OVERLAY", "GameFontNormalSmall")
    statusBar:SetPoint("BOTTOMLEFT", frame, "BOTTOMLEFT", 22, 18)
    statusBar:SetTextColor(0.8, 0.8, 0.8)

    frame.Refresh = refresh
end

-- ============================================================ 入口 / 命令

toggle = function()
    if frame and frame:IsVisible() then
        frame:Hide()
        return
    end
    buildUI()
    refresh()
    pcall(frame.Show, frame)
end

-- ============================================================ 小地图按钮（可拖拽环绕，点击开关）

local minimapBtn
local mmDrag, mmMoved = false, false
local MINIMAP_R_DEFAULT = 78

local function mmAtan2(y, x)
    local ok, r = pcall(math.atan2, y, x)
    if ok and r then return r end
    if x > 0 then return math.atan(y / x)
    elseif x < 0 and y >= 0 then return math.atan(y / x) + math.pi
    elseif x < 0 then return math.atan(y / x) - math.pi
    else return (y >= 0) and (math.pi / 2) or -(math.pi / 2) end
end

local function mmPlace()
    if not minimapBtn then return end
    local c = cfgReady()
    if type(c.mm) ~= "number" then c.mm = -0.8 end
    local r = tonumber(c.mmr) or MINIMAP_R_DEFAULT
    minimapBtn:ClearAllPoints()
    minimapBtn:SetPoint("CENTER", Minimap, "CENTER", math.cos(c.mm) * r, math.sin(c.mm) * r)
end

local function buildMinimapButton()
    if minimapBtn or not Minimap then return end
    minimapBtn = CreateFrame("Button", "EmberLootMinimapButton", Minimap)
    minimapBtn:SetFrameStrata("MEDIUM")
    minimapBtn:SetFrameLevel(8)
    minimapBtn:SetWidth(31)
    minimapBtn:SetHeight(31)
    minimapBtn:SetHighlightTexture("Interface\\Minimap\\UI-Minimap-ZoomButton-Highlight")
    local border = minimapBtn:CreateTexture(nil, "OVERLAY")
    border:SetWidth(53); border:SetHeight(53)
    border:SetTexture("Interface\\Minimap\\MiniMap-TrackingBorder")
    border:SetPoint("TOPLEFT", minimapBtn, "TOPLEFT")
    local icon = minimapBtn:CreateTexture(nil, "ARTWORK")
    icon:SetWidth(17); icon:SetHeight(17)
    icon:SetTexture("Interface\\Icons\\INV_Misc_Bag_11")
    icon:SetPoint("CENTER", minimapBtn, "CENTER", 1, -1)
    minimapBtn.icon = icon
    minimapBtn:SetScript("OnMouseDown", function()
        mmDrag = true
        mmMoved = false
    end)
    minimapBtn:SetScript("OnMouseUp", function() mmDrag = false end)
    minimapBtn:SetScript("OnUpdate", function()
        if not mmDrag then return end
        local mx, my = GetCursorPosition()
        local s = (Minimap.GetEffectiveScale and Minimap:GetEffectiveScale()) or UIParent:GetEffectiveScale() or 1
        local cx, cy = Minimap:GetCenter()
        local dx, dy = (mx or 0) / s - (cx or 0), (my or 0) / s - (cy or 0)
        if math.abs(dx) + math.abs(dy) > 4 then mmMoved = true end
        cfgReady().mm = mmAtan2(dy, dx)
        mmPlace()
    end)
    minimapBtn:SetScript("OnClick", function()
        if mmMoved then return end  -- 拖拽结束不算点击
        if toggle then toggle() end
    end)
    minimapBtn:SetScript("OnEnter", function()
        pcall(GameTooltip.SetOwner, GameTooltip, minimapBtn, "ANCHOR_LEFT")
        pcall(GameTooltip.ClearLines, GameTooltip)
        GameTooltip:AddLine("EmberLoot " .. VERSION, 0.4, 0.9, 1)
        GameTooltip:AddLine(L("点击打开掉落浏览器"), 0.8, 0.8, 0.8)
        pcall(GameTooltip.Show, GameTooltip)
    end)
    minimapBtn:SetScript("OnLeave", function() pcall(GameTooltip.Hide, GameTooltip) end)
    mmPlace()
end

SLASH_EMBERLOOT1 = "/el"
SLASH_EMBERLOOT2 = "/emberloot"
SlashCmdList["EMBERLOOT"] = function(msg)
    msg = string.lower(msg or "")
    local c = cfgReady()
    if string.find(msg, "zh", 1, true) then
        c.lang = "zh"
        if frame and frame:IsVisible() then refresh() end
    elseif string.find(msg, "en", 1, true) then
        c.lang = "en"
        if frame and frame:IsVisible() then refresh() end
    elseif string.find(msg, "fav", 1, true) then
        toggle()
        viewMode = "fav"
        refresh()
    else
        toggle()
    end
end

-- 登录提示
local loginFrame = CreateFrame("Frame", "EmberLootLoginFrame")
loginFrame:RegisterEvent("PLAYER_LOGIN")
loginFrame:SetScript("OnEvent", function()
    pcall(buildMinimapButton)
    local n, z = 0, 0
    if EL_Items then for _ in pairs(EL_Items) do n = n + 1 end end
    if EL_Zones then for _, zz in pairs(EL_Zones) do
        if zz[3] and zz[3] > 0 then z = z + 1 end
    end end
    DEFAULT_CHAT_FRAME:AddMessage("|cff00c0ffEmberLoot|r " .. VERSION .. " — "
        .. z .. L("个副本 / ") .. n .. L(" 件物品，") .. L("输入 /el 打开掉落浏览器"))
end)

-- 测试/调试钩子（sim_test 专用，零运行时开销）
EL_Debug = {
    tooltipLines = itemTooltipLines,
    fmtMoney = fmtMoney,
    dpsOf = dpsOf,
    version = VERSION,
}
