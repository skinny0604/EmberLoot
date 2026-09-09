-- EmberLoot 0.1.0 —— Emberveil 掉落浏览器（AtlasLoot 式：副本→首领→掉落表）
-- 客户端：Emberveil UE5（1.12.1 / Lua 5.1 API）。零第三方库，OneJudge 同款 pcall 风格。
--
-- 数据（data.lua 生成）：
--   EL_Zones[zid]     = {"NameEn","名字Zh", 玩家人数上限, {cid,...}}
--   EL_Creatures[cid] = {"NameEn","名字Zh", 等级, rank, {zid,...}}
--   EL_Drops[cid]     = { {entry,chance,group,min,max,questFlag}, ... }
--   EL_Items[entry]   = {"NameEn","名字Zh", quality, "icon_纹理名"}
--
-- 命令：/el 或 /emberloot 开关窗口；/el zh|en 切语言；/el fav 只看收藏。
-- 交互：左列点副本→首领；右列始终是物品表；Shift+点物品=收藏；聊天框打开时点物品=插链接。

local VERSION = "0.1.0"

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

-- ============================================================ 主窗口状态

local frame, statusBar, langBtn, favBtn, qBtn, searchBox, backBtn, titleText
local navScroll, navRows          -- 左列
local itemScroll, itemRows        -- 右列
local viewMode = "browse"         -- browse | search | fav
local curZone, curCreature = nil, nil
local searchResults = nil
local ROW_H = 18
local NAV_VISIBLE, ITEM_VISIBLE = 23, 23
local refresh   -- 前向声明：行工厂的 OnClick 闭包引用它（local 必须在闭包创建处可见）

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
            refresh()
        elseif row.navType == "back" then
            curZone, curCreature = nil, nil
            refresh()
        elseif row.navType == "creature" then
            curCreature = row.cid
            refresh()
        end
    end)
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
            local it = EL_Items and EL_Items[e]
            if it then
                local r, g, b = qColor(it[3])
                GameTooltip:AddLine(itemName(e, cfgReady().lang) or "?", r, g, b)
                local qn = QUALITY_NAME[cfgReady().lang][it[3]] or tostring(it[3])
                GameTooltip:AddLine(L("品质 ") .. qn, 0.8, 0.8, 0.8)
                local srcs = getSources(e)
                if srcs[1] then
                    GameTooltip:AddLine(L("掉落自") .. ": " .. (creatureName(srcs[1], cfgReady().lang) or "?"),
                        0.6, 0.6, 0.6)
                end
                GameTooltip:AddLine(L("游戏内未见过该物品"), 0.5, 0.5, 0.5)
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

local function updateScroll(scroll, n, visible)
    FauxScrollFrame_Update(scroll, n, visible, ROW_H)
    return FauxScrollFrame_GetOffset(scroll)
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
    local offLeft = updateScroll(navScroll, nLeft, NAV_VISIBLE)
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
    local offRight = updateScroll(itemScroll, nRight, ITEM_VISIBLE)
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
        refresh()
    end)

    qBtn = makeBtn(L("品质:全部"), 100)
    qBtn:SetPoint("RIGHT", favBtn, "LEFT", -6, 0)
    qBtn:SetScript("OnClick", function()
        local c = cfgReady()
        c.quality = ((c.quality or 0) + 1) % 5
        refresh()
    end)

    searchBox = CreateFrame("EditBox", "EmberLootSearchBox", frame, "InputBoxTemplate")
    searchBox:SetWidth(170); searchBox:SetHeight(20)
    searchBox:SetPoint("TOPLEFT", frame, "TOPLEFT", 26, -30)
    searchBox:SetAutoFocus(false)
    searchBox:SetScript("OnEnterPressed", function()
        searchResults = buildSearch(searchBox:GetText())
        viewMode = searchResults and "search" or "browse"
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
        else
            curZone = nil
        end
        refresh()
    end)

    -- 左列滚动区
    navScroll = CreateFrame("ScrollFrame", "EmberLootNavScroll", frame, "FauxScrollFrameTemplateLight")
    navScroll:SetPoint("TOPLEFT", frame, "TOPLEFT", 26, -84)
    navScroll:SetWidth(230); navScroll:SetHeight(NAV_VISIBLE * ROW_H)
    navScroll:SetScript("OnVerticalScroll", function()
        FauxScrollFrame_OnVerticalScroll(navScroll, arg1, ROW_H, refresh)
    end)

    -- 右列滚动区
    itemScroll = CreateFrame("ScrollFrame", "EmberLootItemScroll", frame, "FauxScrollFrameTemplateLight")
    itemScroll:SetPoint("TOPLEFT", frame, "TOPLEFT", 276, -84)
    itemScroll:SetWidth(416); itemScroll:SetHeight(ITEM_VISIBLE * ROW_H)
    itemScroll:SetScript("OnVerticalScroll", function()
        FauxScrollFrame_OnVerticalScroll(itemScroll, arg1, ROW_H, refresh)
    end)

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

local function toggle()
    if frame and frame:IsVisible() then
        frame:Hide()
        return
    end
    buildUI()
    refresh()
    pcall(frame.Show, frame)
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
local loginFrame = CreateFrame("Frame")
loginFrame:RegisterEvent("PLAYER_LOGIN")
loginFrame:SetScript("OnEvent", function()
    local n, z = 0, 0
    if EL_Items then for _ in pairs(EL_Items) do n = n + 1 end end
    if EL_Zones then for _, zz in pairs(EL_Zones) do
        if zz[3] and zz[3] > 0 then z = z + 1 end
    end end
    DEFAULT_CHAT_FRAME:AddMessage("|cff00c0ffEmberLoot|r " .. VERSION .. " — "
        .. z .. L("个副本 / ") .. n .. L(" 件物品，") .. L("输入 /el 打开掉落浏览器"))
end)
