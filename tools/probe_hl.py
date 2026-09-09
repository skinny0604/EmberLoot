# -*- coding: utf-8 -*-
from lupa import lua51
L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(r"""
local function stub(name)
    local t = { _name = name, _scripts = {}, _text = "" }
    if name then REG_STORE(name, t) end
    return t
end
REG = {}
REG_STORE = function(n, t) REG[n] = t end
local function makeframe(name)
    local t = stub(name)
    setmetatable(t, {
        __index = function(self, k)
            print("  __index k=" .. tostring(k))
            if k == "GetHighlightTexture" then
                return function(s)
                    s._hl = s._hl or stub(s._name and (s._name .. "_hl") or nil)
                    return s._hl
                end
            end
            return function(s, ...) return nil end
        end,
    })
    return t
end
CreateFrame = function(ftype, name) return makeframe(name) end
local row = CreateFrame("Button", "R1")
local ok, hl = pcall(row.GetHighlightTexture, row)
print("pcall ok:", ok, "type(hl):", type(hl))
print("hl is function?", type(hl) == "function")
if type(hl) == "function" then
    local ok2, hl2 = pcall(hl, row)
    print("calling method directly:", ok2, type(hl2))
end
local ok3, err3 = pcall(function() pcall(hl.SetAlpha, hl, 0.35) end)
print("SetAlpha step:", ok3, err3)
""")
