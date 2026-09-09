# -*- coding: utf-8 -*-
"""Local Lua 5.1 verification: compile-check addon sources, execute data.lua."""
import sys
from lupa import lua51

L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute("""
function COMPILE(src, name)
    local f, err = loadstring(src, name)
    if f then return true, nil else return false, err end
end
function COUNT_DATA()
    local z, c, d, i = 0, 0, 0, 0
    for _ in pairs(EL_Zones or {}) do z = z + 1 end
    for _ in pairs(EL_Creatures or {}) do c = c + 1 end
    for _ in pairs(EL_Drops or {}) do d = d + 1 end
    for _ in pairs(EL_Items or {}) do i = i + 1 end
    return z, c, d, i
end
""")

def compile_check(path):
    src = open(path, encoding="utf-8").read()
    return L.globals().COMPILE(src, "@" + path)

def run_data(path):
    L.execute(open(path, encoding="utf-8").read())
    return L.globals().COUNT_DATA()

if __name__ == "__main__":
    for p in sys.argv[1:]:
        if p.endswith("data.lua"):
            z, c, d, i = run_data(p)
            print(f"DATA OK: zones={z} creatures={c} drops={d} items={i}")
        else:
            ok, err = compile_check(p)
            print(("COMPILE OK: " if ok else "COMPILE FAIL: ") + p + ("" if ok else " -> " + str(err)))
