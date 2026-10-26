# Classic REbirth 1.1.3 live check — 2026-10-26

The installed **Annotated Map 1.1.0** DLL ran under the official **Classic REbirth 1.1.3.0** in the existing game folder. This confirms the map core can run on 1.1.3; it does not certify every HD/controller combination. A concurrent 1.1.1 ASI packaging change is separate from this run.

## Confirmed in the running game

- The official 1.1.3 DLL loaded from the game folder; the map mod installed its guarded hooks with 409 markers and 588 bitmaps.
- The full-screen map opened and closed. Mansion 1F, Mansion 2F and Caves/Courtyard B1 rendered; area and floor navigation produced native map-action and composition logs.
- English and Korean names, icons, map terrain and legends appeared on actual GPU output.
- Visited → Revealed → All scope changes and master visibility on/off worked.
- Name size changed from 100 to 110 and name opacity from 70 to 80 with the keyboard shortcuts. Updated values were written to the INI and appeared in the legend.

Screenshots and raw logs are under the game folder's `diagnostics/rebirth113-test-20261026-104135/`. These are live window captures, not reconstructed previews.

## Wine setup used for this check

The existing app's Wine 10 Sikarugir engine, dgVoodoo 2.79 and bundled DXVK were used. Initial DirectX failures were environment failures before map rendering. A separate D3D11 device probe helped establish a working renderer before the map checks.

- REbirth remained the native `ddraw.dll`; `re_ddraw.dll` was dgVoodoo, with its D3D helper available as `d3dim.dll`.
- dgVoodoo used `d3d11_fl10_0` output and 256 MB emulated VRAM.
- The app's bundled 32-bit DXVK D3D11/DXGI PE files were selected. Their DOS-stub Wine-builtin markers were cleared only in the temporary test copies so Wine would load those PE files instead of its stock builtin code. Function-entry bytes and a successful hardware D3D11 feature-level-10.0 device probe confirmed the selected route.
- A private MoltenVK ICD JSON used an absolute library path and disabled portability-driver filtering for this legacy Wine client. The app's original ICD JSON was not edited.
- Other SDK/ASI mods and the external HD loader were excluded from this baseline.

Original DLLs/configuration and Wine renderer files were backed up before modification; `restore-114.py` in the diagnostics folder restores only this test's changed files. Registry snapshots were retained for recovery, but no explicit registry setting was edited and unrelated registry state is not automatically rolled back.

## Still outside the verified scope

Physical controller delivery, the external HD loader/RE:Enhance/Korean translation combination, all game routes and long-session stability are not established by this run. The [official changelog](https://classicrebirth.com/index.php/re1cb-changelog/) identifies integrated HD Loader and multiple stackable mods as 1.1.4 additions. The existing native regression harness stubs REbirth and is not a substitute for live compatibility checks.

The current published requirement remains 1.1.4 until the supported scope and other package versions are updated separately.

## Artifact identity

- [Official previous-version download](https://classicrebirth.com/index.php/download/resident-evil-dll-fix-for-classic-edition/): `re1cr-2020-12-06.7z`, SHA256 `9234c80aa030518375ae55440cf088b8f2ebec32c78f0ca5362fade6ad363e32`.
- Official 1.1.3 DLL SHA256: `6c17ec863c17b2834cfd1f802c4dac5fdc4e146f516671559ad5b9e0f4948019`.
- Original 1.1.4 DLL SHA256: `144764bf113d0f19767a9f2e35927b30ccfbb978790a427189583544b6c52889`.
- Map DLL tested SHA256: `77f92652ea62d3a88240236f7c77420d1b5a9d0ea91a997d442718f3d5c10285`.
