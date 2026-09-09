## EmberLoot 0.1.1

AtlasLoot 式副本掉落浏览器（Emberveil 客户端，WoW 1.12.1 / Lua 5.1 API）。
AtlasLoot-style dungeon loot browser (Emberveil client, WoW 1.12.1 / Lua 5.1 API).

![EmberLoot](https://raw.githubusercontent.com/skinny0604/EmberLoot/main/docs/preview.png)

### 0.1.1 修复 / Fixed

- **修复打开窗口即报错**：`UIPanelTemplates.lua:169 attempt to index local 'scrollBar' (a nil value)` —— Emberveil 客户端的 `FauxScrollFrame_Update` 对无滚动条模板（FauxScrollFrameTemplateLight）没有空值保护。滚动已改为插件自管偏移 + 滚轮驱动，不再调用任何 `FauxScrollFrame_*` API。
- Fixed the on-open error `attempt to index local 'scrollBar' (a nil value)` by replacing FauxScrollFrame_* calls with self-managed scroll offsets driven by mouse wheel.

### 功能 / Features

- 副本 → 首领 → 掉落表三级浏览；整副本聚合掉落表（按品质/掉率排序，标注来源）
- 物品品质染色 + 图标 + 掉率 + 一组多选 + 任务标记；悬停 tooltip
- 搜索（中英文）、品质过滤、收藏（Shift+点）、聊天框插链接
- 中英双语一键切换（`/el zh` / `/el en`）；零第三方库
- Instance→boss→loot browsing, quality colors & icons, tooltips, search, favorites, bilingual CN/EN UI

### 数据 / Data

8 个已开放副本 · 64 首领/精英 + 8 区域小怪掉落池 · 3809 件物品 · 9256 条掉落记录
8 released instances · 64 bosses/elites + 8 zone trash pools · 3809 items · 9256 drop rows
（数据来自 [database.emberveil.org](https://database.emberveil.org)，中英双名内置）

### 安装 / Install

1. 下载 `EmberLoot-0.1.1.zip` 解压
2. `EmberLoot` 文件夹放进 `...\Emberveil\live\Azeroth\Interface\AddOns\`（覆盖旧版）
3. 重登游戏，聊天栏出现 `EmberLoot 0.1.1` 即成功；`/el` 打开

Full guide: [README.md（中文）](../blob/main/README.md) · [README_EN.md (English)](../blob/main/README_EN.md)
