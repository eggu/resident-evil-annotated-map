/* Annotated Map for original Resident Evil (GOG Biohazard.exe + Classic REbirth 1.1.4).
 * Draws room names, locked doors, items, files, puzzles and save points over the native status-screen map.
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

enum { T_ALL, T_ROOMS, T_LOCKS, T_KEYS, T_DOCS, T_PUZZLES, T_COMMON, T_COUNT };
static const char *const toggle_keys[T_COUNT] = {"All", "Rooms", "Locks", "KeyItems", "Documents", "Puzzles", "CommonItems"};
static int toggles[T_COUNT];
static int scope = 1, english = 1, offset_x, offset_y, overlay_z = 0x10, room_tint = 1;
static int arrow_rotation;   /* INI [Calibration] ArrowRotation (degrees) if the player-heading convention is off */
static float name_alpha = 0.7f, blink_alpha;   /* blink_alpha: visible share for arrows this frame */   /* name layer opacity; native semi-transparent sprites use 0.5 */
static void save_settings(void) {
    char v[12];
    for (int i = 0; i < T_COUNT; i++) { v[0] = (char)('0' + toggles[i]); v[1] = 0; WritePrivateProfileStringA("AnnotatedMap", toggle_keys[i], v, ini_path); }
    v[0] = (char)('0' + scope); WritePrivateProfileStringA("AnnotatedMap", "Scope", v, ini_path);
    WritePrivateProfileStringA("AnnotatedMap", "Language", english ? "en" : "ko", ini_path);
}
static int key_code(const char *v, int def);
static int pad_code(const char *v, int def);
static int open_vk, close_vk, open_pad, close_on_cancel;
static void load_settings(void) {
    for (int i = 0; i < T_COUNT; i++) toggles[i] = GetPrivateProfileIntA("AnnotatedMap", toggle_keys[i], 1, ini_path) != 0;
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
    GetPrivateProfileStringA("Keys", "OpenKey", "M", k, sizeof k, ini_path); open_vk = key_code(k, 'M');
    GetPrivateProfileStringA("Keys", "OpenPad", "RB", k, sizeof k, ini_path); open_pad = pad_code(k, 0x0200);
    GetPrivateProfileStringA("Keys", "CloseKey", "ESC", k, sizeof k, ini_path); close_vk = key_code(k, VK_ESCAPE);
    close_on_cancel = GetPrivateProfileIntA("Keys", "CloseOnCancel", 1, ini_path) != 0;

    name_alpha = (float)(opacity < 10 ? 10 : opacity > 100 ? 100 : opacity) / 100.0f;  /* off if REbirth HD map replacement misbehaves */
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
    static const unsigned char kind_toggle[7] = {0, T_ROOMS, T_LOCKS, T_KEYS, T_DOCS, T_PUZZLES, T_COMMON};
    if (m->page != page || !toggles[kind_toggle[m->kind]]) return 0;
    if (!(m->chars & (jill() ? 2 : 1))) return 0;
    if (m->side) {   /* lock key: label the room not visited yet, else the destination (RE1 HD map mod rule) */
        int own = slot_visited(m->stage, m->slot), dst = slot_visited(m->tstage, m->tslot);
        if ((m->side == 2) != (dst && !own)) return 0;
        if (!room_known(m->stage, m->slot, m->page, 0) && !room_known(m->tstage, m->tslot, m->page, 0)) return 0;
    } else if (!room_known(m->stage, m->slot, m->page, m->kind == 1)) return 0;
    if (m->flagtype == 1 && !flag_on(FLG_PICKUP, m->flag)) return 0;   /* set = still there; pickup clears (0x414fe0) */
    if (m->flagtype == 1 && !guards_pass(m->guard[jill() ? 1 : 0])) return 0;
    if (m->flagtype == 2 && flag_on(FLG_DOOR, m->flag)) return 0;
    if (m->flagtype == 3) {   /* puzzle solved: every curated condition holds (reward taken / SCD flag) */
        int solved = 1;
        for (const unsigned short *c = ov_conds[m->flag]; c[0] != 255; c += 3)
            if (c[0] > 9 || ck(c[0], c[1]) != (c[2] != 0)) { solved = 0; break; }
        if (solved) return 0;
    }
    return 1;
}

/* Fullscreen map keys (INI [Keys]): OpenKey / OpenPad open it at the original gameplay gate; the same key or button,
 * CloseKey, or the game's cancel action (CloseOnCancel) close it. Pad buttons are read with XInput (loaded at runtime). */
static int direct_pending, direct_active, direct_init;
/* defaults: M / RB to open, Esc or cancel to close (set in load_settings) */
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
/* layer 0: icons, legend, titles (opaque); 1: names + leader lines (NameOpacity); 2: floor/area arrows (blinking) */
#define LAYERS 3
static Tile tiles[LAYERS][TILES_X * TILES_Y], background, terrain, outline, arrows;
static int layer;
static int drawing_background, semi_layer;
static unsigned nav_held;
static int compose_needed = 1;
static unsigned cached_page = ~0u;
static int cached_left, cached_top, cached_fullscreen;
static DWORD nav_repeat_at;
static unsigned char terrain_px[BG_TEX * BG_TEX / 2], outline_px[BG_TEX * BG_TEX / 2];
static unsigned char tile_px[LAYERS][TILES_X * TILES_Y][TILE_TEX * TILE_TEX / 2];
static unsigned char tim_buf[20 + 32 + 12 + TILE_TEX * TILE_TEX / 2];
__declspec(dllexport) volatile int ov_fullscreen;
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
static void blit(int bid, int x, int y) {
    if (bid < 0) return;
    const OvBitmap *b = &ov_bitmaps[bid];
    const unsigned char *src = ov_pixels + b->off;
    unsigned row = (b->w + 1u) / 2u;
    for (int j = 0; j < b->h; j++) {
        int py = y + j; if (py < 0 || py >= TILES_Y * TILE_TEX) continue;
        for (int i = 0; i < b->w; i++) {
            int px = x + i; if (px < 0 || px >= TILES_X * TILE_TEX) continue;
            unsigned v = (src[j * row + i / 2] >> ((i & 1) * 4)) & 15; if (!v) continue;
            unsigned ti = (unsigned)(py / TILE_TEX) * TILES_X + (unsigned)(px / TILE_TEX);
            unsigned lx = (unsigned)(px % TILE_TEX), ly = (unsigned)(py % TILE_TEX);
            unsigned char *d = &tile_px[layer][ti][ly * (TILE_TEX / 2) + lx / 2];
            *d = (lx & 1) ? (unsigned char)((*d & 0x0f) | (v << 4)) : (unsigned char)((*d & 0xf0) | v);
            tile_dirty[layer][ti] = 1;
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
        if (c == 1 || c == 2) {   /* wall / door cell: fill with a neighbouring room's colour */
            static const int nb[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
            c = 0;
            for (int k = 0; k < 4 && !c; k++) {
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
    for (int y = y0; y <= y1; y++) for (int x = x0; x <= x1; x++) {
        if (x < 0 || y < 0 || x >= TILES_X * TILE_TEX || y >= TILES_Y * TILE_TEX) continue;
        unsigned ti = (unsigned)(y / TILE_TEX) * TILES_X + (unsigned)(x / TILE_TEX), lx = (unsigned)(x % TILE_TEX), ly = (unsigned)(y % TILE_TEX);
        unsigned char *d = &tile_px[layer][ti][ly * (TILE_TEX / 2) + lx / 2];
        *d = (lx & 1) ? (unsigned char)((*d & 0x0f) | (v << 4)) : (unsigned char)((*d & 0xf0) | v);
        tile_dirty[layer][ti] = 1;
    }
}

static void compose(unsigned page, int ox, int oy) {
    /* clear only tiles the previous compose drew into (31 MB of tiles at OV_SCALE 16) */
    for (int k = 0; k < LAYERS; k++) for (unsigned t = 0; t < TILES_X * TILES_Y; t++)
        if (tile_dirty[k][t]) { memset(tile_px[k][t], 0, sizeof tile_px[k][t]); tile_dirty[k][t] = 0; }
    if (ov_fullscreen) {
        memset(terrain_px, 0, sizeof terrain_px); memset(outline_px, 0, sizeof outline_px);
        compose_terrain(page);
        if (!background.used) upload_tile(&background, ov_background_pixels, ov_background_palette, BG_TEX);
        if (!arrows.used) upload_tile(&arrows, ov_arrow_pixels, ov_palette, TILE_TEX);
        release_tile(&terrain); release_tile(&outline);
        upload_tile(&terrain, terrain_px, ov_terrain_palette, BG_TEX);
        upload_tile(&outline, outline_px, ov_terrain_palette, BG_TEX);
    }
    if (toggles[T_ALL]) {
        for (unsigned i = 0; i < OV_MARKER_COUNT; i++) {
            const OvMarker *m = &ov_markers[i];
            if (!marker_visible(m, page)) continue;
            int view = ov_fullscreen ? 1 : 0, bx = view ? 0 : ox, by = view ? 0 : oy;   /* fullscreen coords are absolute */
            if (m->icon >= 0) blit(m->icon, bx + m->ico[view][0], by + m->ico[view][1]);
            const OvLabel *l = &m->lab[view][english ? 0 : 1];
            layer = 1;
            if (l->bid >= 0 && view) blit(l->bid, bx + l->x, by + l->y);   /* status screen: icons only */
            layer = 0;
        }
    }
    if (toggles[T_ALL] && toggles[T_ROOMS])
        for (unsigned i = 0; i < OV_LINE_COUNT; i++) {   /* leader lines of names placed outside their room */
            const OvLine *ln = &ov_lines[i];
            const OvMarker *m = &ov_markers[ln->marker];
            if (ln->view != (ov_fullscreen ? 1 : 0) || ln->lang != (english ? 0 : 1) || !marker_visible(m, page)) continue;
            int bx = ov_fullscreen ? 0 : ox, by = ov_fullscreen ? 0 : oy;
            layer = 1;
            fill_rect(bx + (ln->x0 < ln->x1 ? ln->x0 : ln->x1) - OV_SCALE / 4, by + (ln->y0 < ln->y1 ? ln->y0 : ln->y1) - OV_SCALE / 4,
                      bx + (ln->x0 > ln->x1 ? ln->x0 : ln->x1), by + (ln->y0 > ln->y1 ? ln->y0 : ln->y1), 7);
            layer = 0;
        }
    if (ov_fullscreen) {
        /* RE2-style: area title top-left, DISPLAY STATUS block bottom-left, blinking green floor/area arrows */
        blit(ov_page_titles[page][english ? 0 : 1], 10 * OV_SCALE, 8 * OV_SCALE);
        int lang = english ? 0 : 1;
        blit(ov_full_legend_title[lang], 8 * OV_SCALE, 205 * OV_SCALE);
        for (int r = 0; r < 10; r++) {
            int variant = r == 7 ? (direct_active ? 2 : 0) : r == 8 ? scope - 1 : 0;
            int off = r <= 6 && !toggles[r];
            blit(ov_full_legend[r][variant][off][lang], (8 + (r >= 5 ? OV_FULL_LEGEND_COL2 : 0)) * OV_SCALE, (210 + 5 * (r % 5)) * OV_SCALE);
        }
        unsigned area = MAP_STATE[4], up_down = MAP_STATE[12], areas = MAP_STATE[13];
        /* raw 0x80 (LEFT, RE1-Mod-SDK KEY_LEFT 8) -> area+1 / table 0x43bd08; raw 0x20 (RIGHT) -> area-1 / table 0x43bd18 */
        static const signed char left_special[4] = {3, 2, -1, 1}, right_special[4] = {-1, 3, 1, 0};
        int can[4];
        can[0] = (up_down & 1) != 0; can[1] = (up_down & 2) != 0;
        if (areas & 8) { can[2] = area < 4 && left_special[area] >= 0; can[3] = area < 4 && right_special[area] >= 0; }
        else { can[2] = area != 2 && (areas & (1u << (area + 1))); can[3] = area > 0 && (areas & (1u << (area - 1))); }
        layer = 2;
        if (can[0]) blit(ov_nav[0], (320 * OV_SCALE - ov_bitmaps[ov_nav[0]].w) / 2, 2 * OV_SCALE);
        if (can[1]) blit(ov_nav[1], (320 * OV_SCALE - ov_bitmaps[ov_nav[1]].w) / 2, (240 * OV_SCALE - ov_bitmaps[ov_nav[1]].h) - 4 * OV_SCALE);
        if (can[2]) blit(ov_nav[2], 5 * OV_SCALE, (120 * OV_SCALE - ov_bitmaps[ov_nav[2]].h / 2));
        if (can[3]) blit(ov_nav[3], 315 * OV_SCALE - ov_bitmaps[ov_nav[3]].w, (120 * OV_SCALE - ov_bitmaps[ov_nav[3]].h / 2));
        layer = 0;
    } else {
        /* status screen: legend in hotkey order 0..9 on one line below the floor drawing (box x 32..137 PSX) */
        static const unsigned char order[] = {1, 2, 3, 4, 5, 6, 7, 11, 8, 10};
        int x = ox - 16 * OV_SCALE;
        for (unsigned r = 0; r < sizeof order; r++) {
            unsigned row = order[r];
            int on = row >= 8 ? 1 : toggles[row - 1];
            if (row == 8) row = scope == 3 ? 9 : scope == 2 ? 14 : 8;
            int bid = ov_legend[row][(on ? 0 : 2) + (english ? 0 : 1)];
            blit(bid, x, oy + 95 * OV_SCALE);
            x += ov_bitmaps[bid].w + OV_STATUS_LEGEND_GAP * OV_SCALE;
        }
    }
    /* texture uploads dominate a recompose (REbirth HD path per TIM): keep tiles whose pixels did not change */
    static uint32_t tile_hash[LAYERS][TILES_X * TILES_Y];
    for (unsigned t = 0; t < TILES_X * TILES_Y; t++) {
        for (int k = 0; k < LAYERS; k++) {
            uint32_t h = 0;
            if (tile_dirty[k][t]) {
                h = 2166136261u;
                const uint32_t *w = (const uint32_t *)tile_px[k][t];
                for (unsigned i = 0; i < TILE_TEX * TILE_TEX / 8; i++) h = (h ^ w[i]) * 16777619u;
                h |= 1;
            }
            if (h && h == tile_hash[k][t] && tiles[k][t].used) continue;
            release_tile(&tiles[k][t]);
            tile_hash[k][t] = 0;
            if (h && upload_tile(&tiles[k][t], tile_px[k][t], ov_palette, TILE_TEX)) tile_hash[k][t] = h;
        }
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
    semi_layer = 2;
    draw_part(&arrows, sxp - OV_ARROW_CELL / 2, syp - OV_ARROW_CELL / 2, (best % 4) * OV_ARROW_CELL, (best / 4) * OV_ARROW_CELL, OV_ARROW_CELL, OV_ARROW_CELL);
    semi_layer = 0;
}
static void draw_part(Tile *tile, int x, int y, int u, int v, int w, int h) {
    if (w <= 0 || h <= 0) return;
    unsigned char sp[36]; memset(sp, 0, sizeof sp);
    if (drawing_background) *(uint32_t *)sp = drawing_background == 2 ? 0x50000000u : drawing_background == 3 ? 0 : 0x40000000u;
    else if (semi_layer) *(uint32_t *)sp = 0x50000000u;   /* names: same semi-transparency as the native map sprite (0x51000000) */
    *(int16_t *)(sp + 4) = (int16_t)x; *(int16_t *)(sp + 6) = (int16_t)y;
    *(uint16_t *)(sp + 8) = (uint16_t)w; *(uint16_t *)(sp + 10) = (uint16_t)h;
    sp[14] = (unsigned char)u; sp[15] = (unsigned char)v;
    *(uint16_t *)(sp + 18) = 480;
    sp[20] = sp[21] = sp[22] = 128;
    memcpy(TEX_SLOT, tile->state, SLOT_SIZE);
    ov_uv_scale = drawing_background ? 1 : OV_SCALE; add_sprt(sp, overlay_z, -2, 1); ov_uv_scale = 0;
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
    blink_alpha = (GetTickCount() / 400) & 1 ? 0.85f : 0.35f;   /* arrows pulse bright/dim, never vanish */
    for (unsigned t = 0; t < TILES_X * TILES_Y; t++) {
        for (int k = 0; k < LAYERS; k++) {
        if (!tiles[k][t].used) continue;
        int bx = (int)(t % TILES_X) * TILE_PSX, by = (int)(t / TILES_X) * TILE_PSX;
        semi_layer = k; draw_part(&tiles[k][t], bx, by, 0, 0, TILE_PSX, TILE_PSX); semi_layer = 0;
        }
    }
    if (ov_fullscreen && arrows.used) draw_player();
    memcpy(TEX_SLOT, saved, SLOT_SIZE);
}

static void render_overlay(unsigned page, int left, int top);

static void __cdecl menu_begin_hook(int a, int b) {
    compose_needed = 1;
    ((void(__cdecl *)(int, int))0x4172c0)(a, b);
    if (!direct_pending) return;
    log_text("M direct viewer selected: native map init deferred");
    direct_pending = 0; direct_active = 1; direct_init = 1; ov_fullscreen = 1; nav_held = 0;
    *(volatile unsigned char *)0xC2E930 = 0;
    /* Let the original first menu frame initialize the map in its normal order. */
    *(volatile unsigned char *)0xC2E931 = 0;
    *(volatile unsigned char *)0xC2E940 = 0;
}
static void __cdecl menu_cleanup_hook(void) {
    compose_needed = 1;
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
    if (!held && !pressed) { nav_held = 0; return; }
    DWORD now = GetTickCount();
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
static unsigned keys_down;
static int poll_keys(void) {
    DWORD pid = 0; GetWindowThreadProcessId(GetForegroundWindow(), &pid);
    if (pid != GetCurrentProcessId()) { keys_down = 0; return 0; }
    unsigned now = 0;
    for (int k = 0; k <= 9; k++)
        if ((GetAsyncKeyState('0' + k) | GetAsyncKeyState(VK_NUMPAD0 + k)) & 0x8000) now |= 1u << k;
    unsigned pressed = now & ~keys_down; keys_down = now;
    if (!pressed) return 0;
    int retint = 0;
    for (int k = 0; k <= 6; k++) if (pressed & (1u << k)) { toggles[k] = !toggles[k]; retint |= k == 0 || k == 3 || k == 4 || k == 6; }
    if (pressed & (1u << 7)) { if (!direct_active) ov_fullscreen = !ov_fullscreen; }
    if (pressed & (1u << 8)) scope = scope % 3 + 1;   /* visited -> revealed -> all */
    if (pressed & (1u << 9)) english = !english;
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
static void render_overlay(unsigned page, int left, int top) {
    if (page > 10) return;
    int changed = poll_keys();
    if (compose_needed || changed || page != cached_page || ov_fullscreen != cached_fullscreen ||
        (!ov_fullscreen && (left != cached_left || top != cached_top))) {
        compose(page, left * OV_SCALE, top * OV_SCALE);
        cached_page = page; cached_left = left; cached_top = top; cached_fullscreen = ov_fullscreen;
        compose_needed = 0;
        log_fmt("compose page=%d origin=%d,%d fullscreen=%d", (int)page, left, top, ov_fullscreen);
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
            xy[0] = (int16_t)fx; xy[1] = (int16_t)fy; xy[2] = (int16_t)(fx + 255); xy[3] = (int16_t)(fy + 199);
        }
    }
    /* +44 is the see-through share (live check 2026-10-19: 0.7 showed names ~30%); native semi = 0.5 */
    if (semi_layer) *(float *)(cmd + 44) = 1.0f - (semi_layer == 2 ? blink_alpha : name_alpha);
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
    /* REbirth maps mod modules itself, so GetModuleFileName(inst) fails: use <exe dir>\mod_annotated_map\ */
    static const char stem[] = "mod_annotated_map\\RE1.AnnotatedMap.";
    char path[MAX_PATH]; DWORD n = GetModuleFileNameA(NULL, path, MAX_PATH);
    while (n && path[n - 1] != '\\') n--;
    if (!n || n + sizeof stem + 4 >= MAX_PATH) return TRUE;
    memcpy(path + n, stem, sizeof stem); n += sizeof stem - 1;
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
