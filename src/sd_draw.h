/* ---------- SD mode (Classic REbirth HD loader off, user decisions 2026-11-12, common/SD-MAP-PORTING.md): markers, room names, leaders
 * and legend are drawn at 1 texel = 1 PSX pixel from the SD atlas (sd_assets.h, tools/build_sd.py). The map is composed on the CPU
 * into three screen-sized layers (map: icons + names + leaders; legend; floor/area arrows), each held in two 256x256 4bpp textures
 * (x 0..255, x 256..319), and re-composed every frame; unchanged textures are not uploaded again. Included by re1_map.c. */
#include "sd_assets.h"

enum { SD_LAYER_MAP, SD_LAYER_LEGEND, SD_LAYER_NAV, SD_LAYERS };
#define SD_FULL_LEGEND_TOP SD_FULL_BAND
static unsigned char sd_px[SD_LAYERS][2][TILE_TEX * TILE_TEX / 2];
static unsigned char sd_used[SD_LAYERS][2];
static Tile sd_tile[SD_LAYERS][2];
static uint32_t sd_held[SD_LAYERS][2], sd_want[SD_LAYERS][2];
static unsigned short sd_map_pal[16];
static int sd_clip[4];   /* x0, y0, x1, y1 (exclusive) of the layer being composed */
static unsigned char sd_arrow_px[TILE_TEX * TILE_TEX / 2];
static int sd_arrows_failed;

static void sd_put(int layer, int x, int y, unsigned v) {
    if (x < sd_clip[0] || y < sd_clip[1] || x >= sd_clip[2] || y >= sd_clip[3]) return;
    int t = x >> 8, lx = x & 255;
    unsigned char *b = &sd_px[layer][t][y * 128 + (lx >> 1)];
    *b = (lx & 1) ? (unsigned char)((*b & 0x0f) | (v << 4)) : (unsigned char)((*b & 0xf0) | v);
    sd_used[layer][t] = 1;
}
static void sd_fill(int layer, int x0, int y0, int x1, int y1, unsigned v) {   /* exclusive end */
    for (int y = y0; y < y1; y++) for (int x = x0; x < x1; x++) sd_put(layer, x, y, v);
}
static void sd_icon(int layer, unsigned id, int x, int y) {
    const SdIcon *ic = &sd_icons[id];
    const unsigned char *p = sd_icon_px + ic->off;
    for (int j = 0; j < ic->h; j++) for (int i = 0; i < ic->w; i++) if (p[j * ic->w + i]) sd_put(layer, x + i, y + j, p[j * ic->w + i]);
}
/* ink mask drawn twice: a black shadow 1 px down-right, then the ink in `colour` (a palette index of the layer) */
static void sd_text(int layer, unsigned id, int x, int y, unsigned colour) {
    const SdText *t = &sd_texts[id];
    unsigned stride = (t->w + 7u) >> 3;
    for (int pass = 0; pass < 2; pass++)
        for (int j = 0; j < t->h; j++) for (int i = 0; i < t->w; i++)
            if ((sd_text_px[t->off + j * stride + (i >> 3)] >> (7 - (i & 7))) & 1) sd_put(layer, x + i + !pass, y + j + !pass, pass ? colour : 1);
}
static void sd_line(int layer, int x0, int y0, int x1, int y1, unsigned c) {   /* 1 px Bresenham */
    int dx = x1 > x0 ? x1 - x0 : x0 - x1, dy = y1 > y0 ? y0 - y1 : y1 - y0, sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1, err = dx + dy;
    for (;;) {
        sd_put(layer, x0, y0, c);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

/* icons: enemies first (names and other icons lie over them) */
static void sd_icons_pass(unsigned page, int view, int dx, int dy, int enemies) {
    for (unsigned i = 0; i < OV_MARKER_COUNT; i++) {
        const SdMark *k = &sd_marks[i];
        const OvMarker *m = &ov_markers[i];
        if (k->icon == 0xFFFF || (m->kind == 7) != enemies || !marker_visible(m, page)) continue;
        if (k->cover[view] >= 0 && marker_visible(&ov_markers[k->cover[view]], page)) continue;   /* waits under a key item / puzzle */
        unsigned id = view == 0 ? k->small : k->icon;   /* the status screen has smaller pictures (7x7, enemies 3x3) */
        const SdIcon *ic = &sd_icons[id];
        int x = k->pos[view][0] + dx, y = k->pos[view][1] + dy;
        if (view == 2 && (x < 0 || y < ZVIEW_TOP || x + ic->w > 320 || y + ic->h > zview_bottom())) continue;   /* a marker the window edge would slice is left out */
        sd_icon(SD_LAYER_MAP, id, x, y);
    }
}
/* room names and leaders (views 1, 2), fixed on the map at build time (tools/sd_layout.py): they scroll with the room, nothing is
 * pulled inside the screen or re-ended at run time, and what lies beyond the map window is cut (user 2026-11-13). A name inside its
 * room has no leader. Crowded pages (Mansion 1F / 2F) have no names on the 1x full-screen map. */
static void sd_names(unsigned page, int view, int dx, int dy) {
    int lang = english ? 0 : 1;
    if (view == 1 && sd_crowded[page]) return;
    for (unsigned i = 0; i < SD_ROOM_COUNT; i++) {
        const SdRoom *r = &sd_rooms[i];
        const SdName *n = &r->v[view - 1][lang];
        if (n->sprite == 0xFFFF || !marker_visible(&ov_markers[r->marker], page)) continue;
        for (int k = 1; k < n->n; k++)
            sd_line(SD_LAYER_MAP, n->pt[2 * k - 2] + dx, n->pt[2 * k - 1] + dy, n->pt[2 * k] + dx, n->pt[2 * k + 1] + dy, 2);
        sd_text(SD_LAYER_MAP, n->sprite, n->x + dx, n->y + dy, 2);
    }
}
/* legend: category rows in their colour (grey when off), then scope, language, zoom or tab hint and [~] */
static void sd_cell(const SdCell *c) {
    static const unsigned char col[9] = {15, 2, 5, 3, 4, 6, 13, 7, 10};   /* legend CLUT: all, rooms, locks, key, files, puzzles, events, items, enemies */
    int lang = english ? 0 : 1;
    unsigned id, ink = 15;
    switch (c->r) {
    case 9: id = sd_scope[scope - 1][lang]; break;
    case 10: id = sd_lang[lang]; break;
    case 11: id = sd_zoom[ov_zoom ? 1 : 0][lang]; ink = 9; break;
    case 12: id = sd_tab[direct_active ? 1 : 0][lang]; ink = 9; break;
    case 13: id = sd_hide[lang]; break;
    default: id = sd_row[c->r][lang]; ink = toggles[c->r] ? col[c->r] : 8; break;
    }
    sd_text(SD_LAYER_LEGEND, id, c->x, c->y, ink);
}
static void sd_legend(unsigned page) {
    int lang = english ? 0 : 1;
    if (ov_fullscreen) {
        static const SdCell zoom_hint = {11, 8, 19};
        if (zoomed()) {   /* the title and the hint lie over the scrolling map: give them a box */
            int w = sd_texts[sd_title[page][lang]].w, hw = sd_texts[sd_zoom[1][lang]].w;
            sd_fill(SD_LAYER_LEGEND, 0, 0, 8 + (w > hw ? w : hw) + 5, 32, 1);
        }
        sd_text(SD_LAYER_LEGEND, sd_title[page][lang], 8, 8, 15);
        sd_cell(&zoom_hint);
    }
    if (!legend_on) {   /* folded: one line bottom-left on its own opaque box */
        const SdText *t = &sd_texts[sd_fold[lang]];
        int x = ov_fullscreen ? 0 : 2, y = ov_fullscreen ? 240 - t->h - 4 : SD_STATUS_FOLD_Y;
        sd_fill(SD_LAYER_LEGEND, x, y, x + t->w + 6, y + t->h + 3, 1);
        sd_text(SD_LAYER_LEGEND, sd_fold[lang], x + 3, y + 1, 15);
        return;
    }
    if (ov_fullscreen) sd_fill(SD_LAYER_LEGEND, 0, SD_FULL_LEGEND_TOP, 320, 240, 1);
    for (unsigned k = 0; k < (ov_fullscreen ? SD_FULL_CELLS : SD_STATUS_CELLS); k++) sd_cell(ov_fullscreen ? &sd_full_cells[k] : &sd_status_cells[k]);
}
static void sd_nav(void) {
    int can[4];
    if (!ov_fullscreen || zoomed()) return;
    nav_can(can);
    if (can[0]) sd_icon(SD_LAYER_NAV, sd_nav_icon[0], 154, 2);
    if (can[1]) sd_icon(SD_LAYER_NAV, sd_nav_icon[1], 154, 194);
    if (can[2]) sd_icon(SD_LAYER_NAV, sd_nav_icon[2], 5, 114);
    if (can[3]) sd_icon(SD_LAYER_NAV, sd_nav_icon[3], 306, 114);
}

static void sd_frame(unsigned page, int left, int top) {
    int view = zoomed() ? 2 : ov_fullscreen ? 1 : 0;
    int dx = view == 2 ? -ov_pan_x : view == 0 ? left : 0, dy = view == 2 ? ZVIEW_TOP - ov_pan_y : view == 0 ? top : 0;
    memset(sd_px, 0, sizeof sd_px); memset(sd_used, 0, sizeof sd_used);
    memcpy(sd_map_pal, sd_pal, sizeof sd_map_pal);
    sd_map_pal[2] = legend_pal[ov_color_index[0]];   /* names and leaders: the Rooms colour of the legend */
    sd_clip[0] = 0; sd_clip[1] = view == 2 ? ZVIEW_TOP : 0; sd_clip[2] = 320; sd_clip[3] = view == 2 ? zview_bottom() : 240;
    if (toggles[T_ALL]) {
        sd_icons_pass(page, view, dx, dy, 1);
        if (view && toggles[T_ROOMS]) sd_names(page, view, dx, dy);
        sd_icons_pass(page, view, dx, dy, 0);
    }
    sd_clip[1] = 0; sd_clip[3] = 240;
    sd_legend(page);
    sd_nav();
    if (ov_fullscreen && !sd_arrows.used && !sd_arrows_failed) {   /* player arrow: 16 headings in 4 x 4 cells of 9 px */
        for (int k = 0; k < 16; k++) {
            const SdIcon *ic = &sd_icons[sd_arrow_icon[k]];
            for (int j = 0; j < 9; j++) for (int i = 0; i < 9; i++) {
                unsigned v = sd_icon_px[ic->off + j * 9 + i];
                int x = (k % 4) * 9 + i, y = (k / 4) * 9 + j;
                unsigned char *b = &sd_arrow_px[y * 128 + (x >> 1)];
                if (v) *b = (x & 1) ? (unsigned char)((*b & 0x0f) | (v << 4)) : (unsigned char)((*b & 0xf0) | v);
            }
        }
        if (!upload_tile(&sd_arrows, sd_arrow_px, sd_map_pal, TILE_TEX)) sd_arrows_failed = 1;
    }
    for (int l = 0; l < SD_LAYERS; l++) for (int t = 0; t < 2; t++) {
        uint32_t h = sd_used[l][t] ? tile_hash_of(sd_px[l][t], 1) : 0;
        sd_want[l][t] = h;
        if (h == sd_held[l][t] && (h == 0 || sd_tile[l][t].used)) continue;
        release_tile(&sd_tile[l][t]); sd_held[l][t] = 0;
    }
}
static void sd_service(void) {   /* legend first, then the map, at most ov_upload_budget textures per frame */
    static const unsigned char order[SD_LAYERS] = {SD_LAYER_LEGEND, SD_LAYER_MAP, SD_LAYER_NAV};
    static unsigned logged_failures, logged_ok;
    if (!logged_ok && sd_tile[SD_LAYER_LEGEND][0].used) { logged_ok = 1; log_text("SD textures uploaded (first legend texture)"); }
    if (tile_failed != logged_failures) { logged_failures = tile_failed; log_fmt("SD texture upload failures so far: %d", (int)tile_failed, 0, 0, 0); }
    for (int o = 0; o < SD_LAYERS; o++) for (int t = 0; t < 2; t++) {
        int l = order[o];
        if (sd_want[l][t] && !sd_tile[l][t].used && sd_held[l][t] != sd_want[l][t])
            if (!upload_one(&sd_tile[l][t], &sd_held[l][t], sd_want[l][t], sd_px[l][t], l == SD_LAYER_LEGEND ? legend_pal : sd_map_pal)) return;
    }
}
static void sd_draw_layers(void) {
    for (int l = 0; l < SD_LAYERS; l++) for (int t = 0; t < 2; t++) {
        if (!sd_tile[l][t].used) continue;
        semi_layer = l == SD_LAYER_NAV ? 2 : 0;   /* the floor / area arrows pulse as in HD */
        draw_part(&sd_tile[l][t], t * 256, 0, 0, 0, t ? 64 : 256, 240);
        semi_layer = 0;
    }
}
