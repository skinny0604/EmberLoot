## EmberLoot 0.2.0

AtlasLoot 式副本掉落浏览器（Emberveil 客户端，WoW 1.12.1 / Lua 5.1 API）。
AtlasLoot-style dungeon loot browser (Emberveil client, WoW 1.12.1 / Lua 5.1 API).

![EmberLoot](https://raw.githubusercontent.com/skinny0604/EmberLoot/main/docs/preview.png)

### 0.2.0 新增 / New

- **物品属性 tooltip**：悬停物品即可查看完整属性——物品等级、需求等级、绑定类型、护甲/伤害/每秒伤害/攻速、属性（力量/敏捷/耐力/智力/精神等）、抗性、耐久度、触发法术（装备/击中时可能/使用）、套装、出售价格。属性数据全部内置于插件（双语），无需游戏内先"见过"该物品。
  **Item stat tooltips**: hover any item for full stats — item level, required level, binding, armor/damage/DPS/speed, base stats, resistances, durability, triggered spells (equip / chance on hit / use), sets, and sell price. All stat data ships inside the addon (bilingual), no in-game cache needed.
- **小地图按钮**：新增可拖拽的小地图按钮，沿小地图边缘吸附，左键点击直接开关掉落浏览器，位置自动记忆。
  **Minimap button**: a draggable minimap button that snaps around the minimap edge; left-click toggles the browser and the position is remembered.

### 说明 / Notes

- 属性数据采集自 database.emberveil.org 物品库（3800+ 物品，中英双语），由 `tools/crawl_items.py` 离线生成。
  Stat data was crawled from database.emberveil.org (3800+ items, bilingual) via `tools/crawl_items.py`.
- 已被客户端缓存的物品仍优先显示原生 tooltip；未缓存物品使用数据库自绘 tooltip。
  Items already cached by your client still show the native tooltip; uncached items use the built-in database tooltip.
