# EmberLoot

English | [中文](README.md)

**Dungeon & raid loot browser for Emberveil** (AtlasLoot-style) · For the Emberveil client (WoW 1.12.1 emulation / Lua 5.1 API) · Current version 0.2.0

![EmberLoot](docs/preview.png)

## Features

- **Instance → boss → loot table** three-level browsing: bundles 8 released instances (Scarlet Monastery, Deadmines, BRD, Stratholme, Molten Core, Onyxia's Lair etc. — grows with the official database), 64 bosses/elites + 8 zone trash-pool entries, **3809 items / 9256 drop rows** (bilingual names)
- Items colored by quality (Poor→Legendary), with icons, drop chance, multi-drop group markers ("one of N"), and quest-item markers
- **Item stat tooltips**: hover any item to see item level / required level, binding, armor / damage / DPS / speed, stats and resistances, durability, on-use & on-hit spells, sets, sell price (0.2.0 bundles full stat data — no in-game cache needed)
- **Minimap button**: snaps around the minimap, draggable, click to toggle the browser
- **Search** in both Chinese and English names; **quality filter** (all / uncommon+ / rare+ / epic+)
- **Favorites**: Shift+click an item to favorite; dedicated favorites view
- Click an item while the chat edit box is open to insert its item link
- **Bilingual**: `/el zh` / `/el en` toggles the UI; both name datasets are bundled
- Draggable window with position memory; zero third-party libraries

## Install

1. Download `EmberLoot-0.2.0.zip` and extract it
2. Put the whole `EmberLoot` folder into `...\Emberveil\live\Azeroth\Interface\AddOns\`
3. Re-login; when chat prints `EmberLoot 0.2.0 — N instances / M items` you are set

## Commands

| Command | Effect |
|---|---|
| `/el` or `/emberloot` | Toggle the loot browser |
| `/el zh` / `/el en` | Switch UI language |
| `/el fav` | Open and show favorites |

## Usage

- Left pane: instance list (player limit + boss count) → boss list (with level; `*` = rare elite / boss)
- Right pane: items — click a boss for its drops; without a selection you get the aggregated instance loot table (sorted by quality then chance, with drop sources)
- Shift+click = toggle favorite; click with chat box open = insert item link

## Data & updates

`tools/crawl.py` crawls [database.emberveil.org](https://database.emberveil.org) offline (bilingual fetches; drop rows include chance/group/counts) and generates the compact Lua table `EmberLoot/data.lua`. When the server adds content, re-run the crawler to refresh.

## License

MIT License
