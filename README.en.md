# Annotated Map: Survivor's Notes — Resident Evil (1996)

English | [한국어](README.md)

A bilingual ASI map mod for the original Resident Evil PC release (GOG Japanese `Biohazard.exe` with [Classic REbirth 1.1.4](https://classicrebirth.com/index.php/re1cb-changelog/)). Shows room names, locked doors and required keys, key items, documents and maps, puzzles, common items, typewriters and item boxes.

- The status-screen map shows icons; the full-screen map opened with **Tab** (controller **START**) also shows names.
- Collected items, unlocked doors and solved puzzles disappear. Rooms with remaining items are tinted amber.
- Required keys appear on the unvisited side of locked doors. The full-screen map shows your position and facing direction.
- Supports Chris and Jill item placements, with Korean and English labels.

## Screenshots

### Full-screen map

| | Visited rooms | All rooms |
|---|---|---|
| Mansion 1F | ![Full-screen map — Mansion 1F — Visited rooms](docs/screenshots/en/full_map_mansion_1f_visited.png) | ![Full-screen map — Mansion 1F — All rooms](docs/screenshots/en/full_map_mansion_1f_all.png) |
| Mansion 2F | ![Full-screen map — Mansion 2F — Visited rooms](docs/screenshots/en/full_map_mansion_2f_visited.png) | ![Full-screen map — Mansion 2F — All rooms](docs/screenshots/en/full_map_mansion_2f_all.png) |

### Status-screen map

| | Visited rooms | All rooms |
|---|---|---|
| Mansion 2F | ![Status-screen map — Mansion 2F — Visited rooms](docs/screenshots/en/mini_map_mansion_2f_visited.png) | ![Status-screen map — Mansion 2F — All rooms](docs/screenshots/en/mini_map_mansion_2f_all.png) |

## Installation

1. Download `RE1-Annotated-Map-<version>.zip` from [Releases](https://github.com/eggu/resident-evil-annotated-map/releases). The `Source code` archives are not installable packages.
2. Close the game and copy the ZIP contents (`dsound.dll`, `scripts/`) into the folder containing `Biohazard.exe`, preserving the directory structure. No REbirth **MOD SELECTION** step is needed.
3. Classic REbirth must be installed separately. [Ultimate ASI Loader](https://github.com/ThirteenAG/Ultimate-ASI-Loader) v9.7.4 (MIT) is included as `dsound.dll`.
   - If Ultimate ASI Loader is already installed as `dsound.dll` (for example by REuncap), you can skip `dsound.dll`.
   - If a different `dsound.dll` (such as DSOAL) is present, do not overwrite it; copy the included `dsound.dll` as `winmm.dll` instead.

Upgrading from 1.1.0: delete `RE1.AnnotatedMap.dll` and `mod_annotated_map/` from the game folder. To keep your settings, move `mod_annotated_map/RE1.AnnotatedMap.ini` into `scripts/` in place of the default INI. For later upgrades, skip `scripts/RE1.AnnotatedMap.ini` when extracting, or back it up and restore it.

To uninstall, delete `scripts/RE1.AnnotatedMap.asi`, `.ini` and `.log`, and `dsound.dll` if no other ASI mod uses it. The mod does not modify the EXE or saves. Unsupported executables (timestamp other than `0x3642d468`) are left unpatched.

Compatible with the [Korean HD translation mod](https://github.com/eggu/resident-evil-korean-hd-translation).

## Controls

| Key | Action |
|---|---|
| Tab / controller START (Menu/Options) | Open or close the full-screen map while exploring and able to control the character, or from the status-screen map |
| Esc / cancel button | Close the full-screen map |
| Move forward/backward | Select floor |
| Move left/right | Select area |
| 0 | Toggle all annotations |
| 1 | Room names, typewriters and item boxes |
| 2 | Locked doors and keys |
| 3 | Key items and amber room tint |
| 4 | Documents and maps |
| 5 | Puzzles |
| 6 | Common items |
| 8 | Cycle visibility: visited rooms → revealed rooms (floor map acquired) → all rooms |
| 9 | Switch Korean / English |
| - / = (+), numpad - / + | Name size in 10% steps (50–150%) |
| Shift + those keys | Name opacity in 10% steps (10–100%) |

## Settings (`scripts/RE1.AnnotatedMap.ini`)

The archive includes a commented default configuration; the mod also creates display preferences if the file is missing. Close the game before editing the INI, then save and restart.

### Change the controller map button

Classic REbirth opens its settings screen with BACK by default. If START is bound to a game action, edit `scripts/RE1.AnnotatedMap.ini` and change `OpenPad=START` under `[Keys]` to an unused button, for example:

```ini
[Keys]
OpenPad=LS
```

`LS` means clicking the left stick. Other supported values are listed below; LT/RT triggers and button combinations are not supported. This setting is independent of the game's controller bindings. Set `OpenPad=NONE` to disable the controller shortcut and use `OpenKey=TAB` on the keyboard instead. These options already work in version 1.1.0; if your INI has no `[Keys]` section, add the example above. Save the file and restart the game.

### Display and key settings

Defaults: **English, name size 100%, opacity 70%, Rooms on, other categories off**. All remains enabled as the master switch. Keep your existing INI when upgrading to preserve its values. On the main keyboard, use the equal/plus key without Shift to increase size.

Both map views share full legend wording and current state. Pretendard Medium legend: body 20px, title 22px, outline 3px at the 4x reference scale. The status-screen legend uses the empty band below the HUD.

| Setting | Default | Description |
|---|---|---|
| `[Keys] OpenKey` | `TAB` | Keyboard toggle: one character, `ESC`, `TAB`, `SPACE`, `F1`–`F12`, a virtual key code such as `0x4D`, or `NONE` |
| `[Keys] OpenPad` | `START` | XInput toggle: `A B X Y LB RB START BACK LS RS UP DOWN LEFT RIGHT`, or `NONE` |
| `[Keys] CloseKey` | `ESC` | Keyboard close key |
| `[Keys] CloseOnCancel` | `1` | Close with the game's cancel button |
| `[AnnotatedMap] RoomTint` | `1` | Set to `0` to disable tinting rooms with remaining items |
| `[AnnotatedMap] NameSize` | `100` | Name size (50–150); 100 is the original size |
| `[AnnotatedMap] NameOpacity` | `70` | Label opacity (10–100) |
| `[Calibration] OffsetX/OffsetY/Z` | | Status-screen annotation position and depth correction |
| `[Calibration] ArrowRotation` | `0` | Character arrow rotation correction in degrees |

Changes and validation status: [Korean / English release notes](RELEASE_NOTES.md).


Larger names keep their existing anchors and may overlap. The new HUD layout, physical keys, GPU alpha and long-session gameplay have not yet been verified in game.

## Build

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export RE1_GAME_DIR="/path/to/Resident Evil"   # GOG Japanese game folder containing Biohazard.exe and jpn/
.venv/bin/python build.py --package           # wiki → assets → DLL → native tests → dist/ ZIP
```

Omitting font options uses the bundled open-source fonts: Pretendard for body text, Noto Serif for the English title, and Nanum Myeongjo for the Korean title. Override any of them at build time:

```sh
.venv/bin/python build.py --package --font "/path/to/body.ttf" \
  --title-font-en "/path/to/title-en.ttf" --title-font-ko "/path/to/title-ko.ttf"
```

Unspecified options retain their defaults. Choose fonts with Korean glyphs for Korean text. Fonts are rasterized during the build, so changing them requires rebuilding. Invalid paths or unreadable fonts stop the build. Check custom font licenses before distributing a build.

- Add `--extract` to regenerate data. This requires all `ROOM*.RDT` files and `refs/evilresource/pages/*.html` ([evilresource.com/resident-evil](https://www.evilresource.com/resident-evil) room pages). References: [RE1-Mod-SDK](https://github.com/Gemini-Loboto3/RE1-Mod-SDK), [biorand/classic](https://github.com/biorand/classic), [biorand/biohazard-utils](https://github.com/biorand/biohazard-utils).
- Manually maintained data lives in `data/curated.json` (puzzles, event items and room-name corrections) and `data/items.json` (item names).
- `tests/test_native.py` runs the real EXE and built DLL in Unicorn to check patches, flag conditions, map input and drawing commands. `tools/audit_fit.py` checks room world-to-map transforms.

Research and implementation notes are available in the [wiki](docs/wiki/README.md).

## License

Source code is licensed under the [MIT License](LICENSE). This is an unofficial fan mod, unaffiliated with Capcom or Classic REbirth. See [NOTICE](NOTICE.md) for references and font licenses.
