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
