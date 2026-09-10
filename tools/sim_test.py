# -*- coding: utf-8 -*-
"""Smoke-test EmberLoot.lua under a stubbed WoW 1.12 API (lupa Lua 5.1)."""
import sys
from lupa import lua51

ADDON = r"D:\workspace\emberloot\EmberLoot\EmberLoot.lua"
DATA = r"D:\workspace\emberloot\EmberLoot\data.lua"

L = lua51.LuaRuntime(unpack_returned_tuples=True)

harness = r"""
-- ===== WoW API stubs =====
local REG = {}
local function stub(name)
    local t = { _name = name, _scripts = {}, _text = "", _kids = {} }
    if name then REG[name] = t end
    return t
end
local function fontstub()
    local t = { _text = "" }
    return setmetatable(t, { __index = function(_, k)
        if k == "GetText" then return function(s) return s._text end end
        if k == "SetText" then return function(s, v) s._text = tostring(v or "") end end
        return function() return nil end
    end })
end
local function makeframe(name)
    local t = stub(name)
    t._textures = {}
    setmetatable(t, {
        __index = function(self, k)
            if type(k) == "string" and string.sub(k, 1, 1) == "_" then return nil end
            if k == "GetText" then return function(s) return s._text end end
            if k == "SetText" then return function(s, v) s._text = tostring(v or "") end end
            if k == "GetPoint" then return function() return nil, nil, nil, 0, 0 end end
            if k == "IsVisible" then return function() return true end end
            if k == "IsShown" then return function() return true end end
            if k == "SetTexture" then return function() return 1 end end
            if k == "GetHighlightTexture" then
                return function(s)
                    s._hl = s._hl or stub(s._name and (s._name .. "_hl") or nil)
                    return s._hl
                end
            end
            if k == "SetScript" then
                return function(s, kind, fn) s._scripts[kind] = fn end
            end
            if k == "GetScript" then return function(s, kind) return s._scripts[kind] end end
            if k == "CreateTexture" then
                return function(s)
                    local tx = makeframe(nil)
                    function tx:SetTexture() return 1 end
                    s._textures[#s._textures + 1] = tx
                    return tx
                end
            end
            if k == "CreateFontString" then
                return function(s)
                    local fs = makeframe(nil)
                    s._fs[#s._fs] = s._fs[#s._fs] or {}
                    table.insert(s._fs, fs)
                    return fs
                end
            end
            return function(s, ...) return nil end   -- generic no-op method
        end,
    })
    return t
end

UIParent = makeframe("UIParent")
GameTooltip = makeframe("GameTooltip")
function GameTooltip:NumLines() return 1 end
DEFAULT_CHAT_FRAME = makeframe("ChatFrame")
function DEFAULT_CHAT_FRAME:AddMessage(msg) print("CHAT: " .. tostring(msg)) end
ChatFrame1EditBox = nil
function ChatEdit_InsertLink() end
function IsShiftKeyDown() return false end
function FauxScrollFrame_Update() end
function FauxScrollFrame_GetOffset() return 0 end
function FauxScrollFrame_OnVerticalScroll() end
SlashCmdList = {}

CreateFrame = function(ftype, name, parent, template)
    local f = makeframe(name)
    f._fs = {}
    return f
end

-- ===== load addon =====
function LOADFILE(path)
    local f = io.open(path, "r")
    local src = f:read("*a")
    f:close()
    local fn, err = loadstring(src, "@" .. path)
    if not fn then error("COMPILE FAIL: " .. tostring(err)) end
    fn()
    return true
end

-- ===== test driver =====
local failures = {}
local function step(name, fn)
    local ok, err = pcall(fn)
    if ok then
        print("PASS " .. name)
    else
        print("FAIL " .. name .. " -> " .. tostring(err))
        table.insert(failures, name .. ": " .. tostring(err))
    end
end

LOADFILE(_G.DATA_PATH)

step("login message", function()
    -- fire nothing; just confirm data tables sane
    local n = 0
    for _ in pairs(EL_Items) do n = n + 1 end
    assert(n > 1000, "items too few: " .. n)
end)

step("open window (/el)", function()
    SlashCmdList["EMBERLOOT"]("")
    assert(REG["EmberLootFrame"], "frame not created")
end)

step("zone list rendered", function()
    local row = REG["EmberLootNav1"]
    assert(row, "no nav row")
    assert(row._scripts.OnClick, "nav row has no OnClick")
end)

step("click first zone -> boss list", function()
    local row = REG["EmberLootNav1"]
    row._scripts.OnClick()
    -- after refresh, nav rows now hold creatures; click first creature
    local c = REG["EmberLootNav1"]
    assert(c._scripts.OnClick, "creature row missing OnClick")
    c._scripts.OnClick()
end)

step("item rows show entries", function()
    local it = REG["EmberLootItem1"]
    assert(it and it._scripts.OnClick, "no item row")
    assert(it.entry and it.entry > 0, "item row has no entry")
end)

step("item hover (tooltip)", function()
    local it = REG["EmberLootItem1"]
    it._scripts.OnEnter()
    it._scripts.OnLeave()
end)

step("item click (no chatbox)", function()
    local it = REG["EmberLootItem1"]
    it._scripts.OnClick()
end)

step("lang toggle EN/ZH", function()
    local b = REG[langBtn and langBtn._name or ""]
    -- langBtn is a local; reach via frame children not possible -> drive via slash
    SlashCmdList["EMBERLOOT"]("en")
    SlashCmdList["EMBERLOOT"]("zh")
end)

step("quality cycle via /el (noop safe)", function()
    SlashCmdList["EMBERLOOT"]("")
    SlashCmdList["EMBERLOOT"]("")
end)

step("search via editbox", function()
    local sb = REG["EmberLootSearchBox"]
    assert(sb, "no search box")
    sb._text = "血"
    sb._scripts.OnEnterPressed()
    sb._text = "zzz_nomatch"
    sb._scripts.OnEnterPressed()
    sb._text = ""
    sb._scripts.OnEnterPressed()
end)

step("favorites view via slash", function()
    -- toggle fav by shift-click: emulate with IsShiftKeyDown true
    local realShift = IsShiftKeyDown
    IsShiftKeyDown = function() return true end
    local it = REG["EmberLootItem1"]
    it._scripts.OnClick()
    IsShiftKeyDown = realShift
    SlashCmdList["EMBERLOOT"]("fav")
    SlashCmdList["EMBERLOOT"]("")   -- close
    SlashCmdList["EMBERLOOT"]("")   -- reopen (state kept)
end)

step("mouse wheel scroll (self-managed offset)", function()
    local ns = REG["EmberLootNavScroll"]
    local is = REG["EmberLootItemScroll"]
    assert(ns and ns._scripts.OnMouseWheel, "nav scroll missing OnMouseWheel")
    assert(is and is._scripts.OnMouseWheel, "item scroll missing OnMouseWheel")
    local row = REG["EmberLootNav1"]
    assert(row and row._scripts.OnMouseWheel, "nav row missing OnMouseWheel")
    arg1 = -3; ns._scripts.OnMouseWheel()   -- 下滚 3 行
    arg1 = 3;  ns._scripts.OnMouseWheel()   -- 回滚
    arg1 = -99999; is._scripts.OnMouseWheel() -- 越界下滚（须被钳制不炸）
    arg1 = 99999;  is._scripts.OnMouseWheel() -- 越界上滚（须被钳制不炸）
    arg1 = nil; is._scripts.OnMouseWheel()  -- 空滚轮事件
end)

step("back button", function()
    local b = REG["EmberLootBack"]
    if b and b._scripts.OnClick then b._scripts.OnClick() end
end)

-- ===== 0.2.0：小地图按钮 + 属性 tooltip =====

step("login event builds minimap button", function()
    Minimap = makeframe("Minimap")
    function GetCursorPosition() return 500, 400 end
    local lf = REG["EmberLootLoginFrame"]
    assert(lf and lf._scripts.OnEvent, "login frame missing OnEvent")
    lf._scripts.OnEvent()
    local mb = REG["EmberLootMinimapButton"]
    assert(mb, "minimap button not created")
    assert(mb._scripts.OnClick and mb._scripts.OnUpdate and mb._scripts.OnEnter, "minimap handlers missing")
    mb._scripts.OnEnter()   -- tooltip 不炸
    mb._scripts.OnLeave()
end)

step("minimap drag math (OnUpdate)", function()
    local mb = REG["EmberLootMinimapButton"]
    -- 0.2.1 回归：按下后光标没动 -> 不算拖拽，点击必须生效
    GetCursorPosition = function() return 500, 400 end
    mb._scripts.OnMouseDown()
    mb._scripts.OnUpdate()   -- 光标未动，mmMoved 必须仍为 false
    mb._scripts.OnClick()    -- 若被误判拖拽（0.2.0 bug），这里会静默不 toggle
    mb._scripts.OnMouseUp()
    -- 真拖拽：光标移开 >4px -> 记录角度
    GetCursorPosition = function() return 560, 380 end
    mb._scripts.OnMouseDown()
    mb._scripts.OnUpdate()   -- GetCursorPosition -> 角度更新 + mmPlace 不炸
    mb._scripts.OnMouseUp()
    mb._scripts.OnUpdate()   -- 未拖拽状态 early-return
    local c = EL_Config
    assert(type(c.mm) == "number", "mm angle not stored after drag")
    GetCursorPosition = function() return 500, 400 end
end)

step("minimap click toggles window", function()
    local mb = REG["EmberLootMinimapButton"]
    mb._scripts.OnClick()    -- mmMoved=false -> toggle() 不炸
end)

step("tooltip: full detail lines (zh)", function()
    EL_Items[999001] = {"Test Sword", "测试之剑", 4, "inv_sword_39", {
        il = 80, rl = 60, c = 2, sc = 7, inv = 13, b = 1,
        st = {{"Agility", 5}, {"Stamina", 8}},
        rs = {{"Fire", 8}, {"Nature", 9}},
        dg = {{44, 115, "Physical"}, {16, 30, "Nature"}},
        dl = 1900, du = 125, sp = 255355,
        spx = {{"击中时可能：", "Lightning Bolt", "雷霆之怒", "deals 300 nature damage", "造成300点自然伤害"}},
    }}
    local lines = EL_Debug.tooltipLines(999001, "zh")
    local txt = {}
    for i, ln in ipairs(lines) do txt[i] = ln.text end
    txt = table.concat(txt, "\n")
    assert(string.find(txt, "测试之剑", 1, true), "zh name missing")
    assert(string.find(txt, "拾取后绑定", 1, true), "bonding missing")
    assert(string.find(txt, "44 - 115 伤害", 1, true), "damage missing")
    assert(string.find(txt, "每秒伤害", 1, true), "dps missing")
    assert(string.find(txt, "+8 耐力", 1, true), "stamina missing")
    assert(string.find(txt, "+9 自然抗性", 1, true), "nature resist missing")
    assert(string.find(txt, "击中时可能：造成300点自然伤害", 1, true), "spell proc missing")
    assert(string.find(txt, "25金 53银 55铜", 1, true), "money wrong: ")
    assert(string.find(txt, "物品等级 80", 1, true), "item level missing")
end)

step("tooltip: full detail lines (en)", function()
    local lines = EL_Debug.tooltipLines(999001, "en")
    local txt = {}
    for i, ln in ipairs(lines) do txt[i] = ln.text end
    txt = table.concat(txt, "\n")
    assert(string.find(txt, "Binds when picked up", 1, true), "en bonding missing")
    assert(string.find(txt, "44 - 115 Damage", 1, true), "en damage missing")
    assert(string.find(txt, "+8 Stamina", 1, true), "en stamina missing")
    assert(string.find(txt, "25g 53s 55c", 1, true), "en money wrong")
end)

step("tooltip: dps + money helpers", function()
    local d = EL_Debug.dpsOf({dg = {{44, 115, "Physical"}}, dl = 1900})
    assert(math.abs(d - 41.842105263) < 0.01, "dps wrong: " .. tostring(d))
    assert(EL_Debug.fmtMoney(0) == "0铜", "zero money")
    assert(EL_Debug.fmtMoney(10000) == "1金", "1g money")
    assert(EL_Debug.fmtMoney(105) == "1银 5铜", "mixed money: " .. EL_Debug.fmtMoney(105))
    assert(EL_Debug.fmtMoney(105, true) == "1s 5c", "mixed money en: " .. EL_Debug.fmtMoney(105, true))
end)

step("tooltip: detail-less fallback intact", function()
    EL_Items[999002] = {"Old Item", "旧物品", 1, "inv_misc_food_39"}
    local lines = EL_Debug.tooltipLines(999002, "zh")
    assert(lines[1] and string.find(lines[1].text, "旧物品", 1, true), "fallback name wrong")
    local found = false
    for _, ln in ipairs(lines) do
        if string.find(ln.text, "游戏内未见过该物品", 1, true) then found = true end
    end
    assert(found, "fallback hint missing")
end)

if #failures > 0 then
    error("SMOKE FAILURES: " .. table.concat(failures, " | "))
end
print("SMOKE ALL PASS")
"""

L.globals().DATA_PATH = ADDON
# data.lua must load first inside the same env
pre = L.eval("function(path) local f = io.open(path, 'r') local s = f:read('*a') f:close() "
             "local fn, err = loadstring(s, '@data.lua') if not fn then error(err) end fn() return true end")
pre(DATA)

harness_fn = L.eval("function() local f, err = loadstring(_G.HARNESS_SRC, '@harness') "
                    "if not f then error(err) end f() end")
L.globals().HARNESS_SRC = harness
try:
    harness_fn()
    print("SIM TEST: ALL GREEN")
except Exception as e:
    print("SIM TEST FAILED:", e)
    sys.exit(1)
