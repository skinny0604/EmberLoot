# -*- coding: utf-8 -*-
"""Integrity checks on data.lua: drop rows reference known items; zone creatures exist."""
from lupa import lua51

L = lua51.LuaRuntime(unpack_returned_tuples=True)
L.execute(open(r"D:\workspace\emberloot\EmberLoot\data.lua", encoding="utf-8").read())
check = L.eval("""
function()
    local missing_item, bad_rank, bad_level, no_zones = 0, 0, 0, 0
    local trash, bosses = 0, 0
    for cid, rows in pairs(EL_Drops) do
        for _, r in ipairs(rows) do
            if not EL_Items[r[1]] then missing_item = missing_item + 1 end
        end
    end
    for cid, c in pairs(EL_Creatures) do
        if type(c[3]) ~= "number" then bad_level = bad_level + 1 end
        if type(c[4]) ~= "number" then bad_rank = bad_rank + 1 end
        if type(c[5]) ~= "table" or #c[5] == 0 then no_zones = no_zones + 1 end
        if c[4] >= 2 then bosses = bosses + 1 elseif tostring(cid):find("^9000000") then trash = trash + 1 end
    end
    -- zone creature lists reference existing EL_Creatures?
    local dangling = 0
    for zid, z in pairs(EL_Zones) do
        for _, cid in ipairs(z[4]) do
            if not EL_Creatures[cid] then dangling = dangling + 1 end
        end
    end
    return missing_item, bad_level, bad_rank, no_zones, trash, bosses, dangling
end""")
missing, badl, badr, noz, trash, bosses, dangling = check()
print(f"missing item refs: {missing}")
print(f"bad level/rank fields: {badl}/{badr}")
print(f"creatures without zones: {noz}")
print(f"rank>=2 bosses: {bosses}, trash pools: {trash}")
print(f"dangling zone->creature refs: {dangling}")
