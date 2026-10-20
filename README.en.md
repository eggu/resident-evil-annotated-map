# Annotated Map: Survivor's Notes — Resident Evil (1996)

English | [한국어](README.md)

An unofficial bilingual map mod for the original Resident Evil PC release (GOG Japanese `Biohazard.exe` with [Classic REbirth 1.1.4](https://classicrebirth.com/index.php/re1cb-changelog/)). Shows room names, locked doors and required keys, key items, documents and maps, puzzles, common items, typewriters and item boxes.

- The status-screen map shows icons; the full-screen map opened with **M** (controller **RB**) also shows names.
- Collected items, unlocked doors and solved puzzles disappear. Rooms with remaining items are tinted amber.
- Required keys appear on the unvisited side of locked doors. The full-screen map shows your position and facing direction.
- Supports Chris and Jill item placements, with Korean and English labels.

## Installation

1. Download `RE1-Annotated-Map-<version>.zip` from [Releases](https://github.com/eggu/resident-evil-annotated-map/releases). The `Source code` archives are not installable packages.
2. Close the game and copy the ZIP contents into the folder containing `Biohazard.exe`, preserving the directory structure.
3. Start the game and enable `Annotated Map: Survivor's Notes` in REbirth **MOD SELECTION**.

To uninstall, remove `mod_annotated_map/` and `RE1.AnnotatedMap.dll` from the game folder. The mod does not modify the EXE or saves. Unsupported executables (timestamp other than `0x3642d468`) are left unpatched.

Compatible with the [Korean HD translation mod](https://github.com/eggu/resident-evil-korean-hd-translation).

## Controls

| Key | Action |
|---|---|
| M / controller RB | Open or close the full-screen map while exploring and able to control the character |
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
| 7 | Switch between full-screen and status-screen maps |
| 8 | Cycle visibility: visited rooms → revealed rooms (floor map acquired) → all rooms |
| 9 | Switch Korean / English |

## Settings (`mod_annotated_map/RE1.AnnotatedMap.ini`)

Created on first launch; stores display preferences.

| Setting | Default | Description |
|---|---|---|
| `[Keys] OpenKey` | `M` | Keyboard toggle: one character, `ESC`, `TAB`, `SPACE`, `F1`–`F12`, a virtual key code such as `0x4D`, or `NONE` |
| `[Keys] OpenPad` | `RB` | XInput toggle: `A B X Y LB RB START BACK LS RS UP DOWN LEFT RIGHT`, or `NONE` |
| `[Keys] CloseKey` | `ESC` | Keyboard close key |
| `[Keys] CloseOnCancel` | `1` | Close with the game's cancel button |
| `[AnnotatedMap] RoomTint` | `1` | Set to `0` to disable tinting rooms with remaining items |
| `[AnnotatedMap] NameOpacity` | `70` | Label opacity (10–100) |
| `[Calibration] OffsetX/OffsetY/Z` | | Status-screen annotation position and depth correction |
| `[Calibration] ArrowRotation` | `0` | Character arrow rotation correction in degrees |

Changes and validation status: [Korean / English release notes](RELEASE_NOTES.md).

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
