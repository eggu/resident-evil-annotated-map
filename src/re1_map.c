/* Annotated Map for original Resident Evil (GOG Biohazard.exe + Classic REbirth), loaded as an ASI plugin.
 * Draws room names, locked doors, items, files, puzzles, enemies and save points over the native status-screen map.
 * Native facts and data provenance: docs/wiki/01-native-map.md. No CRT; KERNEL32/USER32 only. */
#include <windows.h>
#include <stdint.h>
#include "overlay_data.h"

#define EXE_TIMESTAMP 0x3642d468u
#define EXE_IMAGE_SIZE 0x990000u
#define STATUS_FLG (*(volatile uint32_t *)0xC33090)
#define STAGE_NO (*(volatile uint8_t *)0xC386F0)
#define MAP_STATE ((volatile uint8_t *)0xB38DE0)       /* +5 map stage, +6 page, +7 current slot */
#define MAP_LOADED_PAGE (*(volatile uint8_t *)0xC2E93D) /* page+0x7c once loaded (0x43bfb0) */
#define MAP_SPRITE ((volatile int16_t *)0x4B1D58)       /* GsSPRITE: x@+4 y@+6, mx@+0x18 my@+0x1a, sx@+0x1c sy@+0x1e */
#define FLG_DOOR ((volatile uint32_t *)0xC38744)
#define FLG_PICKUP ((volatile uint32_t *)0xC3876C)
#define FLG_VISITED ((volatile uint32_t *)0xC387A0)
#define FLG_KILL ((volatile uint32_t *)0xC3874C)   /* enemy killed: em_set 0x4191b0 skips the spawn while set */
#define SLOT_SIZE 0x21c
#define TEX_SLOT ((unsigned char *)(0x6977a8 + 13 * SLOT_SIZE)) /* Add_sprt slot n=-2, upload idx 1 (as the Korean HD translation) */
#define TILE_TEX OV_TILE_TEX   /* overlay tiles: 32 PSX px at OV_SCALE texels each */
#define BG_TEX 256            /* background / terrain / outline textures */
#define TILE_PSX (TILE_TEX / OV_SCALE)
#define TILES_X (320 / TILE_PSX)
#define TILES_Y (256 / TILE_PSX)

static const unsigned char page_stage[11] = {0, 1, 1, 2, 2, 3, 3, 4, 4, 4, 4};  /* exe 0x4b1bf8 */
static const unsigned char stage_flag_base[5] = {0, 32, 63, 82, 100};          /* exe 0x4b1bc8 */

void *__cdecl memset(void *d, int c, size_t n) { unsigned char *p = d; while (n--) *p++ = (unsigned char)c; return d; }
void *__cdecl memcpy(void *d, const void *s, size_t n) { unsigned char *p = d; const unsigned char *q = s; while (n--) *p++ = *q++; return d; }

/* ---------- logging & settings */
static char ini_path[MAX_PATH], log_path[MAX_PATH];
static unsigned log_lines;
static void log_text(const char *s) {
    if (log_lines++ > 400) return;
    HANDLE h = CreateFileA(log_path, FILE_APPEND_DATA, FILE_SHARE_READ, NULL, OPEN_ALWAYS, 0, NULL);
    if (h == INVALID_HANDLE_VALUE) return;
    DWORD w; unsigned n = (unsigned)lstrlenA(s);
    WriteFile(h, s, n, &w, NULL); WriteFile(h, "\r\n", 2, &w, NULL); CloseHandle(h);
}
static void log_fmt(const char *fmt, int a, int b, int c, int d) { char buf[256]; wsprintfA(buf, fmt, a, b, c, d); log_text(buf); }

/* legend / key order: [0] all, [1] rooms, [2] locks, [3] key items, [4] files, [5] puzzles, [6] events, [7] common, [8] enemies */
enum { T_ALL, T_ROOMS, T_LOCKS, T_KEYS, T_DOCS, T_PUZZLES, T_EVENTS, T_COMMON, T_ENEMIES, T_COUNT };
static const char *const toggle_keys[T_COUNT] = {"All", "Rooms", "Locks", "KeyItems", "Documents", "Puzzles", "Events", "CommonItems", "Enemies"};
#define SETTINGS_VERSION 5   /* 1: up to 1.1.2 (no Version key); 2: icons, item names, legend fold, enemies, door-centre keys; 3 (candidate 14 only): ItemNames 0 all / 1 no common / 2 off; 4: ItemNames as RE1 HD / RE2 / RE3: 0 off / 1 all / 2 all but common; 5: legend renumbered ([6] events, scope [9], language [\\]) and [Colors]. Toggles are stored under category names, so the renumbering moves no value; version 5 only adds Events (default off) */
static int toggles[T_COUNT];
static int scope = 1, english = 1, offset_x, offset_y, overlay_z = 0x10, room_tint = 1;
static int arrow_rotation;   /* INI [Calibration] ArrowRotation (degrees) if the player-heading convention is off */
static int name_size = 100, name_opacity = 70, icon_size = 100, icon_opacity = 80, item_names = 2, legend_on = 1;   /* item_names: 0 all, 1 all but common items, 2 hidden */
__declspec(dllexport) volatile int ov_key_side;   /* INI KeySide; exported for tests/test_native.py */
__declspec(dllexport) volatile int ov_fullscreen;
__declspec(dllexport) int ov_zoom, ov_pan_x = 96, ov_pan_y = 112;
static int map_paint;
__declspec(dllexport) int ov_hd_on = 1;   /* INI HdIcons: HD-style icons on the full map (the status screen always keeps the pixel icons); exported for tests */
static int sd_mode, display_mode;   /* SD mode (src/sd_draw.h): 1x pixel markers and names; INI DisplayMode 0 Auto, 1 HD, 2 SD */
static int hd_off;   /* config.ini [DLL] HDLoader=0 or RetroMode=1: the x8 overlay textures cannot be sampled, only the notice is drawn */
static int notice_draw, notice_failed;
__declspec(dllexport) int ov_upload_budget = 12;   /* texture uploads per frame (INI UploadBudget); exported for tests */
static int zoomed(void) { return ov_fullscreen && ov_zoom; }
static int zoom_clamp(int v, int hi) { return v < 0 ? 0 : v > hi ? hi : v; }
static int clamp_range(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }
static int pending_save;   /* INI older than SETTINGS_VERSION (or missing): rewrite once, from the game loop, not DllMain */
static float name_alpha = 0.7f, icon_alpha = 0.8f, blink_alpha;   /* blink_alpha: visible share for arrows this frame */   /* name layer opacity; native semi-transparent sprites use 0.5 */
/* RE0 map mod rule: write a copy (keeping [Keys], [Calibration] and comments), then replace the INI in one rename;
 * on any failure the previous INI stays as it was and the failure is logged */
static void save_settings(void) {
    char v[12], tmp[MAX_PATH + 4];
    wsprintfA(tmp, "%s.tmp", ini_path);
    if (!CopyFileA(ini_path, tmp, FALSE) && GetFileAttributesA(ini_path) != INVALID_FILE_ATTRIBUTES) {
        log_text("Settings not saved: INI copy failed, previous INI kept"); return;
    }
    BOOL ok = TRUE;
    for (int i = 0; i < T_COUNT; i++) { v[0] = (char)('0' + toggles[i]); v[1] = 0; ok &= WritePrivateProfileStringA("AnnotatedMap", toggle_keys[i], v, tmp); }
    v[0] = (char)('0' + scope); ok &= WritePrivateProfileStringA("AnnotatedMap", "Scope", v, tmp);
    ok &= WritePrivateProfileStringA("AnnotatedMap", "Language", english ? "en" : "ko", tmp);
    wsprintfA(v, "%d", name_size); ok &= WritePrivateProfileStringA("AnnotatedMap", "NameSize", v, tmp);
    wsprintfA(v, "%d", name_opacity); ok &= WritePrivateProfileStringA("AnnotatedMap", "NameOpacity", v, tmp);
    wsprintfA(v, "%d", icon_size); ok &= WritePrivateProfileStringA("AnnotatedMap", "IconSize", v, tmp);
    wsprintfA(v, "%d", icon_opacity); ok &= WritePrivateProfileStringA("AnnotatedMap", "IconOpacity", v, tmp);
    v[0] = (char)('0' + (item_names == 0 ? 1 : item_names == 1 ? 2 : 0)); v[1] = 0;   /* INI: 0 off, 1 all, 2 all but common (the other map mods' meaning) */
    ok &= WritePrivateProfileStringA("AnnotatedMap", "ItemNames", v, tmp);
    ok &= WritePrivateProfileStringA("AnnotatedMap", "Legend", legend_on ? "1" : "0", tmp);
    ok &= WritePrivateProfileStringA("AnnotatedMap", "KeySide", ov_key_side ? "1" : "0", tmp);
    ok &= WritePrivateProfileStringA("AnnotatedMap", "DisplayMode", display_mode == 1 ? "HD" : display_mode == 2 ? "SD" : "Auto", tmp);
    ok &= WritePrivateProfileStringA("AnnotatedMap", "Zoom", NULL, tmp);   /* zoom is never persisted: the map always opens at 1x; drop a key written by candidates 7-9 */
    wsprintfA(v, "%d", SETTINGS_VERSION); ok &= WritePrivateProfileStringA("AnnotatedMap", "Version", v, tmp);
    if (!ok || !MoveFileExA(tmp, ini_path, MOVEFILE_REPLACE_EXISTING)) {
        DeleteFileA(tmp); log_text("Settings not saved: write/replace failed, previous INI kept");
    }
}
static int key_code(const char *v, int def);
static int pad_code(const char *v, int def);
static int open_vk, close_vk, open_pad, close_on_cancel, capture_vk, ctrl_mod;
static int clamp10(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : (v + 5) / 10 * 10; }
static void detect_hd_off(void) {   /* config.ini beside Biohazard.exe: [DLL] HDLoader / RetroMode (REbirth 1.1.4) */
    char cfg[MAX_PATH]; DWORD n = GetModuleFileNameA(NULL, cfg, MAX_PATH);
    while (n && n < MAX_PATH && cfg[n - 1] != '\\') n--;
    if (!n || n + 11 >= MAX_PATH) return;
    memcpy(cfg + n, "config.ini", 11);
    hd_off = GetPrivateProfileIntA("DLL", "HDLoader", 0, cfg) == 0 || GetPrivateProfileIntA("DLL", "RetroMode", 0, cfg) != 0;   /* a missing HDLoader counts as off */
}
/* [Colors]: one #RRGGBB per category. The legend CLUT (names and legend rows use it) is copied from the generated palette and the
 * category indices are overwritten before any upload; unset or invalid keys keep the generated colour. 5 bits per channel, rounded
 * (the generator's snap555 does the same, so a default typed here equals the baked colour). */
static unsigned short legend_pal[16];
static const char *const color_keys[8] = {"Rooms", "Locks", "KeyItems", "Files", "Puzzles", "Events", "CommonItems", "Enemies"};
static int hex_digit(char c) { return c >= '0' && c <= '9' ? c - '0' : (c | 32) >= 'a' && (c | 32) <= 'f' ? (c | 32) - 'a' + 10 : -1; }
static int parse_color(const char *v, unsigned *rgb) {   /* "#RRGGBB", optionally followed by a space / ';' comment */
    if (v[0] != '#') return 0;
    unsigned c = 0;
    for (int i = 1; i <= 6; i++) { int d = hex_digit(v[i]); if (d < 0) return 0; c = c << 4 | (unsigned)d; }
    if (v[7] && v[7] != ' ' && v[7] != ';' && v[7] != '\t') return 0;
    *rgb = c; return 1;
}
static unsigned short rgb555_of(unsigned rgb) {
    unsigned r = (rgb >> 16 & 255) * 31 + 127, g = (rgb >> 8 & 255) * 31 + 127, b = (rgb & 255) * 31 + 127;
    unsigned short c = (unsigned short)(0x8000 | (b / 255) << 10 | (g / 255) << 5 | r / 255);
    return (c & 0x7fff) ? c : (unsigned short)0x8421;   /* RGB zero is the renderer's colour key */
}
static void load_colors(void) {
    memcpy(legend_pal, ov_legend_palette, sizeof legend_pal);
    for (int i = 0; i < 8; i++) {
        char v[32]; unsigned rgb;
        GetPrivateProfileStringA("Colors", color_keys[i], "", v, sizeof v, ini_path);
        if (!v[0]) continue;
        if (parse_color(v, &rgb)) legend_pal[ov_color_index[i]] = rgb555_of(rgb);
        else { char msg[96]; wsprintfA(msg, "Colors: %s is not #RRGGBB; default kept", color_keys[i]); log_text(msg); }
    }
}
static void load_settings(void) {
    detect_hd_off();
    load_colors();
    for (int i = 0; i < T_COUNT; i++) toggles[i] = GetPrivateProfileIntA("AnnotatedMap", toggle_keys[i], i <= T_ROOMS, ini_path) != 0;
    scope = (int)GetPrivateProfileIntA("AnnotatedMap", "Scope", 1, ini_path);   /* 1 visited, 2 revealed, 3 all */
    if (scope < 1 || scope > 3) scope = 1;
    char lang[8]; GetPrivateProfileStringA("AnnotatedMap", "Language", "en", lang, sizeof lang, ini_path);
    english = !(lang[0] == 'k' && lang[1] == 'o');
    /* calibration knobs (PSX pixels / ordering-table depth); defaults match the native map sprite */
    offset_x = (int)GetPrivateProfileIntA("Calibration", "OffsetX", 0, ini_path);
    offset_y = (int)GetPrivateProfileIntA("Calibration", "OffsetY", 0, ini_path);
    overlay_z = (int)GetPrivateProfileIntA("Calibration", "Z", 0x10, ini_path);
    room_tint = GetPrivateProfileIntA("AnnotatedMap", "RoomTint", 1, ini_path) != 0;
    int opacity = (int)GetPrivateProfileIntA("AnnotatedMap", "NameOpacity", 70, ini_path);
    arrow_rotation = (int)GetPrivateProfileIntA("Calibration", "ArrowRotation", 0, ini_path);
    char k[16];
    GetPrivateProfileStringA("Keys", "OpenKey", "TAB", k, sizeof k, ini_path); open_vk = key_code(k, VK_TAB);
    GetPrivateProfileStringA("Keys", "OpenPad", "START", k, sizeof k, ini_path); open_pad = pad_code(k, 0x0010);
    GetPrivateProfileStringA("Keys", "CloseKey", "ESC", k, sizeof k, ini_path); close_vk = key_code(k, VK_ESCAPE);
    close_on_cancel = GetPrivateProfileIntA("Keys", "CloseOnCancel", 1, ini_path) != 0;

    GetPrivateProfileStringA("Keys", "CaptureKey", "F12", k, sizeof k, ini_path); capture_vk = key_code(k, VK_F12);
    GetPrivateProfileStringA("Keys", "Modifier", "SHIFT", k, sizeof k, ini_path);   /* icon keys: SHIFT (default) or CTRL */
    ctrl_mod = !lstrcmpiA(k, "CTRL") || !lstrcmpiA(k, "CONTROL");

    name_size = clamp10((int)GetPrivateProfileIntA("AnnotatedMap", "NameSize", 100, ini_path), 50, 150);
    name_opacity = clamp10(opacity, 10, 100);
    name_alpha = (float)name_opacity / 100.0f;  /* off if REbirth HD map replacement misbehaves */
    icon_size = clamp10((int)GetPrivateProfileIntA("AnnotatedMap", "IconSize", 100, ini_path), 50, 200);
    icon_opacity = clamp10((int)GetPrivateProfileIntA("AnnotatedMap", "IconOpacity", 80, ini_path), 10, 100);
    icon_alpha = (float)icon_opacity / 100.0f;
    ov_hd_on = GetPrivateProfileIntA("AnnotatedMap", "HdIcons", 1, ini_path) != 0;
    ov_upload_budget = zoom_clamp((int)GetPrivateProfileIntA("AnnotatedMap", "UploadBudget", 12, ini_path), 200);
    if (ov_upload_budget < 1) ov_upload_budget = 12;
    legend_on = GetPrivateProfileIntA("AnnotatedMap", "Legend", 1, ini_path) != 0;
    ov_key_side = GetPrivateProfileIntA("AnnotatedMap", "KeySide", 0, ini_path) != 0;   /* 0 door centre, 1 unvisited side */
    char dm[8]; GetPrivateProfileStringA("AnnotatedMap", "DisplayMode", "Auto", dm, sizeof dm, ini_path);
    display_mode = !lstrcmpiA(dm, "HD") ? 1 : !lstrcmpiA(dm, "SD") ? 2 : 0;
    sd_mode = display_mode == 2 || (display_mode == 0 && hd_off);
    if (sd_mode) { ov_key_side = 0; log_text("SD mode: 1x markers and names (HD textures off or DisplayMode=SD); size, opacity and item-name settings do not apply"); }
    else if (hd_off) log_text("WARNING: DisplayMode=HD but HD textures are off (config.ini [DLL] HDLoader=0 or RetroMode=1): only a notice is drawn. Use DisplayMode=Auto or SD.");
    else log_text("HD mode");
    /* Version: written on the next save. 1 -> 2 changes no scale (new keys take their defaults), so nothing is converted;
     * a later scale change converts here once, keyed on the old version. */
    int version = (int)GetPrivateProfileIntA("AnnotatedMap", "Version", 1, ini_path);
    /* ItemNames: versions 1-2: 0 off / 1 on; version 3 (candidate 14 only): 0 all / 1 all but common / 2 off; since 4: 0 off / 1 all /
     * 2 all but common. Internally item_names is the [H] cycle position: 0 all, 1 all but common, 2 off. A missing key means off. */
    int names = (int)GetPrivateProfileIntA("AnnotatedMap", "ItemNames", -1, ini_path);
    if (names < 0) item_names = 2;
    else if (version < 3) item_names = names ? 0 : 2;
    else if (version == 3) item_names = names > 2 ? 2 : names;
    else item_names = names == 1 ? 0 : names == 2 ? 1 : 2;
    if (version < SETTINGS_VERSION) { pending_save = 1; log_fmt("Settings version %d -> %d", version, SETTINGS_VERSION, 0, 0); }
}

/* ---------- game state */
static int flag_on(volatile uint32_t *arr, unsigned bit) { return (arr[bit >> 5] & (0x80000000u >> (bit & 31))) != 0; }
static int jill(void) { return (STATUS_FLG & 0x800000u) != 0; }  /* RDT suffix choice, exe 0x41b6e6 */
static int slot_visited(unsigned stage, unsigned slot) { return stage < 5 && flag_on(FLG_VISITED, stage_flag_base[stage] + slot); }
/* floor map picked up (native loader 0x43c001 -> 0x43cec0: Flg_7 bit 0x7C + n; Mansion B1 / Lab B1 / Lab B4 have none):
 * its rooms are "revealed" even before they are visited */
static const signed char map_bit[11] = {0, 1, -1, 2, 3, 4, 4, -1, 5, 5, -1};
static int page_revealed(unsigned page) { return page < 11 && map_bit[page] >= 0 && flag_on(FLG_VISITED, 0x7c + (unsigned)map_bit[page]); }
/* scope 1: visited rooms; 2: plus rooms revealed by a floor map; 3: every room. Room names always include revealed rooms. */
static int room_known(unsigned stage, unsigned slot, unsigned page, int name) {
    return scope == 3 || slot_visited(stage, slot) || ((scope == 2 || name) && page_revealed(page));
}

static const uintptr_t ck_group[10] = {0xC38790, 0xC38724, 0xC38744, 0xC3874C, 0xC33098, 0xC33090, 0xC3AB90, 0xC3876C, 0xC387A0, 0xAA7A80};
static int ck(unsigned group, unsigned bit) { return group < 10 && flag_on((volatile uint32_t *)ck_group[group], bit); }
/* Item placement guards from the room's init SCD (if ck(...)): shown only if some placement record would put the
 * item there now, e.g. Jill's Master Key only while Flg_1[91] is clear. Rows: group, bit, flags
 * (1 = needs set, 2 = negated guard / else branch, 4 = new guard, 8 = new alternative); 254 = unknown (passes). */
static int guards_pass(unsigned idx) {
    if (idx == 0xFFFF) return 1;
    int any_alt = 0, alt_ok = 0, guard_ok = 1, conds_ok = 1, neg = 0, started = 0;
    for (const unsigned short *g = ov_guards[idx];; g += 3) {
        int end = g[0] == 255;
        if (end || (g[2] & 4)) {                      /* close the previous guard */
            if (started) { guard_ok = guard_ok && (conds_ok != neg); }
            conds_ok = 1; neg = (g[2] & 2) != 0; started = 1;
        }
        if (end || (g[2] & 8)) {                      /* close the previous alternative */
            if (alt_ok) any_alt |= guard_ok;
            alt_ok = 1; guard_ok = 1;
        }
        if (end) break;
        if (g[0] != 254 && ck(g[0], g[1]) != ((g[2] & 1) != 0)) conds_ok = 0;
    }
    return any_alt;
}
static int marker_visible(const OvMarker *m, unsigned page) {
    static const unsigned char kind_toggle[9] = {0, T_ROOMS, T_LOCKS, T_KEYS, T_DOCS, T_PUZZLES, T_COMMON, T_ENEMIES, T_EVENTS};
    if (m->page != page || !toggles[kind_toggle[m->kind]]) return 0;
    if (!(m->chars & (jill() ? 2 : 1))) return 0;
    /* era 2: mansion revisit RDTs (folders 6/7), loaded while Stage_no >= 5; era 1: the first visit's version of such a room */
    if (m->era && (m->era == 2) != (STAGE_NO >= 5)) return 0;
    if (m->side == 3) {   /* lock key on the door centre (RE0 rule, KeySide=0) */
        if (ov_key_side || (!room_known(m->stage, m->slot, m->page, 0) && !room_known(m->tstage, m->tslot, m->page, 0))) return 0;
    } else if (m->side) {   /* KeySide=1: label the room not visited yet, else the destination (RE1 HD map mod rule) */
        if (!ov_key_side) return 0;
        int own = slot_visited(m->stage, m->slot), dst = slot_visited(m->tstage, m->tslot);
        if ((m->side == 2) != (dst && !own)) return 0;
        if (!room_known(m->stage, m->slot, m->page, 0) && !room_known(m->tstage, m->tslot, m->page, 0)) return 0;
    } else if (!room_known(m->stage, m->slot, m->page, m->kind == 1)) return 0;
    if (m->flagtype == 1 && !flag_on(FLG_PICKUP, m->flag)) return 0;   /* set = still there; pickup clears (0x414fe0) */
    if ((m->flagtype == 1 || m->flagtype == 4) && !guards_pass(m->guard[jill() ? 1 : 0])) return 0;
    if (m->flagtype == 4 && m->flag != 255 && flag_on(FLG_KILL, m->flag)) return 0;   /* killed */
    if (m->flagtype == 2 && flag_on(FLG_DOOR, m->flag)) return 0;
    if (m->flagtype == 3) {   /* puzzle solved: every curated condition of one group holds (reward taken / SCD flag); 254 starts another group */
        int solved = 1;
        for (const unsigned short *c = ov_conds[m->flag]; ; c += 3) {
            if (c[0] == 255 || c[0] == 254) { if (solved) return 0; if (c[0] == 255) break; solved = 1; continue; }
            if (c[0] > 9 || ck(c[0], c[1]) != (c[2] != 0)) solved = 0;
        }
    }
    return 1;
}

/* Fullscreen map keys (INI [Keys]): OpenKey / OpenPad open it at the original gameplay gate; the same key or button,
 * CloseKey, or the game's cancel action (CloseOnCancel) close it. Pad buttons are read with XInput (loaded at runtime). */
static int direct_pending, direct_active, direct_init;
/* defaults: Tab / START to open, Esc or cancel to close (set in load_settings) */
typedef DWORD(WINAPI *xinput_get_state_fn)(DWORD, void *);
static xinput_get_state_fn xinput_get_state;
static int foreground(void) { DWORD pid = 0; GetWindowThreadProcessId(GetForegroundWindow(), &pid); return pid == GetCurrentProcessId(); }
static unsigned pad_buttons(void) {
    static int tried;
    if (!tried) {   /* not in DllMain (loader lock): first poll during gameplay */
        static const char *const dlls[] = {"xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"};
        tried = 1;
        for (unsigned i = 0; i < 3 && !xinput_get_state; i++) {
            HMODULE h = LoadLibraryA(dlls[i]);
            if (h) xinput_get_state = (xinput_get_state_fn)(void *)GetProcAddress(h, "XInputGetState");
        }
        if (!xinput_get_state) log_text("XInput not available: OpenPad disabled");
    }
    if (!xinput_get_state) return 0;
    unsigned char st[16]; unsigned b = 0;
    for (DWORD i = 0; i < 4; i++) if (xinput_get_state(i, st) == 0) b |= *(uint16_t *)(st + 4);   /* XINPUT_STATE.Gamepad.wButtons */
    return b;
}
static int edge(int down, int *was) { int p = down && !*was; *was = down; return p; }
static int open_pressed(void) {
    static int kd, pd;
    int fg = foreground();
    int k = edge(fg && open_vk && (GetAsyncKeyState(open_vk) & 0x8000), &kd);
    int pad = edge(fg && open_pad && (pad_buttons() & (unsigned)open_pad), &pd);
    return k || pad;
}
static int close_pressed(void) {
    static int cd;
    int c = edge(foreground() && close_vk && (GetAsyncKeyState(close_vk) & 0x8000), &cd);
    int cancel = close_on_cancel && (*(volatile uint16_t *)0xC38712 & 0x8000);   /* cancel action, as the native menu (0x40b6ab) */
    return open_pressed() || c || cancel;
}
static int key_code(const char *v, int def) {   /* "M", "ESC", "TAB", "F1".."F12", "0x4D"; "" or "NONE" disables */
    if (!v[0]) return def;
    if (!lstrcmpiA(v, "NONE")) return 0;
    if (!lstrcmpiA(v, "ESC") || !lstrcmpiA(v, "ESCAPE")) return VK_ESCAPE;
    if (!lstrcmpiA(v, "TAB")) return VK_TAB;
    if (!lstrcmpiA(v, "SPACE")) return VK_SPACE;
    if (!lstrcmpiA(v, "BACKSPACE")) return VK_BACK;
    if ((v[0] == 'F' || v[0] == 'f') && v[1] >= '1' && v[1] <= '9') { int n = v[1] - '0'; if (v[2] >= '0' && v[2] <= '9') n = n * 10 + v[2] - '0'; return n <= 12 ? VK_F1 + n - 1 : def; }
    if (v[0] == '0' && (v[1] == 'x' || v[1] == 'X')) { int n = 0; for (const char *c = v + 2; *c; c++) n = n * 16 + (*c <= '9' ? *c - '0' : (*c | 32) - 'a' + 10); return n; }
    if (!v[1]) return v[0] >= 'a' && v[0] <= 'z' ? v[0] - 32 : v[0];
    return def;
}
static int pad_code(const char *v, int def) {   /* XInput button names; "" default, "NONE" disables */
    static const char *const names[] = {"UP", "DOWN", "LEFT", "RIGHT", "START", "BACK", "LS", "RS", "LB", "RB", 0, 0, "A", "B", "X", "Y"};
    if (!v[0]) return def;
    for (int i = 0; i < 16; i++) if (names[i] && !lstrcmpiA(v, names[i])) return 1 << i;
    return 0;
}
static void request_direct_map(void) {
    if (!open_pressed()) return;
    log_fmt("M request mode=%d busy=%d control=%x status=%x", *(volatile unsigned char *)0xC330AC,
            *(volatile unsigned char *)0xC3523E, *(volatile uint16_t *)0xC3AB90, (int)STATUS_FLG);
    if (*(volatile unsigned char *)0xC330AC != 2 || *(volatile unsigned char *)0xC3523E != 0 ||
        (*(volatile uint16_t *)0xC3AB90 & 0x140) != 0x140 || (STATUS_FLG & 0x40ff00u)) return;
    /* Leave pause, task scheduling and resource ownership to the game's own menu path. */
    *(volatile uint16_t *)0xC3F8E0 |= 0x800;
    direct_pending = 1; log_text("M accepted: native menu requested");
}
static void __cdecl camera_update_hook(int mode) {
    ((void(__cdecl *)(int))0x414dd0)(mode); request_direct_map();
}
static void __cdecl camera_change_hook(void) {
    ((void(__cdecl *)(void))0x414e60)(); request_direct_map();
}

/* ---------- native calls */
typedef int(__cdecl *add_sprt_fn)(void *, int, int, int);
typedef int(__cdecl *upload_fn)(void *, int, int, int);
typedef int(__cdecl *upload_map_fn)(void *, int, int, int, int, int, int, int);
typedef void(__cdecl *map_draw_fn)(void *);
typedef void(__fastcall *slot_fn)(void *);                     /* __thiscall with no stack args == fastcall(ecx) */
static const add_sprt_fn add_sprt = (add_sprt_fn)0x441920;
static const upload_fn upload_tim = (upload_fn)0x43f700;
static const upload_map_fn upload_map_tim = (upload_map_fn)0x43f950;
static const map_draw_fn native_map_draw = (map_draw_fn)0x43c7c0;
static const slot_fn slot_construct = (slot_fn)0x4983f0, slot_destruct = (slot_fn)0x498040;
static void(__cdecl *const texture_free)(void *) = (void(__cdecl *)(void *))0x43f2e0;

/* ---------- tiles: 4bpp 256x256 TIMs, one native texture slot state each */
typedef struct { int used; unsigned char state[SLOT_SIZE]; } Tile;
static Tile notice_tile, sd_arrows;
static void sd_frame(unsigned page, int left, int top);
static void sd_service(void);
static void sd_draw_layers(void);
/* layer 0: titles, nav arrows (opaque); 1: names + leader lines (NameOpacity; legend CLUT, so a name has its legend row's
 * colour); 2: floor/area arrows (blinking); 3: opaque legend (legend CLUT); 4: marker icons (IconOpacity, IconSize).
 * Enemy icons are not composed into tiles: each kind has its own texture + CLUT (one shared CLUT turned every enemy brown)
 * and every enemy is its own sprite, drawn per tile after the names and before the item icons (ENEMY_PASS). */
#define LAYERS 5
#define ICON_LAYER 4
#define ENEMY_PASS 5
#define MAX_ENEMY_DRAWS 240   /* enemy and HD-icon sprites per frame; with the ~45 tile sprites this stays under Add_sprt's 300 per frame */
#define SPRITE_KINDS (OV_ENEMY_KINDS + OV_HD_KINDS)   /* kinds 0..13 enemies, then the HD icons */
static Tile tiles[LAYERS][TILES_X * TILES_Y], background, terrain, outline, arrows, enemy_tex[SPRITE_KINDS];
static struct { unsigned char kind, tile; short x, y; } enemy_draws[MAX_ENEMY_DRAWS];   /* PSX px, top-left */
static unsigned enemy_count, enemy_dropped;
static int enemy_quad[4];   /* x0, y0, x1, y1 PSX (inclusive) while an enemy sprite is submitted with IconSize != 100 */
static int layer;
static int drawing_background, semi_layer;
static int bg_quad[4];
static unsigned nav_held;
static int compose_needed = 1;
static unsigned cached_page = ~0u;
static int cached_left, cached_top, cached_fullscreen;
static DWORD nav_repeat_at;
static unsigned char terrain_px[BG_TEX * BG_TEX / 2], outline_px[BG_TEX * BG_TEX / 2];
static unsigned char tile_px[LAYERS][TILES_X * TILES_Y][TILE_TEX * TILE_TEX / 2];
static unsigned char tim_buf[20 + 32 + 12 + TILE_TEX * TILE_TEX / 2];
__declspec(dllexport) volatile int ov_uv_scale;  /* exported for tests/test_native.py */

static void release_slot(unsigned char *slot) {
    unsigned count = *(unsigned *)(slot + 0x1e0);
    for (unsigned i = 0; i < count && i < 8; i++) { void *t = *(void **)(slot + 0x1e8 + i * 4); if (t) texture_free(t); }
    slot_destruct(slot);
}
static void release_tile(Tile *t) {
    if (!t->used) return;
    unsigned char saved[SLOT_SIZE]; memcpy(saved, TEX_SLOT, SLOT_SIZE);
    memcpy(TEX_SLOT, t->state, SLOT_SIZE); release_slot(TEX_SLOT);
    memcpy(TEX_SLOT, saved, SLOT_SIZE); t->used = 0;
}
static int upload_tile(Tile *t, const unsigned char *px, const unsigned short *palette, unsigned size) {
    uint32_t *h = (uint32_t *)tim_buf;
    h[0] = 0x10; h[1] = 8; h[2] = 12 + 32;
    uint16_t *c = (uint16_t *)(tim_buf + 12); c[0] = 0; c[1] = 0; c[2] = 16; c[3] = 1;
    memcpy(tim_buf + 20, palette, 32);
    uint32_t *p = (uint32_t *)(tim_buf + 52); p[0] = 12 + size * size / 2;
    uint16_t *pd = (uint16_t *)(tim_buf + 56); pd[0] = 0; pd[1] = 0; pd[2] = (uint16_t)(size / 4); pd[3] = (uint16_t)size;
    memcpy(tim_buf + 64, px, size * size / 2);
    unsigned char saved[SLOT_SIZE]; memcpy(saved, TEX_SLOT, SLOT_SIZE);
    memset(TEX_SLOT, 0, SLOT_SIZE);
    slot_construct(TEX_SLOT);
    /* Add_sprt adds the page origin again; page zero keeps tile UVs local. */
    upload_tim(tim_buf, 0, 0, 1);
    int ok = *(unsigned *)(TEX_SLOT + 0x1e0) == 1 && *(void **)(TEX_SLOT + 0x1e8);
    if (ok) {
        /* REbirth's HD upload leaves the original Add_sprt bounds empty. */
        int16_t *rect = (int16_t *)(TEX_SLOT + 0x208);
        rect[0] = rect[1] = 0; rect[2] = (int16_t)(size / 4); rect[3] = (int16_t)size;
        rect[4] = 0; rect[5] = 480; rect[6] = 0; rect[7] = 1; rect[8] = 0;
        memcpy(t->state, TEX_SLOT, SLOT_SIZE);
    } else release_slot(TEX_SLOT);
    memcpy(TEX_SLOT, saved, SLOT_SIZE);
    t->used = ok;
    return ok;
}

static unsigned char tile_dirty[LAYERS][TILES_X * TILES_Y];
/* Zoom (2x) names and icons live in map space: the whole 512x400 PSX canvas is composed once into ZW x ZH tiles (layer 1 names +
 * leader lines, layer 4 icons) and panning only moves where the visible tiles are drawn; tiles are uploaded when they first
 * come into view. The other layers (legend, titles, arrows) stay screen space. */
#define ZW 16
#define ZH 13
#define ZL_NAME 0
#define ZL_ICON 1
static Tile ztiles[2][ZW * ZH];
static unsigned char ztile_px[2][ZW * ZH][TILE_TEX * TILE_TEX / 2], ztile_dirty[2][ZW * ZH];
static uint32_t ztile_hash[2][ZW * ZH];   /* content hash of the texture held (0: none); ztile_want: composed content */
static uint32_t ztile_want[2][ZW * ZH], tile_want[LAYERS][TILES_X * TILES_Y], tile_hash[LAYERS][TILES_X * TILES_Y];
/* Zoom viewport on screen (PSX px): the whole map area, from the top of the screen (the area title is drawn over it) down to the
 * legend's top edge, or to the screen bottom while the legend is folded with [~]. Heights stay multiples of 4 for the terrain UVs. */
#define ZVIEW_TOP 0
static int zview_bottom(void) { return legend_on ? 204 : 240; }
static int zview_h(void) { return zview_bottom() - ZVIEW_TOP; }
/* Pan may go a quarter of the viewport past each edge of the 512x400 canvas (multiples of 4 for the terrain UVs), so edge rooms
 * and names can be brought toward the centre. */
static int zmargin_x(void) { return 80; }
static int zmargin_y(void) { return (zview_h() / 4) & ~3; }
static int zpan_min_x(void) { return -zmargin_x(); }
static int zpan_max_x(void) { return 512 - 320 + zmargin_x(); }
static int zpan_min_y(void) { return -zmargin_y(); }
static int zpan_max_y(void) { return 400 - zview_h() + zmargin_y(); }
static int zpan_mid_y(void) { return ((400 - zview_h()) / 2) & ~3; }
static int fdiv32(int v) { return v >= 0 ? v / 32 : -((31 - v) / 32); }   /* floor(v / 32): tile index for a possibly negative position */
/* Every name / icon / leader-line box composed into the zoom tiles (map space, PSX px, end exclusive) with its marker: a box the
 * window edge would slice is not drawn, nor is the rest of its marker (see draw_zoom_map). */
#define ZBOX_MAX 2600
#define ZCUT_MAX 40
__declspec(dllexport) int ov_zbox_n, ov_cut_n;
__declspec(dllexport) short ov_zbox[ZBOX_MAX][6], ov_cut[ZCUT_MAX][5];   /* x0 y0 x1 y1 layer(0 names+lines, 1 icons) pair / screen rect */
static int zpair;
static void zbox_add(int x, int y, int w, int h, int icon_layer) {
    if (ov_zbox_n >= ZBOX_MAX || w <= 0 || h <= 0) return;
    short *b = ov_zbox[ov_zbox_n++];
    b[0] = (short)(x / OV_SCALE); b[1] = (short)(y / OV_SCALE); b[2] = (short)((x + w + OV_SCALE - 1) / OV_SCALE); b[3] = (short)((y + h + OV_SCALE - 1) / OV_SCALE);
    b[4] = (short)icon_layer; b[5] = (short)zpair;
}
static int zmap_layer(void) { return map_paint && zoomed() && (layer == 1 || layer == ICON_LAYER); }
/* byte holding texel (px, py) of the current layer's buffer (NULL outside it); marks that tile dirty */
static unsigned char *texel(int px, int py, unsigned *odd) {
    int zm = zmap_layer(), gw = zm ? ZW : TILES_X, gh = zm ? ZH : TILES_Y;
    if (px < 0 || py < 0 || px >= gw * TILE_TEX || py >= gh * TILE_TEX) return 0;
    unsigned ti = (unsigned)(py / TILE_TEX) * (unsigned)gw + (unsigned)(px / TILE_TEX), lx = (unsigned)(px % TILE_TEX), ly = (unsigned)(py % TILE_TEX);
    *odd = lx & 1;
    unsigned off = ly * (TILE_TEX / 2) + lx / 2;
    if (zm) { int k = layer == ICON_LAYER ? ZL_ICON : ZL_NAME; ztile_dirty[k][ti] = 1; return &ztile_px[k][ti][off]; }
    tile_dirty[layer][ti] = 1; return &tile_px[layer][ti][off];
}
static void blit(int bid, int x, int y) {
    if (bid < 0) return;
    const OvBitmap *b = &ov_bitmaps[bid];
    const unsigned char *src = ov_pixels + b->off;
    unsigned row = (b->w + 1u) / 2u;
    /* shortcut: keep label anchors when resizing; rerun placement if every enlarged name must avoid icons. */
    int scale = layer == 1 ? name_size : layer >= ICON_LAYER ? icon_size : 100;
    if (map_paint && zoomed() && layer >= ICON_LAYER) scale = (scale * 143 + 50) / 100;
    int w = (b->w * scale + 50) / 100, h = (b->h * scale + 50) / 100;
    x += (b->w - w) / 2; y += (b->h - h) / 2;
    if (layer == 1 && !(map_paint && zoomed())) {
        if (x < 0) x = 0; if (x + w > 320 * OV_SCALE) x = 320 * OV_SCALE - w;
        if (y < 0) y = 0; if (y + h > 204 * OV_SCALE) y = 204 * OV_SCALE - h;
    }
    if (zmap_layer()) zbox_add(x, y, w, h, layer == ICON_LAYER);
    for (int j = 0; j < h; j++) {
        for (int i = 0; i < w; i++) {
            unsigned sx = (unsigned)i * b->w / w, sy = (unsigned)j * b->h / h;
            unsigned v = (src[sy * row + sx / 2] >> ((sx & 1) * 4)) & 15; if (!v) continue;
            unsigned odd; unsigned char *d = texel(x + i, y + j, &odd); if (!d) continue;
            *d = odd ? (unsigned char)((*d & 0x0f) | (v << 4)) : (unsigned char)((*d & 0xf0) | v);
        }
    }
}

/* Fullscreen room outlines: thin opaque lines through the wall/door cells (hi-res layer 0), while the
 * semi-transparent fill extends under them with the neighbouring room's colour. */
static void put_outline(unsigned x, unsigned y, unsigned color) {
    unsigned char *p = &outline_px[y * (BG_TEX / 2) + x / 2];
    *p = (x & 1) ? (unsigned char)((*p & 15) | color << 4) : (unsigned char)((*p & 240) | color);
}
static void put_terrain(unsigned x, unsigned y, unsigned color) {
    unsigned char *p = &terrain_px[y * (BG_TEX / 2) + x / 2];
    *p = (x & 1) ? (unsigned char)((*p & 15) | color << 4) : (unsigned char)((*p & 240) | color);
}
static void fill_rect(int x0, int y0, int x1, int y1, unsigned v);
static void compose_terrain(unsigned page) {
    unsigned stage = page_stage[page];
    static const unsigned char slot_count[5] = {32, 31, 19, 18, 24};
    unsigned char remaining[32] = {0};
    if (room_tint && toggles[T_ALL] && (toggles[T_KEYS] || toggles[T_COMMON]))
        for (unsigned i = 0; i < OV_TINT_COUNT; i++) {
            const unsigned char *t = ov_tint[i];
            if (t[0] == stage && t[1] < 32 && (t[3] & (jill() ? 2 : 1)) && flag_on(FLG_PICKUP, t[2])) remaining[t[1]] = 1;
        }
    /* walls only once the floor's map was picked up, like the native loader (0x43c001 -> 0x43cec0: Flg_7 bit 0x7C + n;
     * B1 / Lab B1 / Lab B4 have no map item); scope 3 (all rooms) reveals them anyway */
    int walls = scope == 3 || page_revealed(page);
    static unsigned char col[100][128];
    for (unsigned y = 0; y < 100; y++) for (unsigned x = 0; x < 128; x++) {
        unsigned v = ov_map_pixels[page][y * 128 + x], color = 0;
        if (v == 7) color = walls ? 1 : 0;
        else if (v >= 13) {
            unsigned slot = (v - 13) / 6, part = (v - 13) % 6;
            if (slot < slot_count[stage] && slot_visited(stage, slot)) {
                /* native CLUT parts: +0 door, +1/+2 edge, +3/+4 fill (+4/+5 differ on variant slots); current = red +1..+3 */
                int current = MAP_STATE[5] == stage && MAP_STATE[7] == slot, var = ov_slot_variant[page][slot];
                static const unsigned char plain[6] = {2, 3, 3, 4, 4, 0}, alt[6] = {2, 3, 3, 4, 5, 6};
                color = (var ? alt : plain)[part];
                if (current && part >= 1 && part <= 3) color = 7;
                else if (!current && remaining[slot] && (part == 3 || part == 4)) color = part == 3 ? 8 : 9;
            } else if (walls && part == 0 && slot < slot_count[stage]) color = 2;   /* doors belong to the outline: shown with the walls */
        }
        col[y][x] = (unsigned char)color;
    }
    for (unsigned y = 0; y < 100; y++) for (unsigned x = 0; x < 128; x++) {
        unsigned c = col[y][x];
        if (c == 1 || c == 2) {   /* wall / door cell: the outline line runs through its left/top half (texel 2x, 2y), so only
                                   * the room its right/bottom half faces fills it; a fill from the left/top showed past every
                                   * right/bottom wall (2 PSX px at the 2x zoom) */
            static const int nb[3][2] = {{1, 0}, {0, 1}, {1, 1}};
            c = 0;
            for (int k = 0; k < 3 && !c; k++) {
                int nx = (int)x + nb[k][0], ny = (int)y + nb[k][1];
                if (nx >= 0 && ny >= 0 && nx < 128 && ny < 100 && col[ny][nx] >= 3) c = col[ny][nx];
            }
        }
        if (c) put_terrain(x, y, c);
    }
    /* opaque outline texture at 2 texels per map pixel (drawn 1:1, one PSX pixel per texel): walls as 1-px lines
     * through the cells, doors as short gold segments on the same line (one upload instead of dozens of hi-res tiles) */
    for (unsigned y = 0; y < 100; y++) for (unsigned x = 0; x < 128; x++) {   /* walls: 1-px lines through wall cells */
        if (col[y][x] != 1) continue;
        unsigned r = x + 1 < 128 ? col[y][x + 1] : 0, d = y + 1 < 100 ? col[y + 1][x] : 0;
        put_outline(2 * x, 2 * y, 1);
        if (r == 1) put_outline(2 * x + 1, 2 * y, 1);
        if (d == 1) put_outline(2 * x, 2 * y + 1, 1);
    }
    /* doors: the wall line continues through the door as a gold segment. The native marker's shape is the door type:
     * square = double door (two leaves, 1-px split in the middle), oblong = single door. Wall direction = where the
     * wall touches the marker (above/below -> vertical wall). */
    static unsigned char seen[100][128];
    static unsigned short stack[100 * 128];
    memset(seen, 0, sizeof seen);
    for (unsigned y = 0; y < 100; y++) for (unsigned x = 0; x < 128; x++) {
        if (col[y][x] != 2 || seen[y][x]) continue;
        unsigned n = 0, x0 = x, x1 = x, y0 = y, y1 = y;
        stack[n++] = (unsigned short)(y * 128 + x); seen[y][x] = 1;
        while (n) {
            unsigned v = stack[--n], cx = v % 128, cy = v / 128;
            if (cx < x0) x0 = cx; if (cx > x1) x1 = cx; if (cy < y0) y0 = cy; if (cy > y1) y1 = cy;
            static const int nb[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
            for (int k = 0; k < 4; k++) {
                int nx = (int)cx + nb[k][0], ny = (int)cy + nb[k][1];
                if (nx < 0 || ny < 0 || nx >= 128 || ny >= 100 || seen[ny][nx] || col[ny][nx] != 2) continue;
                seen[ny][nx] = 1; stack[n++] = (unsigned short)(ny * 128 + nx);
            }
        }
        /* wall direction from the map's own wall pixels (also when walls are hidden before the floor map) */
        const unsigned char *mp = ov_map_pixels[page];
        #define WALL(xx, yy) (mp[(yy) * 128 + (xx)] == 7)
        int vwall = 0, wl = -1;                                   /* wall line position across the door */
        for (unsigned i = x0; i <= x1; i++)
            if ((y0 > 0 && WALL(i, y0 - 1)) || (y1 + 1 < 100 && WALL(i, y1 + 1))) { vwall = 1; wl = (int)i; }
        if (!vwall)
            for (unsigned j = y0; j <= y1; j++)
                if ((x0 > 0 && WALL(x0 - 1, j)) || (x1 + 1 < 128 && WALL(x1 + 1, j))) wl = (int)j;
        #undef WALL
        if (wl < 0) wl = vwall ? (int)(x0 + x1) / 2 : (int)(y0 + y1) / 2;
        if ((x1 - x0) == (y1 - y0)) {                             /* double door: the original square marker */
            for (unsigned ty = 2 * y0; ty <= 2 * y1 + 1; ty++) for (unsigned tx = 2 * x0; tx <= 2 * x1 + 1; tx++) put_outline(tx, ty, 2);
            continue;
        }
        int a0 = 2 * (int)(vwall ? y0 : x0) - 1, a1 = 2 * (int)(vwall ? y1 : x1) + 1;   /* single door: spans the opening */
        for (int a = a0; a <= a1; a++)
            for (int t = 2 * wl - 1; t <= 2 * wl + 1; t++)                                   /* 3 px thick on the wall line */
                if (a >= 0 && t >= 0) { if (vwall) put_outline((unsigned)t, (unsigned)a, 2); else put_outline((unsigned)a, (unsigned)t, 2); }
    }
}
static void fill_rect(int x0, int y0, int x1, int y1, unsigned v) {   /* texels, inclusive; leader lines */
    if (zmap_layer()) zbox_add(x0, y0, x1 - x0 + 1, y1 - y0 + 1, 0);
    for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
        unsigned odd; unsigned char *d = texel(x, y, &odd); if (!d) continue;
        *d = odd ? (unsigned char)((*d & 0x0f) | (v << 4)) : (unsigned char)((*d & 0xf0) | v);
    }
}

/* Enemy icons: one TILE_TEX texture per kind (bitmap at 0,0) with that kind's CLUT, uploaded on first use and kept. */
static unsigned char enemy_px[TILE_TEX * TILE_TEX / 2];
static int kind_bitmap(int k) { return k < OV_ENEMY_KINDS ? ov_enemy_icons[k] : ov_hd_icons[k - OV_ENEMY_KINDS]; }
static const unsigned short *kind_palette(int k) { return k < OV_ENEMY_KINDS ? ov_enemy_palettes[k] : ov_hd_palettes[k - OV_ENEMY_KINDS]; }
/* HD item icons are drawn larger than the pixel icons they replace: +20 % on the 1x full map, +50 % on top of the 2x zoom scale (1.43).
 * The layout reserves a box of exactly the same size (tools/gen_assets.py HD_BOX1_PSX / HD_BOX2_PSX), so names stay adjacent. */
#define HD_SCALE_1X 120
#define HD_SCALE_2X 214
static int hd_box(int w, int zoom) { return ((w / OV_SCALE * (zoom ? HD_SCALE_2X : HD_SCALE_1X) + 50) / 100) * OV_SCALE; }
static int enemy_kind(int bid) { for (int k = 0; k < SPRITE_KINDS; k++) if (bid >= 0 && kind_bitmap(k) == bid) return k; return -1; }
static void queue_enemy(int bid, int x, int y) {   /* x, y: texels, as blit() */
    int k = enemy_kind(bid);
    if (k < 0) return;
    if (enemy_count >= MAX_ENEMY_DRAWS) { enemy_dropped++; return; }
    int px = (x + OV_SCALE / 2) / OV_SCALE, py = (y + OV_SCALE / 2) / OV_SCALE;   /* sprites sit on whole PSX pixels */
    if (px < 0 || py < 0 || px >= (zoomed() ? 512 : 320) || py >= (zoomed() ? 400 : TILES_Y * TILE_PSX)) return;   /* zoom: map space */
    enemy_draws[enemy_count].kind = (unsigned char)k;
    enemy_draws[enemy_count].tile = (unsigned char)((py / TILE_PSX) * TILES_X + px / TILE_PSX);
    enemy_draws[enemy_count].x = (short)px; enemy_draws[enemy_count].y = (short)py;
    enemy_count++;
}
static void draw_part(Tile *tile, int x, int y, int u, int v, int w, int h);
static unsigned uploads_this_frame;
static unsigned char sprite_failed[SPRITE_KINDS];
/* One 256 texture + own CLUT per sprite kind (enemy or HD icon), uploaded the first frame it is drawn, within the per-frame budget. */
static int ensure_sprite_tex(int k) {
    if (enemy_tex[k].used) return 1;
    if (sprite_failed[k] || uploads_this_frame >= (unsigned)ov_upload_budget) return 0;
    uploads_this_frame++;
    const OvBitmap *b = &ov_bitmaps[kind_bitmap(k)];
    const unsigned char *src = ov_pixels + b->off;
    unsigned row = (b->w + 1u) / 2u;
    memset(enemy_px, 0, sizeof enemy_px);
    for (unsigned j = 0; j < b->h; j++) memcpy(enemy_px + j * (TILE_TEX / 2), src + j * row, row);
    if (!upload_tile(&enemy_tex[k], enemy_px, kind_palette(k), TILE_TEX)) { sprite_failed[k] = 1; enemy_dropped++; return 0; }
    return 1;
}
static void draw_enemies(unsigned t) {
    for (unsigned i = 0; i < enemy_count; i++) {
        if (zoomed() ? t != 0 : enemy_draws[i].tile != t) continue;   /* zoom: one pass, map space -> window */
        if (!ensure_sprite_tex(enemy_draws[i].kind)) continue;
        const OvBitmap *b = &ov_bitmaps[kind_bitmap(enemy_draws[i].kind)];
        int w = b->w / OV_SCALE, h = b->h / OV_SCALE, x = enemy_draws[i].x, y = enemy_draws[i].y;
        int size = zoomed() ? icon_size * (enemy_draws[i].kind >= OV_ENEMY_KINDS ? HD_SCALE_2X : 143) / 100 : enemy_draws[i].kind >= OV_ENEMY_KINDS ? icon_size * HD_SCALE_1X / 100 : icon_size;
        int sw = (w * size + 50) / 100, sh = (h * size + 50) / 100;
        if (zoomed()) {   /* map space -> window; a sprite the window edge would slice is skipped whole */
            x -= ov_pan_x; y += ZVIEW_TOP - ov_pan_y;
            if (x + (w - sw) / 2 < 0 || y + (h - sh) / 2 < ZVIEW_TOP || x + (w + sw) / 2 > 320 || y + (h + sh) / 2 > zview_bottom()) continue;
        }
        if (size != 100) {
            enemy_quad[0] = x + (w - sw) / 2; enemy_quad[1] = y + (h - sh) / 2;
            enemy_quad[2] = enemy_quad[0] + sw - 1; enemy_quad[3] = enemy_quad[1] + sh - 1;
        }
        semi_layer = icon_opacity >= 100 ? 0 : ICON_LAYER;
        draw_part(&enemy_tex[enemy_draws[i].kind], x, y, 0, 0, w, h);
        semi_layer = 0; enemy_quad[2] = 0;
    }
}
static int zoom_coord(int v, unsigned page, int axis) {
    (void)page; return zoomed() ? v - (axis ? ov_pan_y - ZVIEW_TOP : ov_pan_x) * OV_SCALE : v;
}
static uint32_t tile_hash_of(const unsigned char *px, int dirty) {
    if (!dirty) return 0;
    uint32_t h = 2166136261u;
    const uint32_t *w = (const uint32_t *)px;
    for (unsigned i = 0; i < TILE_TEX * TILE_TEX / 8; i++) h = (h ^ w[i]) * 16777619u;
    return h | 1;
}
static const unsigned short *ov_legend_palette_for_zoom(int k) { return k == ZL_NAME ? legend_pal : ov_palette; }
/* IconSize / NameSize scale each icon and name about its own centre, but the layout (tools/gen_assets.py) put a name against its icon
 * at 100 %. Re-place at runtime: when a name lies beyond an edge of its icon's layout box on an axis, move it along that axis by the
 * growth of the icon half (IconSize) plus the growth of the name half (NameSize), so the two stay touching at any size and the scaled
 * icon never covers its name. Texels; box = icon layout box, name = layout name box. Exported for tests/test_native.py. */
static int beyond(int ilo, int ihi, int nlo, int nhi) { return nlo + OV_SCALE / 2 >= ihi ? 1 : nhi - OV_SCALE / 2 <= ilo ? -1 : 0; }
static int growth(int dim, int pct) { int v = dim * (pct - 100); return v >= 0 ? (v + 100) / 200 : -((-v + 100) / 200); }
__declspec(dllexport) int ov_name_offset(int axis, int ix, int iy, int bw, int bh, int lx, int ly, int lw, int lh) {
    return axis ? beyond(iy, iy + bh, ly, ly + lh) * (growth(bh, icon_size) + growth(lh, name_size))
                : beyond(ix, ix + bw, lx, lx + lw) * (growth(bw, icon_size) + growth(lw, name_size));
}
static unsigned tile_failed;
static void nav_can(int can[4]) {   /* floor / area arrows the current page has */
    unsigned area = MAP_STATE[4], up_down = MAP_STATE[12], areas = MAP_STATE[13];
    /* raw 0x80 (LEFT, RE1-Mod-SDK KEY_LEFT 8) -> area+1 / table 0x43bd08; raw 0x20 (RIGHT) -> area-1 / table 0x43bd18 */
    static const signed char left_special[4] = {3, 2, -1, 1}, right_special[4] = {-1, 3, 1, 0};
    can[0] = (up_down & 1) != 0; can[1] = (up_down & 2) != 0;
    if (areas & 8) { can[2] = area < 4 && left_special[area] >= 0; can[3] = area < 4 && right_special[area] >= 0; }
    else { can[2] = area != 2 && (areas & (1u << (area + 1))); can[3] = area > 0 && (areas & (1u << (area - 1))); }
}
static void compose(unsigned page, int ox, int oy) {
    /* clear only tiles the previous compose drew into (31 MB of tiles at OV_SCALE 16) */
    for (int k = 0; k < LAYERS; k++) for (unsigned t = 0; t < TILES_X * TILES_Y; t++)
        if (tile_dirty[k][t]) { memset(tile_px[k][t], 0, sizeof tile_px[k][t]); tile_dirty[k][t] = 0; }
    static unsigned dropped_logged;
    if (enemy_dropped != dropped_logged) { dropped_logged = enemy_dropped; log_fmt("Enemy icons dropped (cap or upload): %d", (int)enemy_dropped, 0, 0, 0); }
    enemy_count = 0; ov_zbox_n = 0;
    for (int k = 0; k < 2; k++) for (unsigned t = 0; t < ZW * ZH; t++)
        if (ztile_dirty[k][t]) { memset(ztile_px[k][t], 0, sizeof ztile_px[k][t]); ztile_dirty[k][t] = 0; }
    if (ov_fullscreen) {
        memset(terrain_px, 0, sizeof terrain_px); memset(outline_px, 0, sizeof outline_px);
        compose_terrain(page);
        if (!background.used) upload_tile(&background, ov_background_pixels, ov_background_palette, BG_TEX);
        if (!sd_mode && !arrows.used) upload_tile(&arrows, ov_arrow_pixels, ov_palette, TILE_TEX);
        release_tile(&terrain); release_tile(&outline);
        upload_tile(&terrain, terrain_px, ov_terrain_palette, BG_TEX);
        upload_tile(&outline, outline_px, ov_terrain_palette, BG_TEX);
    }
    if (sd_mode) return;   /* SD names, icons and legend are composed every frame by sd_frame() */
    map_paint = 1;
    /* Lines may cross labels: draw them first so names remain readable. */
    if (toggles[T_ALL] && toggles[T_ROOMS])
        for (unsigned i = 0; i < OV_LINE_COUNT; i++) {   /* leader lines of names placed outside their room */
            const OvLine *ln = &ov_lines[i];
            const OvMarker *m = &ov_markers[ln->marker]; zpair = (int)ln->marker;
            if (ln->view != (zoomed() ? 2 : ov_fullscreen ? 1 : 0) || ln->lang != (english ? 0 : 1) || !marker_visible(m, page)) continue;
            int bx = ov_fullscreen ? 0 : ox, by = ov_fullscreen ? 0 : oy;

            layer = 1;
            int x0 = ln->x0, x1 = ln->x1, y0 = ln->y0, y1 = ln->y1;
            fill_rect(bx + (x0 < x1 ? x0 : x1) - OV_SCALE / 4, by + (y0 < y1 ? y0 : y1) - OV_SCALE / 4,
                      bx + (x0 > x1 ? x0 : x1), by + (y0 > y1 ? y0 : y1), 12);   /* grey in the legend CLUT (index 12; 8 is the disabled-row grey) */
            layer = 0;
        }
    if (toggles[T_ALL]) {
        for (unsigned i = 0; i < OV_MARKER_COUNT; i++) {
            const OvMarker *m = &ov_markers[i]; zpair = (int)i;
            int view = zoomed() ? 2 : ov_fullscreen ? 1 : 0, bx = view ? 0 : ox, by = view ? 0 : oy;   /* fullscreen coords are absolute */
            int hd = view && ov_hd_on && m->hd >= 0 && m->kind != 7;   /* full map only: HD sprite instead of the pixel icon */
            if (!marker_visible(m, page)) continue;
            /* RE0 tiers: a common item or enemy under a key item / puzzle icon waits until that marker is gone */
            if (m->cover[view] >= 0 && marker_visible(&ov_markers[m->cover[view]], page)) continue;
            int ix = bx + m->ico[view][0], iy = by + m->ico[view][1];
            int lx = bx + m->lab[view][english ? 0 : 1].x, ly = by + m->lab[view][english ? 0 : 1].y;
            if (m->icon >= 0 && m->lab[view][english ? 0 : 1].bid >= 0) {   /* keep the name against its scaled icon (see ov_name_offset) */
                int w0 = ov_bitmaps[hd ? m->hd : m->icon].w, h0 = ov_bitmaps[hd ? m->hd : m->icon].h;
                int bw = hd ? hd_box(w0, view == 2) : view == 2 ? w0 * 143 / 100 : w0, bh = hd ? hd_box(h0, view == 2) : view == 2 ? h0 * 143 / 100 : h0;
                const OvBitmap *nb = &ov_bitmaps[m->lab[view][english ? 0 : 1].bid];
                int dx = ov_name_offset(0, ix, iy, bw, bh, lx, ly, nb->w, nb->h), dy = ov_name_offset(1, ix, iy, bw, bh, lx, ly, nb->w, nb->h);
                lx += dx; ly += dy;
            }
            if (zoomed()) {
                /* map space: nothing is culled here, the window clips tiles when they are drawn */
                int ib = hd ? m->hd : m->icon;
                int iw = ib < 0 ? 0 : hd ? hd_box(ov_bitmaps[ib].w, 1) : ov_bitmaps[ib].w * 143 / 100;
                int ih = ib < 0 ? 0 : hd ? hd_box(ov_bitmaps[ib].h, 1) : ov_bitmaps[ib].h * 143 / 100;
                /* The zoom layout uses enlarged icon boxes; blit/quad scaling is around the original centre. */
                if (ib >= 0) { ix += (iw - ov_bitmaps[ib].w) / 2; iy += (ih - ov_bitmaps[ib].h) / 2; }
                if (hd) zbox_add(ix - (iw - ov_bitmaps[ib].w) / 2, iy - (ih - ov_bitmaps[ib].h) / 2, iw, ih, 1);   /* sprite icons join the clipping rule */
            }
            layer = ICON_LAYER;
            if (m->kind == 7) queue_enemy(m->icon, ix, iy);
            else if (hd) {   /* the layout box is larger than the 32-texel sprite: centre the sprite in it */
                if (view == 1) { ix += (hd_box(ov_bitmaps[m->hd].w, 0) - ov_bitmaps[m->hd].w) / 2; iy += (hd_box(ov_bitmaps[m->hd].h, 0) - ov_bitmaps[m->hd].h) / 2; }
                queue_enemy(m->hd, ix, iy);
            }
            else if (m->icon >= 0) blit(m->icon, ix, iy);
            const OvLabel *l = &m->lab[view][english ? 0 : 1];
            layer = 1;   /* room names: key 1; every other name: H (item names). Status screen: icons only */
            if (l->bid >= 0 && view && ((m->kind == 1 && m->icon < 0) || item_names == 0 || (item_names == 1 && m->kind != 6))) blit(l->bid, lx, ly);   /* [H]: all / all but common / none */
            layer = 0;
        }
    }
    map_paint = 0;
    layer = 3;
    int lang = english ? 0 : 1;
    int title_y = ov_fullscreen ? 205 * OV_SCALE : 185 * OV_SCALE;
    if (!legend_on) {   /* [~] folds the legend to one line: bottom-left of the screen on the full map (RE0 rule), on its own black box */
        int fy = ov_fullscreen ? 240 * OV_SCALE - ov_bitmaps[ov_hint_fold[lang]].h : title_y;
        blit(ov_hint_fold[lang], 8 * OV_SCALE, fy);
    }
    else {
        blit(ov_full_legend_title[lang], 8 * OV_SCALE, title_y);
        blit(ov_hint_hide[lang], OV_HIDE_X, title_y);
        unsigned n = ov_fullscreen ? OV_FULL_CELLS : OV_STATUS_CELLS;
        for (unsigned c = 0; c < n; c++) {
            const short *cell = ov_fullscreen ? ov_full_cells[c] : ov_status_cells[c];
            int r = cell[0], bid;
            if (r < 10) bid = ov_full_legend[r][r == 9 ? scope - 1 : 0][r <= 8 && !toggles[r]][lang];
            else if (r == 10) bid = ov_name_size[(name_size - 50) / 10][lang];
            else if (r == 11) bid = ov_name_opacity[name_opacity / 10 - 1][lang];
            else if (r == 12) bid = ov_icon_size[ctrl_mod][(icon_size - 50) / 10][lang];
            else if (r == 13) bid = ov_icon_opacity[ctrl_mod][icon_opacity / 10 - 1][lang];
            else if (r == 14) bid = ov_hint_names[item_names][lang];
            else if (r == 16) bid = ov_zoom_hint[ov_zoom][lang];
            else if (r == 18) bid = ov_hint_lang[lang];
            else bid = ov_hint_tab[direct_active ? 1 : 0][lang];
            blit(bid, cell[1], cell[2]);
        }
    }
    layer = 0;
    if (ov_fullscreen) {
        blit(ov_page_titles[page][lang], 10 * OV_SCALE, 8 * OV_SCALE);
        int can[4]; nav_can(can);
        layer = 2;
        if (!zoomed() && can[0]) blit(ov_nav[0], (320 * OV_SCALE - ov_bitmaps[ov_nav[0]].w) / 2, 2 * OV_SCALE);
        if (!zoomed() && can[1]) blit(ov_nav[1], (320 * OV_SCALE - ov_bitmaps[ov_nav[1]].w) / 2, 203 * OV_SCALE - ov_bitmaps[ov_nav[1]].h);   /* above the legend */
        if (!zoomed() && can[2]) blit(ov_nav[2], 5 * OV_SCALE, (120 * OV_SCALE - ov_bitmaps[ov_nav[2]].h / 2));
        if (!zoomed() && can[3]) blit(ov_nav[3], 315 * OV_SCALE - ov_bitmaps[ov_nav[3]].w, (120 * OV_SCALE - ov_bitmaps[ov_nav[3]].h / 2));
        layer = 0;
    }
    /* texture uploads dominate a recompose (REbirth HD path per TIM): keep tiles whose pixels did not change, and upload the
     * changed ones from service_uploads(), a few per frame, instead of all inside this frame */
    for (unsigned t = 0; t < TILES_X * TILES_Y; t++)
        for (int k = 0; k < LAYERS; k++) {
            uint32_t h = tile_hash_of(tile_px[k][t], tile_dirty[k][t]);
            tile_want[k][t] = h;
            if (h == tile_hash[k][t] && (h == 0 || tiles[k][t].used)) continue;
            release_tile(&tiles[k][t]); tile_hash[k][t] = 0;
        }
    for (int k = 0; k < 2; k++)
        for (unsigned t = 0; t < ZW * ZH; t++) {
            uint32_t h = zoomed() ? tile_hash_of(ztile_px[k][t], ztile_dirty[k][t]) : 0;
            ztile_want[k][t] = h;
            if (h == ztile_hash[k][t] && (h == 0 || ztiles[k][t].used)) continue;
            release_tile(&ztiles[k][t]); ztile_hash[k][t] = 0;
        }
}

static DWORD upload_log_from; static unsigned upload_log_count;
static int upload_one(Tile *t, uint32_t *held, uint32_t want, const unsigned char *px, const unsigned short *pal) {
    if (uploads_this_frame >= (unsigned)ov_upload_budget) return 0;
    uploads_this_frame++;
    if (!upload_tile(t, px, pal, TILE_TEX)) tile_failed++;
    *held = want;   /* a failed upload is not retried every frame; the tile stays undrawn */
    return 1;
}
/* Upload the composed tiles that have no texture yet, legend first, at most ov_upload_budget per frame. */
static void service_uploads(void) {
    upload_log_count += uploads_this_frame; uploads_this_frame = 0;
    if (sd_mode) { sd_service(); return; }
    static const unsigned char order[LAYERS] = {3, 0, ICON_LAYER, 1, 2};
    for (int o = 0; o < LAYERS; o++) for (unsigned t = 0; t < TILES_X * TILES_Y; t++) {
        int k = order[o];
        if (tile_want[k][t] && !tiles[k][t].used && tile_hash[k][t] != tile_want[k][t]) {
            if (!upload_one(&tiles[k][t], &tile_hash[k][t], tile_want[k][t], tile_px[k][t], k == 1 || k == 3 ? legend_pal : ov_palette)) return;
        }
    }
    if (!zoomed()) return;
    /* zoom: tiles inside the window, release the ones that left it by more than a tile */
    int tx0 = fdiv32(ov_pan_x), tx1 = fdiv32(ov_pan_x + 319), ty0 = fdiv32(ov_pan_y), ty1 = fdiv32(ov_pan_y + zview_h() - 1);
    for (int k = 0; k < 2; k++) for (int ty = 0; ty < ZH; ty++) for (int tx = 0; tx < ZW; tx++) {
        unsigned t = (unsigned)(ty * ZW + tx);
        int vis = tx >= tx0 && tx <= tx1 && ty >= ty0 && ty <= ty1, nearby = tx >= tx0 - 1 && tx <= tx1 + 1 && ty >= ty0 - 1 && ty <= ty1 + 1;
        if (!nearby && ztiles[k][t].used) { release_tile(&ztiles[k][t]); ztile_hash[k][t] = 0; }
        if (vis && ztile_want[k][t] && !ztiles[k][t].used && ztile_hash[k][t] != ztile_want[k][t])
            if (!upload_one(&ztiles[k][t], &ztile_hash[k][t], ztile_want[k][t], ztile_px[k][t], ov_legend_palette_for_zoom(k))) return;
    }
}

static void draw_part(Tile *tile, int x, int y, int u, int v, int w, int h);
/* Player arrow (fullscreen): Pl_work 0xC351B4 Pos_x +0x34, Pos_z +0x3C, Cdir_y +0x74 (RE1-Mod-SDK PLAYER_WORK; exe 0x402372/0x402bfe).
 * World -> map TIM pixels with the room's fitted transform (tools/fit.py). Semi-transparent, blinking. */
static void draw_player(void) {
    unsigned stage = MAP_STATE[5], room = *(volatile uint8_t *)0xC386F1;
    if (stage >= 5 || room >= 32) return;
    const OvXform *t = &ov_xform[stage][room];
    if (!t->kind || t->page != cached_page) return;
    int x = *(volatile int32_t *)0xC351E8, z = *(volatile int32_t *)0xC351F0, px256, py256;
    const signed char *o = ov_orient[t->o];
    if (t->kind == 1) {
        int u = o[0] * x + o[1] * z, v = o[2] * x + o[3] * z;
        px256 = t->tx256 + (((t->sx24 >> 4) * u) >> 12);
        py256 = t->ty256 + (((t->sy24 >> 4) * v) >> 12);
    } else { px256 = t->ax * 256 + 128; py256 = t->ay * 256 + 128; }
    /* heading: world forward of Cdir_y -> map vector -> nearest of 16 screen headings (k * 22.5 deg clockwise from up) */
    static const short sn[16] = {0, 38, 71, 92, 100, 92, 71, 38, 0, -38, -71, -92, -100, -92, -71, -38};
    int dir = *(volatile int16_t *)0xC35228 + arrow_rotation * 4096 / 360;
    unsigned w = (unsigned)((dir + 128) >> 8) & 15;
    /* forward = RotMatrix(0, Cdir_y, 0) * (1, 0, 0) = (cos, -sin) in world (x, z): exe 0x410170 -> 0x455a80, checked by
     * emulating it (Cdir_y 0 -> +x, 1024 -> -z) */
    int ws = sn[w], wc = sn[(w + 4) & 15], fx = wc, fz = -ws;
    int dx = o[0] * fx + o[1] * fz, dy = o[2] * fx + o[3] * fz, best = 0, bestdot = -100000;
    if (t->kind != 1) { dx = fx; dy = -fz; }
    for (int k = 0; k < 16; k++) {
        int dot = dx * sn[k] - dy * sn[(k + 4) & 15];
        if (dot > bestdot) { bestdot = dot; best = k; }
    }
    int sxp = ov_full_origin[cached_page][0] + (2 * px256) / 256, syp = ov_full_origin[cached_page][1] + (2 * py256) / 256;
    if (zoomed()) { sxp = zoom_coord((sxp - ov_full_origin[cached_page][0]) * 2 * OV_SCALE, cached_page, 0) / OV_SCALE; syp = zoom_coord((syp - ov_full_origin[cached_page][1]) * 2 * OV_SCALE, cached_page, 1) / OV_SCALE;
        if (sxp < 4 || sxp > 315 || syp < ZVIEW_TOP + 4 || syp > zview_bottom() - 5) return; }
    semi_layer = 2;
    if (sd_mode) draw_part(&sd_arrows, sxp - 4, syp - 4, (best % 4) * 9, (best / 4) * 9, 9, 9);
    else draw_part(&arrows, sxp - OV_ARROW_CELL / 2, syp - OV_ARROW_CELL / 2, (best % 4) * OV_ARROW_CELL, (best / 4) * OV_ARROW_CELL, OV_ARROW_CELL, OV_ARROW_CELL);
    semi_layer = 0;
}
static void draw_part(Tile *tile, int x, int y, int u, int v, int w, int h) {
    if (w <= 0 || h <= 0) return;
    if (zoomed() && drawing_background >= 2) {
        int unit = drawing_background == 2 ? 4 : 2;
        /* the part of the 512x400 canvas inside the window (the pan can go past its edges) */
        int mx0 = ov_pan_x > 0 ? ov_pan_x : 0, mx1 = ov_pan_x + 320 < 512 ? ov_pan_x + 320 : 512;
        int my0 = ov_pan_y > 0 ? ov_pan_y : 0, my1 = ov_pan_y + zview_h() < 400 ? ov_pan_y + zview_h() : 400;
        u = mx0 / unit; v = my0 / unit; w = (mx1 - mx0) / unit; h = (my1 - my0) / unit;
        bg_quad[0] = mx0 - ov_pan_x; bg_quad[1] = ZVIEW_TOP + my0 - ov_pan_y; bg_quad[2] = mx1 - ov_pan_x - 1; bg_quad[3] = ZVIEW_TOP + my1 - ov_pan_y - 1;
    }
    unsigned char sp[36]; memset(sp, 0, sizeof sp);
    if (drawing_background) *(uint32_t *)sp = drawing_background == 2 ? 0x50000000u : drawing_background == 3 ? 0 : 0x40000000u;
    else if (semi_layer) *(uint32_t *)sp = 0x50000000u;   /* names: same semi-transparency as the native map sprite (0x51000000) */
    *(int16_t *)(sp + 4) = (int16_t)x; *(int16_t *)(sp + 6) = (int16_t)y;
    *(uint16_t *)(sp + 8) = (uint16_t)w; *(uint16_t *)(sp + 10) = (uint16_t)h;
    sp[14] = (unsigned char)u; sp[15] = (unsigned char)v;
    *(uint16_t *)(sp + 18) = 480;
    sp[20] = sp[21] = sp[22] = 128;
    memcpy(TEX_SLOT, tile->state, SLOT_SIZE);
    ov_uv_scale = drawing_background || notice_draw || sd_mode ? 1 : OV_SCALE; add_sprt(sp, overlay_z, -2, 1); ov_uv_scale = 0;
}
/* Zoom: names, enemies, icons from the map-space tiles, shifted by the pan and clipped to the map window. A name or icon box the
 * window edge would slice mid-glyph is cut out of the tile draws together with the rest of its marker (icon, name, leader line). */
typedef struct { int x0, y0, x1, y1; } Rect;
static Rect zex[2][ZCUT_MAX];
static int zex_n[2];
static void draw_minus(Tile *tile, int tx, int ty, int x0, int y0, int x1, int y1, const Rect *ex, int n) {
    if (x0 >= x1 || y0 >= y1) return;
    for (int i = 0; i < n; i++) {
        int ax = ex[i].x0 > x0 ? ex[i].x0 : x0, ay = ex[i].y0 > y0 ? ex[i].y0 : y0, bx = ex[i].x1 < x1 ? ex[i].x1 : x1, by = ex[i].y1 < y1 ? ex[i].y1 : y1;
        if (ax >= bx || ay >= by) continue;
        draw_minus(tile, tx, ty, x0, y0, x1, ay, ex + i + 1, n - i - 1);   /* above, below, left, right of the cut box */
        draw_minus(tile, tx, ty, x0, by, x1, y1, ex + i + 1, n - i - 1);
        draw_minus(tile, tx, ty, x0, ay, ax, by, ex + i + 1, n - i - 1);
        draw_minus(tile, tx, ty, bx, ay, x1, by, ex + i + 1, n - i - 1);
        return;
    }
    draw_part(tile, x0, y0, x0 - tx, y0 - ty, x1 - x0, y1 - y0);
}
static void find_cut_boxes(void) {
    static unsigned char cut_pair[OV_MARKER_COUNT + 1];
    int top = ZVIEW_TOP, bottom = zview_bottom();
    memset(cut_pair, 0, sizeof cut_pair);
    zex_n[0] = zex_n[1] = ov_cut_n = 0;
    for (int i = 0; i < ov_zbox_n; i++) {
        const short *b = ov_zbox[i];
        int x0 = b[0] - ov_pan_x, y0 = b[1] - ov_pan_y + top, x1 = b[2] - ov_pan_x, y1 = b[3] - ov_pan_y + top;
        if (x1 <= 0 || y1 <= top || x0 >= 320 || y0 >= bottom) continue;   /* outside the window */
        if (x0 < 0 || y0 < top || x1 > 320 || y1 > bottom) cut_pair[b[5]] = 1;   /* sliced by an edge */
    }
    for (int i = 0; i < ov_zbox_n; i++) {
        const short *b = ov_zbox[i];
        if (!cut_pair[b[5]]) continue;
        int k = b[4];
        if (zex_n[k] >= ZCUT_MAX) continue;
        Rect r = {b[0] - ov_pan_x, b[1] - ov_pan_y + top, b[2] - ov_pan_x, b[3] - ov_pan_y + top};
        zex[k][zex_n[k]++] = r;
        if (ov_cut_n < ZCUT_MAX) { short *c = ov_cut[ov_cut_n++]; c[0] = (short)r.x0; c[1] = (short)r.y0; c[2] = (short)r.x1; c[3] = (short)r.y1; c[4] = (short)k; }
    }
}
static void draw_zoom_map(void) {
    int top = ZVIEW_TOP, bottom = zview_bottom();
    int tx0 = fdiv32(ov_pan_x), tx1 = fdiv32(ov_pan_x + 319), ty0 = fdiv32(ov_pan_y), ty1 = fdiv32(ov_pan_y + zview_h() - 1);
    find_cut_boxes();
    for (int pass = 0; pass < 3; pass++) {
        if (pass == 1) { draw_enemies(0); continue; }
        int k = pass == 0 ? ZL_NAME : ZL_ICON;
        for (int ty = ty0 < 0 ? 0 : ty0; ty <= ty1 && ty < ZH; ty++) for (int tx = tx0 < 0 ? 0 : tx0; tx <= tx1 && tx < ZW; tx++) {
            Tile *tile = &ztiles[k][ty * ZW + tx];
            if (!tile->used) continue;
            int x = tx * TILE_PSX - ov_pan_x, y = ty * TILE_PSX + top - ov_pan_y;
            int sx = x < 0 ? 0 : x, sy = y < top ? top : y, ex = x + TILE_PSX > 320 ? 320 : x + TILE_PSX, ey = y + TILE_PSX > bottom ? bottom : y + TILE_PSX;
            semi_layer = k == ZL_ICON ? (icon_opacity >= 100 ? 0 : ICON_LAYER) : 1;
            draw_minus(tile, x, y, sx, sy, ex, ey, zex[k], zex_n[k]);
            semi_layer = 0;
        }
    }
}
static void draw_tiles(void) {
    unsigned char saved[SLOT_SIZE]; memcpy(saved, TEX_SLOT, SLOT_SIZE);
    if (ov_fullscreen && background.used) {
        drawing_background = 1;
        draw_part(&background, 0, 0, 0, 0, 256, 240);
        draw_part(&background, 256, 0, 0, 0, 64, 240);
        drawing_background = 0;
    }
    if (ov_fullscreen && terrain.used) {
        drawing_background = 2;
        draw_part(&terrain, ov_full_origin[cached_page][0], ov_full_origin[cached_page][1], 0, 0, 128, 100);
        drawing_background = 3;   /* opaque walls/doors */
        if (outline.used) draw_part(&outline, ov_full_origin[cached_page][0], ov_full_origin[cached_page][1], 0, 0, 256, 200);
        drawing_background = 0;
    }
    blink_alpha = (GetTickCount() / 400) & 1 ? 0.85f : 0.35f;   /* the floor / area arrows pulse (as in HD); unset, they were fully transparent in SD */
    if (sd_mode) { sd_draw_layers(); if (ov_fullscreen && sd_arrows.used) draw_player(); memcpy(TEX_SLOT, saved, SLOT_SIZE); return; }
    if (zoomed()) draw_zoom_map();
    blink_alpha = (GetTickCount() / 400) & 1 ? 0.85f : 0.35f;   /* arrows pulse bright/dim, never vanish */
    static const unsigned char order[LAYERS + 1] = {0, 1, ENEMY_PASS, ICON_LAYER, 2, 3};
    for (unsigned t = 0; t < TILES_X * TILES_Y; t++) {
        for (int o = 0; o <= LAYERS; o++) {
        int k = order[o];
        if (k == ENEMY_PASS) { draw_enemies(t); continue; }
        if (!tiles[k][t].used) continue;
        int bx = (int)(t % TILES_X) * TILE_PSX, by = (int)(t / TILES_X) * TILE_PSX;
        semi_layer = k == 3 || (k >= ICON_LAYER && icon_opacity >= 100) ? 0 : k;
        draw_part(&tiles[k][t], bx, by, 0, 0, TILE_PSX, TILE_PSX); semi_layer = 0;
        }
    }
    if (ov_fullscreen && arrows.used) draw_player();
    memcpy(TEX_SLOT, saved, SLOT_SIZE);
}

static void render_overlay(unsigned page, int left, int top);

static void reset_zoom(void) {   /* every map open starts at 1x, panned to the middle of the zoom canvas */
    ov_zoom = 0; ov_pan_x = 96; ov_pan_y = zpan_mid_y(); compose_needed = 1;
}
static void enter_direct_viewer(void) {
    reset_zoom();
    direct_pending = 0; direct_active = 1; direct_init = 1; ov_fullscreen = 1; nav_held = 0;
    *(volatile unsigned char *)0xC2E930 = 0;
    /* Let the original first menu frame initialize the map in its normal order. */
    *(volatile unsigned char *)0xC2E931 = 0;
    *(volatile unsigned char *)0xC2E940 = 0;
}
static void __cdecl menu_begin_hook(int a, int b) {
    compose_needed = 1;
    ((void(__cdecl *)(int, int))0x4172c0)(a, b);
    if (!direct_pending) return;
    log_text("M direct viewer selected: native map init deferred");
    enter_direct_viewer();
}
static void __cdecl menu_cleanup_hook(void) {
    reset_zoom();
    if (direct_active) log_text("M direct viewer closed");
    direct_active = direct_pending = 0; ov_fullscreen = 0;
    ((void(__cdecl *)(void))0x40ba50)();
}
static void __cdecl menu_input_hook(void) {
    if (!direct_active) ((void(__cdecl *)(void))0x465a10)();
}
static void __cdecl menu_status_draw_hook(void) {
    if (!direct_active) ((void(__cdecl *)(void))0x488310)();
}
static void __cdecl selector_draw_hook(void *state) {
    if (!direct_active) ((void(__cdecl *)(void *))0x43be40)(state);
}
static void direct_map_input(void) {
    /* C38710/12 are mapped actions; the native selector expects raw direction bits. */
    unsigned held = *(volatile uint16_t *)0xC38710 & 15;
    unsigned pressed = *(volatile uint16_t *)0xC38712 & 15;
    /* zoom key = the game's confirm/examine action (bit 0x40 of the mapped input, exe 0x408825), so config.ini Key_Def and the
     * controller bindings apply; edge-detected on the held bit */
    static int confirm_was;
    int confirm = ov_fullscreen && (*(volatile uint16_t *)0xC38710 & 0x40) != 0;
    if (edge(confirm, &confirm_was)) { ov_zoom = !ov_zoom; compose_needed = 1; save_settings(); }
    if (!held && !pressed) { nav_held = 0; return; }
    DWORD now = GetTickCount();
    if (zoomed()) {
        /* pan by offset only: no recompose, no upload. A tap moves 8 px; held (after 250 ms) 4 px per frame */
        int step = 0;
        if (held != nav_held) { step = 8; nav_repeat_at = now + 250; }
        else if (held && (int32_t)(now - nav_repeat_at) >= 0) step = 4;
        nav_held = held;
        if (!step) return;
        ov_pan_x = clamp_range(ov_pan_x + ((held & 2) != 0) * step - ((held & 8) != 0) * step, zpan_min_x(), zpan_max_x());
        ov_pan_y = clamp_range(ov_pan_y + ((held & 4) != 0) * step - ((held & 1) != 0) * step, zpan_min_y(), zpan_max_y());
        return;
    }
    if (held != nav_held) { pressed |= held & ~nav_held; nav_repeat_at = now + 300; }
    else if (held && (int32_t)(now - nav_repeat_at) >= 0) { pressed |= held; nav_repeat_at = now + 120; }
    nav_held = held;
    if (!pressed) return;
    volatile uint16_t *raw = (volatile uint16_t *)0xC3F8E0;
    uint16_t saved = *raw;
    *raw = (uint16_t)((saved & 0x0fff) | pressed << 12);
    ((void(__cdecl *)(volatile uint8_t *))0x43bd30)(MAP_STATE);
    unsigned before = MAP_STATE[6];
    ((void(__cdecl *)(volatile uint8_t *))0x43bbd0)(MAP_STATE);
    *raw = saved;
    if (pressed) log_fmt("Map action=%x page=%d->%d eligible=%x", pressed, before, MAP_STATE[6],
                         MAP_STATE[12] | MAP_STATE[13] << 8 | MAP_STATE[15] << 16);
}
static void __cdecl menu_ui_hook(void) {
    if (direct_active && close_pressed()) {
        ((void(__cdecl *)(void))0x40b9e0)();
        return;
    }
    if (direct_active && ov_fullscreen) {
        if (*(volatile unsigned char *)0xC2E931 == 7) return;
        *(volatile unsigned char *)0xC2E930 = 0;
        *(volatile unsigned char *)0xC2E931 = 1;
        /* State 1 skips the selector's case 0, which is where the game runs map init (0x40b639). */
        /* init (0x43ca60) sets the page; the floor/area eligibility bytes [12]/[13] are filled by the selector refresh
         * 0x43bd30, which otherwise runs only after an input (arrows missing on the first open after loading) */
        if (direct_init) { ((void(__cdecl *)(void))0x43ca60)(); ((void(__cdecl *)(volatile uint8_t *))0x43bd30)(MAP_STATE);
                           direct_init = 0; compose_needed = 1;
                           log_fmt("M map init stage=%d page=%d", MAP_STATE[5], MAP_STATE[6], 0, 0); }
        direct_map_input();
        render_overlay(MAP_STATE[6], 48, 28);
        return;
    }
    ((void(__cdecl *)(void))0x40bb60)();
}

/* ---------- input (map screen + game window in foreground) */
/* Debug capture (CaptureKey, default F12; REbirth uses F1..F11): map state, settings and the progress flag groups beside the
 * INI, written to a temp file then renamed. No save data, inventory or personal data. */
static void write_capture(void) {
    static char buf[2048];
    char path[MAX_PATH + 16], tmp[MAX_PATH + 20];
    unsigned n = (unsigned)lstrlenA(ini_path);
    if (n < 4) return;
    memcpy(path, ini_path, n - 3); memcpy(path + n - 3, "capture.txt", 12);
    wsprintfA(tmp, "%s.tmp", path);
    int len = wsprintfA(buf, "page=%d stage=%d slot=%d stage_no=%d room=%d jill=%d fullscreen=%d\r\n", MAP_STATE[6], MAP_STATE[5],
                        MAP_STATE[7], STAGE_NO, *(volatile uint8_t *)0xC386F1, jill(), ov_fullscreen);
    len += wsprintfA(buf + len, "toggles=%d%d%d%d%d%d%d%d%d scope=%d names=%d legend=%d keyside=%d\r\n", toggles[0], toggles[1], toggles[2],
                     toggles[3], toggles[4], toggles[5], toggles[6], toggles[7], toggles[8], scope, item_names, legend_on, ov_key_side);
    for (unsigned g = 0; g < 10; g++) {   /* SCD ck groups 0..9 (3: enemy kills, 7: pickups, 8: visited/maps) */
        len += wsprintfA(buf + len, "ck%d=", g);
        for (unsigned i = 0; i < 32; i++) len += wsprintfA(buf + len, "%02x", ((volatile uint8_t *)ck_group[g])[i]);
        len += wsprintfA(buf + len, "\r\n");
    }
    HANDLE h = CreateFileA(tmp, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 0, NULL);
    DWORD w = 0;
    int ok = h != INVALID_HANDLE_VALUE && WriteFile(h, buf, (DWORD)len, &w, NULL) && w == (DWORD)len;
    if (h != INVALID_HANDLE_VALUE) CloseHandle(h);
    if (ok && MoveFileExA(tmp, path, MOVEFILE_REPLACE_EXISTING)) { log_text("Capture written"); return; }
    DeleteFileA(tmp); log_text("Capture failed");
}

/* map keys (map shown, game window in front). Bits: 0..9 digits (0 all .. 8 enemies, 9 scope), 10 -, 11 +, 12 [, 13 ], 14 H, 15 ~, 16 \ (language, VK_OEM_5; Korean keyboards show it as the won sign), 17 capture.
 * Each key is edge-triggered and debounced (RE0 rule: a live log showed one press arriving 3 times, 200 ms apart). */
#define KEY_BITS 18
#define DEBOUNCE_MS 350
static unsigned keys_down;
static DWORD key_time[KEY_BITS];
static int modifier_held(void) {
    return ((ctrl_mod ? GetAsyncKeyState(VK_CONTROL) | GetAsyncKeyState(VK_LCONTROL) | GetAsyncKeyState(VK_RCONTROL)
                      : GetAsyncKeyState(VK_SHIFT) | GetAsyncKeyState(VK_LSHIFT) | GetAsyncKeyState(VK_RSHIFT)) & 0x8000) != 0;
}
static int step10(int v, int d, int lo, int hi) { v += d * 10; return v < lo ? lo : v > hi ? hi : v; }
static int poll_keys(void) {
    DWORD pid = 0; GetWindowThreadProcessId(GetForegroundWindow(), &pid);
    if (pid != GetCurrentProcessId()) { keys_down = 0; return 0; }
    if (pending_save) { pending_save = 0; save_settings(); }
    /* the open key (Tab / OpenPad) on the status map switches to the direct viewer
     * (the status menu cannot keep a full screen over it) */
    if (!direct_active && open_pressed()) { log_text("Open key: status map -> direct viewer"); enter_direct_viewer(); }
    unsigned now = 0;
    for (int k = 0; k <= 9; k++)
        if ((GetAsyncKeyState('0' + k) | GetAsyncKeyState(VK_NUMPAD0 + k)) & 0x8000) now |= 1u << k;
    static const int vks[KEY_BITS - 10][2] = {{VK_OEM_MINUS, VK_SUBTRACT}, {VK_OEM_PLUS, VK_ADD}, {VK_OEM_4, 0}, {VK_OEM_6, 0},
                                              {'H', 0}, {VK_OEM_3, 0}, {VK_OEM_5, 0}, {0, 0}};
    for (int k = 10; k < KEY_BITS; k++) {
        int a = k == 17 ? capture_vk : vks[k - 10][0], b = vks[k - 10][1];
        if (((a ? GetAsyncKeyState(a) : 0) | (b ? GetAsyncKeyState(b) : 0)) & 0x8000) now |= 1u << k;
    }
    unsigned pressed = now & ~keys_down; keys_down = now;
    if (!pressed) return 0;
    DWORD t = GetTickCount();
    for (int k = 0; k < KEY_BITS; k++)
        if (pressed & (1u << k)) {
            if (t - key_time[k] < DEBOUNCE_MS && key_time[k]) pressed &= ~(1u << k);
            else key_time[k] = t;
        }
    if (!pressed) return 0;
    if (pressed & (1u << 17)) { write_capture(); if (!(pressed &= ~(1u << 17))) return 0; }
    int retint = 0;
    for (int k = 0; k < T_COUNT; k++) if (pressed & (1u << k)) { toggles[k] = !toggles[k]; retint |= k == T_ALL || k == T_KEYS || k == T_DOCS || k == T_COMMON; }
    if (pressed & (1u << 9)) scope = scope % 3 + 1;   /* visited -> revealed -> all */
    if (pressed & (1u << 16)) english = !english;
    if ((pressed & (1u << 14)) && !sd_mode) item_names = (item_names + 1) % 3;
    if (pressed & (1u << 15)) legend_on = !legend_on;
    int mod = modifier_held();
    int names = ((pressed >> 11) & 1) - ((pressed >> 10) & 1), icons = ((pressed >> 13) & 1) - ((pressed >> 12) & 1);   /* - +, [ ] */
    /* RE0 mapping: - + name size, [ ] name opacity; with the modifier: icon size, icon opacity */
    if (sd_mode) names = icons = 0;
    if (names && mod) icon_size = step10(icon_size, names, 50, 200);
    else if (names) name_size = step10(name_size, names, 50, 150);
    if (icons && mod) { icon_opacity = step10(icon_opacity, icons, 10, 100); icon_alpha = (float)icon_opacity / 100.0f; }
    else if (icons) { name_opacity = step10(name_opacity, icons, 10, 100); name_alpha = (float)name_opacity / 100.0f; }
    save_settings();
    if (retint) { MAP_LOADED_PAGE = 0; MAP_STATE[1] = 0; }   /* reload page -> re-run tint hook (0x43bf40) */
    return 1;
}

/* ---------- hooks */
static void __cdecl map_draw_hook(void *state) {
    /* Direct viewing is drawn once by menu_ui_hook, without the original small map/UI. */
    if (direct_active && ov_fullscreen) return;
    native_map_draw(state);
    volatile int16_t *s = MAP_SPRITE;
    unsigned page = MAP_STATE[6];
    if (page > 10) return;
    if (s[0x1c / 2] != 0x1000 || s[0x1e / 2] != 0x1000) { ov_fullscreen = 0; return; }
    render_overlay(page, s[2] - s[0x18 / 2] + offset_x, s[3] - s[0x1a / 2] + offset_y);
}
#include "sd_draw.h"
/* HD textures off: the overlay's x8 textures cannot be sampled, so draw only a small 1:1 English notice. */
static unsigned char notice_px[TILE_TEX * TILE_TEX / 2];
static void draw_hd_notice(void) {
    unsigned char saved[SLOT_SIZE]; memcpy(saved, TEX_SLOT, SLOT_SIZE);
    if (!notice_tile.used && !notice_failed) {
        memcpy(notice_px, ov_notice_pixels, sizeof ov_notice_pixels);
        if (!upload_tile(&notice_tile, notice_px, legend_pal, TILE_TEX)) notice_failed = 1;
    }
    if (notice_tile.used) { notice_draw = 1; draw_part(&notice_tile, 4, 4, 0, 0, 256, 32); notice_draw = 0; }
    memcpy(TEX_SLOT, saved, SLOT_SIZE);
}
static int upload_pending(void) {
    if (sd_mode) return 0;
    for (int k = 0; k < LAYERS; k++) for (unsigned t = 0; t < TILES_X * TILES_Y; t++)
        if (tile_want[k][t] && !tiles[k][t].used && tile_hash[k][t] != tile_want[k][t]) return 1;
    if (zoomed()) for (int k = 0; k < 2; k++) for (unsigned t = 0; t < ZW * ZH; t++)
        if (ztile_want[k][t] && !ztiles[k][t].used && ztile_hash[k][t] != ztile_want[k][t]) {
            int tx = (int)(t % ZW), ty = (int)(t / ZW);
            if (tx >= fdiv32(ov_pan_x) && tx <= fdiv32(ov_pan_x + 319) && ty >= fdiv32(ov_pan_y) && ty <= fdiv32(ov_pan_y + zview_h() - 1)) return 1;
        }
    return 0;
}
static void render_overlay(unsigned page, int left, int top) {
    if (page > 10) return;
    if (hd_off && !sd_mode) { draw_hd_notice(); return; }
    int changed = poll_keys();
    if (compose_needed || changed || page != cached_page || ov_fullscreen != cached_fullscreen ||
        (!ov_fullscreen && (left != cached_left || top != cached_top))) {
        DWORD t0 = GetTickCount();
        compose(page, left * OV_SCALE, top * OV_SCALE);
        cached_page = page; cached_left = left; cached_top = top; cached_fullscreen = ov_fullscreen;
        compose_needed = 0;
        log_fmt("compose page=%d full=%d zoom=%d ms=%d", (int)page, ov_fullscreen, ov_zoom, (int)(GetTickCount() - t0));
        upload_log_from = GetTickCount(); upload_log_count = 0;
    }
    if (zoomed()) { ov_pan_y = clamp_range(ov_pan_y, zpan_min_y(), zpan_max_y()); ov_pan_x = clamp_range(ov_pan_x, zpan_min_x(), zpan_max_x()); }   /* the legend can change the viewport height */
    if (sd_mode) sd_frame(page, left, top);
    service_uploads();
    if (upload_log_from && !upload_pending()) {   /* the composed tiles are all uploaded: how long the frames took to catch up */
        log_fmt("tiles uploaded: %d in %d ms (budget %d/frame)", (int)upload_log_count, (int)(GetTickCount() - upload_log_from), ov_upload_budget, 0);
        upload_log_from = 0;
    }
    draw_tiles();
}

/* Remaining-item rooms: recolour fill entries (+3,+4 of the room's CLUT block) before the native upload. */
static void tint(unsigned char *tim, int flashing) {
    if (!room_tint || !toggles[T_ALL] || !(toggles[T_KEYS] || toggles[T_COMMON])) return;
    unsigned page = MAP_STATE[6]; if (page > 10) return;
    unsigned stage = page_stage[page], current = MAP_STATE[7];
    uint16_t *clut = (uint16_t *)(tim + 20);
    for (unsigned i = 0; i < OV_TINT_COUNT; i++) {
        const unsigned char *t = ov_tint[i];
        if (t[0] != stage || !(t[3] & (jill() ? 2 : 1)) || !flag_on(FLG_PICKUP, t[2])) continue;
        if (flashing && t[1] == current && MAP_STATE[5] == stage) continue;
        uint16_t *e = clut + 13 + 6 * t[1];
        if (e[3] == 0) continue;   /* unvisited: native already made it transparent */
        e[3] = (uint16_t)((e[3] & 0x8000) | (2 << 10) | (15 << 5) | 28);   /* amber */
        e[4] = (uint16_t)((e[4] & 0x8000) | (1 << 10) | (11 << 5) | 22);
    }
}
static int __cdecl upload_page_hook(void *tim, int a, int b, int c, int d, int e, int f, int g) { tint(tim, 0); return upload_map_tim(tim, a, b, c, d, e, f, g); }
static int __cdecl upload_flash_hook(void *tim, int a, int b, int c, int d, int e, int f, int g) { tint(tim, 1); return upload_map_tim(tim, a, b, c, d, e, f, g); }

/* Add_sprt -> Marni submit (thiscall, 2 stack args): scale our tiles' UVs to the hi-res texture. */
__attribute__((used)) void __cdecl ov_scale_command(unsigned char *cmd) {
    if (!ov_uv_scale) return;
    /* Keep a positive Marni depth; zero-depth tiles disappear in the live renderer. */
    if (ov_fullscreen) {
        *(uint32_t *)(cmd + 24) = drawing_background == 1 ? 416 : drawing_background == 2 ? 408 : drawing_background == 3 ? 404 : 400;
        if (drawing_background >= 2) {
            int16_t *xy = (int16_t *)(cmd + 8);
            int fx = ov_full_origin[cached_page][0], fy = ov_full_origin[cached_page][1];   /* 2x terrain, page-centred */
            if (zoomed()) { fx = bg_quad[0]; fy = bg_quad[1]; }
            xy[0] = (int16_t)fx; xy[1] = (int16_t)fy; xy[2] = (int16_t)(fx + 255); xy[3] = (int16_t)(fy + 199);
            if (zoomed()) { xy[2] = bg_quad[2]; xy[3] = bg_quad[3]; }
        }
    }
    /* +44 is the see-through share (live check 2026-10-19: 0.7 showed names ~30%); native semi = 0.5 */
    if (enemy_quad[2]) {   /* IconSize: stretch the 4 x 4 PSX enemy sprite around its centre */
        int16_t *xy = (int16_t *)(cmd + 8);
        xy[0] = (int16_t)enemy_quad[0]; xy[1] = (int16_t)enemy_quad[1]; xy[2] = (int16_t)enemy_quad[2]; xy[3] = (int16_t)enemy_quad[3];
    }
    if (semi_layer) *(float *)(cmd + 44) = 1.0f - (semi_layer == 2 ? blink_alpha : semi_layer >= ICON_LAYER ? icon_alpha : name_alpha);
    uint16_t *uv = (uint16_t *)(cmd + 16);
    uv[0] = (uint16_t)(uv[0] * ov_uv_scale); uv[1] = (uint16_t)(uv[1] * ov_uv_scale);
    uv[2] = (uint16_t)((uv[2] + 1) * ov_uv_scale - 1); uv[3] = (uint16_t)((uv[3] + 1) * ov_uv_scale - 1);
}
__attribute__((naked)) static void submit_stub(void) {
    __asm__ volatile("pushl %ecx\n pushl 8(%esp)\n call _ov_scale_command\n addl $4,%esp\n popl %ecx\n cmpl $0,_ov_uv_scale\n je 1f\n cmpl $0,_ov_fullscreen\n je 1f\n movl $25,8(%esp)\n cmpl $0,_drawing_background\n je 1f\n movl $26,8(%esp)\n cmpl $1,_drawing_background\n jne 1f\n movl $27,8(%esp)\n1: movl $0x47a9b0,%eax\n jmp *%eax\n");
}

static int patch_call(uintptr_t at, uintptr_t expect, void *target) {
    if (*(unsigned char *)at != 0xe8 || at + 5 + *(int32_t *)(at + 1) != expect) return 0;
    DWORD old, ignored;
    if (!VirtualProtect((void *)at, 5, PAGE_EXECUTE_READWRITE, &old)) return 0;
    *(int32_t *)(at + 1) = (int32_t)((uintptr_t)target - at - 5);
    FlushInstructionCache(GetCurrentProcess(), (void *)at, 5);
    VirtualProtect((void *)at, 5, old, &ignored);
    return 1;
}

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, void *unused) {
    (void)unused;
    if (reason != DLL_PROCESS_ATTACH) return TRUE;
    DisableThreadLibraryCalls(inst);
    /* ASI loader: INI/log beside the module (scripts\RE1.AnnotatedMap.ini).
     * REbirth maps mod modules itself, so GetModuleFileName(inst) fails there: use <exe dir>\mod_annotated_map\ */
    static const char stem[] = "mod_annotated_map\\RE1.AnnotatedMap.";
    char path[MAX_PATH]; DWORD n = GetModuleFileNameA(inst, path, MAX_PATH);
    if (n && n < MAX_PATH) {
        while (n && path[n - 1] != '.' && path[n - 1] != '\\') n--;
        if (!n || path[n - 1] != '.') return TRUE;
    } else {
        n = GetModuleFileNameA(NULL, path, MAX_PATH);
        while (n && path[n - 1] != '\\') n--;
        if (!n || n + sizeof stem + 4 >= MAX_PATH) return TRUE;
        memcpy(path + n, stem, sizeof stem); n += sizeof stem - 1;
    }
    if (n + 4 >= MAX_PATH) return TRUE;
    memcpy(ini_path, path, n); memcpy(ini_path + n, "ini", 4);
    memcpy(log_path, path, n); memcpy(log_path + n, "log", 4);
    log_fmt("DllMain module=%x file=%d", (int)(uintptr_t)inst, (int)GetModuleFileNameA(inst, path, MAX_PATH), 0, 0);
    if ((uintptr_t)GetModuleHandleA(NULL) != 0x400000) return TRUE;
    IMAGE_NT_HEADERS32 *nt = (void *)(0x400000 + ((IMAGE_DOS_HEADER *)0x400000)->e_lfanew);
    if (nt->FileHeader.TimeDateStamp != EXE_TIMESTAMP || nt->OptionalHeader.SizeOfImage != EXE_IMAGE_SIZE) { log_text("Unsupported Biohazard.exe; not installed"); return TRUE; }
    if (!GetModuleHandleA("ddraw.dll")) { log_text("Classic REbirth ddraw.dll not loaded; not installed"); return TRUE; }
    static const uintptr_t draw_sites[] = {0x43c491, 0x43c4f3, 0x43c53f, 0x43c5f5, 0x43c620, 0x43c645, 0x43c704, 0x43c773, 0x43c784};
    /* verify everything before patching anything */
    for (unsigned i = 0; i < sizeof draw_sites / sizeof *draw_sites; i++) {
        uintptr_t a = draw_sites[i];
        if (*(unsigned char *)a != 0xe8 || a + 5 + *(int32_t *)(a + 1) != 0x43c7c0) { log_fmt("Unexpected map draw site %x", (int)a, 0, 0, 0); return TRUE; }
    }
    const uintptr_t up[] = {0x43c158, 0x43c2bc};
    for (unsigned i = 0; i < 2; i++) if (*(unsigned char *)up[i] != 0xe8 || up[i] + 5 + *(int32_t *)(up[i] + 1) != 0x43f950) { log_text("Unexpected upload site"); return TRUE; }
    if (*(unsigned char *)0x441de5 != 0xe8 || 0x441de5 + 5 + *(int32_t *)(0x441de6) != 0x47a9b0) { log_text("Unexpected Add_sprt submit site"); return TRUE; }
    const uintptr_t direct_sites[] = {0x48d0aa, 0x48d0a2, 0x40b5ac, 0x40b5c2, 0x40b91b, 0x40b958, 0x40b96b, 0x40b6d6, 0x40b6ed, 0x43be2a};
    const uintptr_t direct_targets[] = {0x414dd0, 0x414e60, 0x4172c0, 0x40ba50, 0x40ba50, 0x40ba50, 0x40bb60, 0x465a10, 0x488310, 0x43be40};
    void *direct_hooks[] = {camera_update_hook, camera_change_hook, menu_begin_hook, menu_cleanup_hook,
                           menu_cleanup_hook, menu_cleanup_hook, menu_ui_hook, menu_input_hook, menu_status_draw_hook, selector_draw_hook};
    for (unsigned i = 0; i < sizeof direct_sites / sizeof *direct_sites; i++) {
        uintptr_t at = direct_sites[i];
        if (*(unsigned char *)at != 0xe8 || at + 5 + *(int32_t *)(at + 1) != direct_targets[i]) {
            log_fmt("Unexpected direct map call %x", (int)at, 0, 0, 0); return TRUE;
        }
    }
    load_settings();
    for (unsigned i = 0; i < sizeof draw_sites / sizeof *draw_sites; i++) patch_call(draw_sites[i], 0x43c7c0, (void *)map_draw_hook);
    patch_call(0x43c158, 0x43f950, (void *)upload_page_hook);
    patch_call(0x43c2bc, 0x43f950, (void *)upload_flash_hook);
    patch_call(0x441de5, 0x47a9b0, (void *)submit_stub);
    for (unsigned i = 0; i < sizeof direct_sites / sizeof *direct_sites; i++) patch_call(direct_sites[i], direct_targets[i], direct_hooks[i]);
    log_fmt("Annotated Map installed: markers=%d bitmaps=%d lang=%d scope=%d", OV_MARKER_COUNT, OV_BITMAP_COUNT, english, scope);
    return TRUE;
}
