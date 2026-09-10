## EmberLoot 0.2.1

AtlasLoot 式副本掉落浏览器（Emberveil 客户端，WoW 1.12.1 / Lua 5.1 API）。
AtlasLoot-style dungeon loot browser (Emberveil client, WoW 1.12.1 / Lua 5.1 API).

![EmberLoot](https://raw.githubusercontent.com/skinny0604/EmberLoot/main/docs/preview.png)

### 0.2.1 修复 / Fixed

- **小地图按钮点击无反应**：修复拖拽判定基准错误——之前把「光标到小地图圆心的距离」误当拖拽位移，按钮本身就在圆周上，导致每次点击都被当成拖拽吞掉。现在以按下瞬间的光标位置为基准，轻点直接开关浏览器，拖拽照常吸附。
  **Minimap button not responding to clicks**: the drag detection mistakenly measured distance from the minimap center (the button itself sits on the circle), swallowing every click. Movement is now measured from the cursor position at press time — a plain click toggles the browser, dragging still snaps around the minimap.

### 0.2.1 数据更新 / Data refresh

- 官方数据库从 57 区域扩到 76 区域，本版全量跟进：**8 → 25 个副本/战场**，新增厄运之槌、玛拉顿、沉没的神庙、祖尔法拉克、黑石塔（上下层）、通灵学院、阿塔哈卡神庙、黑暗深渊、诺莫瑞根、剃刀高地/沼泽、厄运之槌东区等；物品 **3807 → 4567 件**、掉落记录 **9256 → 24551 条**。
  The official database grew from 57 to 76 zones; this release follows suit: **8 → 25 instances/battlegrounds** (Dire Maul, Maraudon, Sunken Temple, Zul'Farrak, Blackrock Spire, Scholomance, Sunken Temple, Blackfathom Deeps, Gnomeregan, Razorfen, and more), items **3807 → 4567**, drop rows **9256 → 24551**.
- 属性 tooltip 数据同步扩容（新增 760 件物品的双语属性详情）。
  Item stat tooltip data expanded accordingly (bilingual details for 760 new items).

### 说明 / Notes

- NAXX、安其拉（AQ/AQ20）、黑翼之巢的页面在官方数据库尚未填充生物数据，暂不入列；数据就绪后重跑采集器即可。
  Naxxramas, Ahn'Qiraj (AQ/AQ20) and Blackwing Lair have no creature data on the official database yet; they will appear once the source fills in.
- 0.2.0 的功能（物品属性 tooltip、搜索、收藏、品质过滤、双语）全部保留。
  All 0.2.0 features (item stat tooltips, search, favorites, quality filter, bilingual UI) are retained.
