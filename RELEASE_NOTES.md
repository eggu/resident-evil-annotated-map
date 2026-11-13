# Annotated Map: Survivor's Notes — 1.3.1

## English

**What's changed**

- **HD or SD is chosen more strictly.** With `DisplayMode=Auto`, HD mode is used only when Classic REbirth is installed (its `ddraw.dll` in the game folder) with `HDLoader=1`, and `RetroMode` and `LowResEnable` off in its `config.ini`. Every other case is SD mode.
- **Classic REbirth is now needed only for HD mode.** Without it, the mod starts in SD mode instead of refusing to start.
- The mode is chosen when the map is first drawn, so it follows the settings REbirth applies at startup.

**Upgrading**

Close the game and extract the ZIP over the old files. Keep your existing `scripts/RE1.AnnotatedMap.ini` (skip it when extracting, or back it up and restore it): your settings are kept.

Known limitations: see the README.

## 한국어

**바뀐 점**

- **HD·SD 선택 기준이 엄격해졌습니다.** `DisplayMode=Auto`에서는 Classic REbirth가 설치되어 있고(게임 폴더의 `ddraw.dll`) `config.ini`에서 `HDLoader=1`, `RetroMode`·`LowResEnable`이 꺼져 있을 때만 HD 모드이며, 그 밖의 모든 경우는 SD 모드입니다.
- **Classic REbirth는 이제 HD 모드에만 필요합니다.** 없으면 모드가 시작을 거부하지 않고 SD 모드로 시작합니다.
- 지도를 처음 그릴 때 모드를 정하므로 REbirth가 시작할 때 적용한 설정을 따릅니다.

**업그레이드**

게임을 종료하고 ZIP을 기존 파일 위에 풉니다. 기존 `scripts/RE1.AnnotatedMap.ini`는 건너뛰거나 백업 후 복원하세요. 설정은 그대로 유지됩니다.

알려진 제한은 README를 참고하세요.
