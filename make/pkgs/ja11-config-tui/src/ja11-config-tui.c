/*
 * ja11-config-tui.c - Full-featured TUI configurator for FiiO JA11 (KT02H20)
 *
 * Communicates via HID (hidraw backend) with the KT02H20 chip inside
 * the FiiO JadeAudio JA11 to configure the 5-band parametric EQ,
 * DAC digital filters, global gain, and more.
 *
 * Based on reverse engineering from Audiocular-Aura:
 *   https://github.com/mandy321/Audiocular-Aura
 *
 * SPDX-License-Identifier: GPL-3.0-or-later
 *
 * Usage:
 *   ja11-config-tui            - English UI (default)
 *   ja11-config-tui --italian  - Italian UI
 *   ja11-config-tui -it        - Italian UI (short)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>
#include <math.h>
#include <ncurses.h>
#include <hidapi/hidapi.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <ctype.h>
#include <stdarg.h>
#include <locale.h>

#include "ja11-config-tui.h"

/* ============================================================
 * i18n Strings
 * ============================================================ */
typedef struct {
	const char *lang_name;
	/* UI */
	const char *title;
	const char *connected;
	const char *disconnected;
	const char *preamp;
	const char *band_hdr;
	const char *freq_hdr;
	const char *gain_hdr;
	const char *q_hdr;
	const char *type_hdr;
	const char *status_hdr;
	const char *dac_filter;
	const char *sync_ok;
	const char *sync_pending;
	const char *modified_warn;
	const char *status_conn;
	const char *status_disconn;
	const char *preset_label;
	/* Help navigation */
	const char *help_nav;
	const char *help_arrows;
	const char *help_coarse;
	const char *help_fine;
	const char *help_toggle;
	const char *help_cycle;
	/* Help device actions */
	const char *help_dev;
	const char *help_apply;
	const char *help_save;
	const char *help_read;
	const char *help_gain;
	/* Help DAC filters */
	const char *help_filter;
	/* Help presets */
	const char *help_presets;
	const char *help_psave;
	const char *help_pload;
	const char *help_pdel;
	/* Help other */
	const char *help_other;
	const char *help_reset_flat;
	const char *help_reset_def;
	const char *help_quit;
	/* Messages */
	const char *msg_filter_set;
	const char *msg_applied;
	const char *msg_saved;
	const char *msg_read_ok;
	const char *msg_gain_set;
	const char *msg_prompt_gain;
	const char *msg_prompt_pname;
	const char *msg_prompt_pload;
	const char *msg_confirm_save;
	const char *msg_confirm_del;
	const char *msg_no_presets;
	const char *msg_preset_saved;
	const char *msg_preset_loaded;
	const char *msg_preset_deleted;
	const char *msg_cancelled;
	const char *msg_no_device;
	const char *msg_udev_hint;
} Lang;

static const Lang lang_en = {
	.lang_name      = "English",
	.title          = "FiiO JA11 (KT02H20) - Full PEQ Configurator",
	.connected      = "CONNECTED:",
	.disconnected   = "DISCONNECTED",
	.preamp         = "Global Preamp:",
	.band_hdr       = "Band",
	.freq_hdr       = "Freq (Hz)",
	.gain_hdr       = "Gain (dB)",
	.q_hdr          = "Q",
	.type_hdr       = "Type",
	.status_hdr     = "Status",
	.dac_filter     = "DAC Digital Filter:",
	.sync_ok        = "All synced with device",
	.sync_pending   = "** MODIFICATIONS NOT APPLIED **",
	.modified_warn  = "Unapplied changes. Press q again to exit.",
	.status_conn    = "STATUS: Connected",
	.status_disconn = "STATUS: NOT connected",
	.preset_label   = "Preset:",
	/* Help */
	.help_nav       = "=== NAVIGATION ===",
	.help_arrows    = "  Arrows        Move between bands/params",
	.help_coarse    = "  +/-           Change value (coarse step)",
	.help_fine      = "  </>           Change value (fine step)",
	.help_toggle    = "  Space         Toggle band on/off",
	.help_cycle     = "  t             Cycle filter type (PK/LSQ/HSQ)",
	.help_dev       = "=== DEVICE ACTIONS ===",
	.help_apply     = "  a             Apply changes to RAM",
	.help_save      = "  s (then S)    Save to flash (permanent)",
	.help_read      = "  r / R         Reload config from device",
	.help_gain      = "  g / G         Set global preamp gain",
	.help_filter    = "  f / F         Cycle DAC digital filter",
	.help_presets   = "=== PRESETS ===",
	.help_psave     = "  p             Save current preset",
	.help_pload     = "  P             Load preset",
	.help_pdel      = "  K             Delete current preset",
	.help_other     = "=== OTHER ===",
	.help_reset_flat= "  d             Reset to flat (0 dB, Q=0.7)",
	.help_reset_def = "  D             Reset to defaults (optimal freqs)",
	.help_quit      = "  q / Q         Quit",
	/* Messages */
	.msg_filter_set = "DAC filter set to: %s",
	.msg_applied    = "OK: Changes applied to RAM.",
	.msg_saved      = "OK: Configuration saved to flash (permanent).",
	.msg_read_ok    = "OK: Configuration reloaded from device.",
	.msg_gain_set   = "Global gain set to %.1f dB.",
	.msg_prompt_gain= "Global gain (%.0f..+%.0f dB) [current: %+.1f]: ",
	.msg_prompt_pname= "Preset name: ",
	.msg_prompt_pload= "Load preset (1-%d): ",
	.msg_confirm_save= "Save to flash? Press S (SHIFT) to confirm: ",
	.msg_confirm_del= "Delete preset '%s'? Press K (SHIFT) to confirm: ",
	.msg_no_presets = "No presets available.",
	.msg_preset_saved= "Preset '%s' saved.",
	.msg_preset_loaded= "Preset '%s' loaded.",
	.msg_preset_deleted= "Preset deleted.",
	.msg_cancelled   = "Cancelled.",
	.msg_no_device   = "ERROR: FiiO JA11 not found.",
	.msg_udev_hint   = "  SUBSYSTEM==\"hidraw\", ATTRS{idVendor}==\"2972\", MODE=\"0660\", GROUP=\"plugdev\"",
};

static const Lang lang_it = {
	.lang_name      = "Italiano",
	.title          = "FiiO JA11 (KT02H20) - Configuratore PEQ Completo",
	.connected      = "CONNESSO:",
	.disconnected   = "DISCONNESSO",
	.preamp         = "Preamp Globale:",
	.band_hdr       = "Banda",
	.freq_hdr       = "Freq (Hz)",
	.gain_hdr       = "Guad. (dB)",
	.q_hdr          = "Q",
	.type_hdr       = "Tipo",
	.status_hdr     = "Stato",
	.dac_filter     = "Filtro DAC Digitale:",
	.sync_ok        = "Sincronizzato con il dispositivo",
	.sync_pending   = "** MODIFICHE NON APPLICATE **",
	.modified_warn  = "Modifiche non applicate. Premi q di nuovo per uscire.",
	.status_conn    = "STATO: Connesso",
	.status_disconn = "STATO: NON connesso",
	.preset_label   = "Preset:",
	/* Help */
	.help_nav       = "=== NAVIGAZIONE ===",
	.help_arrows    = "  Freccette     Spostamento tra bande/parametri",
	.help_coarse    = "  +/-           Modifica valore (passo veloce)",
	.help_fine      = "  </>           Modifica valore (passo fine)",
	.help_toggle    = "  Spazio        Abilita/disabilita banda",
	.help_cycle     = "  t             Cicla tipo filtro (PK/LSQ/HSQ)",
	.help_dev       = "=== AZIONI DISPOSITIVO ===",
	.help_apply     = "  a             Applica modifiche alla RAM",
	.help_save      = "  s (poi S)     Salva su flash (permanente)",
	.help_read      = "  r / R         Ricarica config. dal dispositivo",
	.help_gain      = "  g / G         Imposta guadagno globale",
	.help_filter    = "  f / F         Cicla filtro DAC digitale",
	.help_presets   = "=== PRESET ===",
	.help_psave     = "  p             Salva preset corrente",
	.help_pload     = "  P             Carica preset",
	.help_pdel      = "  K             Elimina preset corrente",
	.help_other     = "=== ALTRO ===",
	.help_reset_flat= "  d             Reset a flat (0 dB, Q=0.7)",
	.help_reset_def = "  D             Reset a default (freq ottimali)",
	.help_quit      = "  q / Q         Esci",
	/* Messages */
	.msg_filter_set = "Filtro DAC impostato: %s",
	.msg_applied    = "OK: Modifiche applicate alla RAM.",
	.msg_saved      = "OK: Configurazione salvata su flash (permanente).",
	.msg_read_ok    = "OK: Configurazione ricaricata dal dispositivo.",
	.msg_gain_set   = "Guadagno globale impostato a %.1f dB.",
	.msg_prompt_gain= "Guadagno globale (%.0f..+%.0f dB) [corr: %+.1f]: ",
	.msg_prompt_pname= "Nome preset: ",
	.msg_prompt_pload= "Carica preset (1-%d): ",
	.msg_confirm_save= "Salvare su flash? Premi S (MAIUSC) per confermare: ",
	.msg_confirm_del= "Eliminare preset '%s'? Premi K (MAIUSC) per confermare: ",
	.msg_no_presets = "Nessun preset disponibile.",
	.msg_preset_saved= "Preset '%s' salvato.",
	.msg_preset_loaded= "Preset '%s' caricato.",
	.msg_preset_deleted= "Preset eliminato.",
	.msg_cancelled   = "Annullato.",
	.msg_no_device   = "ERRORE: FiiO JA11 non trovato.",
	.msg_udev_hint   = "  SUBSYSTEM==\"hidraw\", ATTRS{idVendor}==\"2972\", MODE=\"0660\", GROUP=\"plugdev\"",
};

static int g_lang = LANG_EN;
#define LANG_PTR (g_lang == LANG_IT ? &lang_it : &lang_en)
#define LANG (*LANG_PTR)

/* ============================================================
 * Globals
 * ============================================================ */
static Band bands[NUM_BANDS];
static int current_band = 0;
static int current_param = 0;    /* 0:Freq 1:Gain 2:Q 3:Type */
static double global_gain = 0.0;
static bool modified = false;
static bool device_connected = false;
static hid_device *device_handle = NULL;
static int dac_filter = DAC_FILTER_FAST_LL;

static Preset presets[MAX_PRESETS];
static int num_presets = 0;
static int current_preset = -1;

static int device_vid = 0;
static int device_pid = 0;
static char device_name[256] = "";
static char status_msg[256] = "";

/* ============================================================
 * HID Low-Level
 * ============================================================ */
static bool send_feature_report(const unsigned char *data, int len)
{
	unsigned char buf[65];
	if (!device_handle) return false;
	memset(buf, 0, sizeof(buf));
	buf[0] = REPORT_ID_FIIO;
	if (len > 64) len = 64;
	memcpy(&buf[1], data, len);
	return (hid_send_feature_report(device_handle, buf, len + 1) != -1);
}

static int read_input_report(unsigned char *buf, int len, int timeout_ms)
{
	if (!device_handle) return -1;
	return hid_read_timeout(device_handle, buf, len, timeout_ms);
}

/* ============================================================
 * HID Commands
 * ============================================================ */
static bool write_band(int idx)
{
	int g, f, qv;
	unsigned char pkt[] = { SET_HDR1, SET_HDR2, 0, 0,
		CMD_FILTER_PARAMS, FILTER_PARAMS_LEN,
		0, 0,0, 0,0, 0,0, FILTER_PK, 0, FOOTER };
	if (!device_handle || idx < 0 || idx >= NUM_BANDS) return false;
	g = (int)round((bands[idx].enabled ? bands[idx].gain : 0.0) * 10.0);
	if (g < 0) g = 65536 + g;
	f = (int)round(bands[idx].freq);
	qv = (int)round(bands[idx].q * 100.0);
	pkt[6] = idx;
	pkt[7] = (g >> 8) & 0xff;  pkt[8] = g & 0xff;
	pkt[9] = (f >> 8) & 0xff;  pkt[10] = f & 0xff;
	pkt[11] = (qv >> 8) & 0xff; pkt[12] = qv & 0xff;
	pkt[13] = bands[idx].filter_type;
	return send_feature_report(pkt, sizeof(pkt));
}

static bool apply_changes(void)
{
	unsigned char pkt[] = { SET_HDR1, SET_HDR2, 0, 0,
		CMD_APPLY, APPLY_LEN, 1, 0, FOOTER };
	return device_handle ? send_feature_report(pkt, sizeof(pkt)) : false;
}

static bool sync_all_bands(void)
{
	if (!device_handle) return false;
	for (int i = 0; i < NUM_BANDS; i++) {
		if (!write_band(i)) return false;
		usleep(25000);
	}
	usleep(10000);
	return apply_changes();
}

static bool save_to_flash(void)
{
	unsigned char pkt[] = { SET_HDR1, SET_HDR2, 0, 0,
		CMD_SAVE_FLASH, SAVE_FLASH_LEN, 3, 0, FOOTER };
	if (!device_handle) return false;
	if (!sync_all_bands()) return false;
	usleep(50000);
	return send_feature_report(pkt, sizeof(pkt));
}

void set_global_gain_cmd(double gain)
{
	int value;
	unsigned char pkt[] = { SET_HDR1, SET_HDR2, 0, 0,
		CMD_GLOBAL_GAIN, GLOBAL_GAIN_LEN, 0,0, 0, FOOTER };
	if (!device_handle) return;
	if (gain < GLOBAL_GAIN_MIN) gain = GLOBAL_GAIN_MIN;
	if (gain > GLOBAL_GAIN_MAX) gain = GLOBAL_GAIN_MAX;
	value = (int)round(gain * 2560.0);
	if (value < 0) value = 65536 + value;
	pkt[6] = value & 0xff;
	pkt[7] = (value >> 8) & 0xff;
	send_feature_report(pkt, sizeof(pkt));
}

static void set_dac_filter_cmd(int filter_idx)
{
	unsigned char pkt[] = { SET_HDR1, SET_HDR2, 0, 0,
		CMD_DAC_FILTER, DAC_FILTER_LEN, (unsigned char)filter_idx, 0, FOOTER };
	if (!device_handle) return;
	send_feature_report(pkt, sizeof(pkt));
}

static const char *dac_filter_name(int idx)
{
	switch (idx) {
	case DAC_FILTER_FAST_LL: return DAC_FILTER_NAME_FAST_LL;
	case DAC_FILTER_FAST_PC: return DAC_FILTER_NAME_FAST_PC;
	case DAC_FILTER_SLOW_LL: return DAC_FILTER_NAME_SLOW_LL;
	case DAC_FILTER_SLOW_PC: return DAC_FILTER_NAME_SLOW_PC;
	case DAC_FILTER_NON_OS:  return DAC_FILTER_NAME_NON_OS;
	default: return "?";
	}
}

/* ============================================================
 * Read device config
 * ============================================================ */
static bool read_device_config(void)
{
	unsigned char resp[64];
	int ret;
	if (!device_handle) return false;

	/* Read global gain */
	{
		unsigned char cmd[] = { READ_HDR1, READ_HDR2, 0, 0,
			CMD_READ_GAIN, 0, 0, FOOTER };
		if (send_feature_report(cmd, sizeof(cmd))) {
			memset(resp, 0, sizeof(resp));
			ret = read_input_report(resp, sizeof(resp), 500);
			if (ret > 0 && resp[4] == CMD_GLOBAL_GAIN) {
				int raw = (resp[7] << 8) | resp[6];
				if (raw > 32767) raw -= 65536;
				global_gain = (double)raw / 2560.0;
			}
		}
	}
	/* Read DAC filter (from input report) */
	{
		unsigned char cmd[] = { READ_HDR1, READ_HDR2, 0, 0,
			CMD_DAC_FILTER, 0, 0, FOOTER };
		if (send_feature_report(cmd, sizeof(cmd))) {
			memset(resp, 0, sizeof(resp));
			ret = read_input_report(resp, sizeof(resp), 500);
			if (ret > 0 && resp[4] == CMD_DAC_FILTER) {
				int val = resp[6];
				if (val >= 1 && val <= DAC_FILTER_COUNT)
					dac_filter = val;
			}
		}
	}
	/* Read each band */
	for (int i = 0; i < NUM_BANDS; i++) {
		unsigned char cmd[] = { READ_HDR1, READ_HDR2, 0, 0,
			CMD_READ_PARAM, 1, i, FOOTER };
		if (send_feature_report(cmd, sizeof(cmd))) {
			memset(resp, 0, sizeof(resp));
			ret = read_input_report(resp, sizeof(resp), 500);
			if (ret > 0 && resp[4] == 21) {
				int idx = resp[6];
				if (idx >= 0 && idx < NUM_BANDS) {
					int rg = (resp[8] << 8) | resp[7];
					if (rg > 32767) rg -= 65536;
					bands[idx].gain = (double)rg / 10.0;
					bands[idx].freq = (double)((resp[10] << 8) | resp[9]);
					int rq = (resp[12] << 8) | resp[11];
					bands[idx].q = (double)rq / 100.0;
					bands[idx].filter_type = resp[13] & 0x03;
					bands[idx].enabled = true;
				}
			}
		}
	}
	return true;
}

/* ============================================================
 * Device connection
 * ============================================================ */
static bool connect_device(void)
{
	if (hid_init() != 0) return false;
	device_handle = hid_open(FIIO_VID, JA11_PID, NULL);
	if (!device_handle) device_handle = hid_open(JKALLY_VID, JM12_PID, NULL);
	if (!device_handle) {
		struct hid_device_info *devs = hid_enumerate(FIIO_VID, 0);
		for (struct hid_device_info *cur = devs; cur; cur = cur->next) {
			if (cur->product_string &&
			    (wcsstr(cur->product_string, L"JA11") ||
			     wcsstr(cur->product_string, L"ja11"))) {
				device_handle = hid_open_path(cur->path);
				break;
			}
		}
		hid_free_enumeration(devs);
	}
	if (!device_handle) {
		struct hid_device_info *devs = hid_enumerate(JKALLY_VID, 0);
		for (struct hid_device_info *cur = devs; cur; cur = cur->next) {
			if (cur->product_string &&
			    (wcsstr(cur->product_string, L"KT02H20") ||
			     wcsstr(cur->product_string, L"JM12"))) {
				device_handle = hid_open_path(cur->path);
				break;
			}
		}
		hid_free_enumeration(devs);
	}
	if (device_handle) {
		device_connected = true;
		struct hid_device_info *info = hid_get_device_info(device_handle);
		if (info) {
			device_vid = info->vendor_id;
			device_pid = info->product_id;
			if (info->product_string)
				snprintf(device_name, sizeof(device_name), "%ls", info->product_string);
			else
				snprintf(device_name, sizeof(device_name), "JA11 (0x%04x:0x%04x)", device_vid, device_pid);
		} else {
			device_vid = FIIO_VID; device_pid = JA11_PID;
			snprintf(device_name, sizeof(device_name), "JA11 (0x%04x:0x%04x)", device_vid, device_pid);
		}
		read_device_config();
		return true;
	}
	return false;
}

static void disconnect_device(void)
{
	if (device_handle) { hid_close(device_handle); device_handle = NULL; }
	device_connected = false;
	hid_exit();
}

/* ============================================================
 * Preset management
 * ============================================================ */
static void save_current_preset(const char *name)
{
	if (num_presets >= MAX_PRESETS) return;
	Preset *p = &presets[num_presets];
	strncpy(p->name, name, MAX_PRESET_NAME - 1);
	p->name[MAX_PRESET_NAME - 1] = 0;
	memcpy(p->bands, bands, sizeof(bands));
	p->global_gain = global_gain;
	current_preset = num_presets;
	num_presets++;
}

static void load_preset(int idx)
{
	if (idx < 0 || idx >= num_presets) return;
	memcpy(bands, presets[idx].bands, sizeof(bands));
	global_gain = presets[idx].global_gain;
	current_preset = idx;
	modified = true;
}

static void save_presets(void)
{
	FILE *f = fopen(PRESET_FILE, "w");
	if (!f) return;
	fprintf(f, "%d\n", num_presets);
	for (int i = 0; i < num_presets; i++) {
		fprintf(f, "%s\n", presets[i].name);
		fprintf(f, "%.1f\n", presets[i].global_gain);
		for (int j = 0; j < NUM_BANDS; j++)
			fprintf(f, "%d %.0f %.1f %.2f %d\n",
				presets[i].bands[j].enabled ? 1 : 0,
				presets[i].bands[j].freq,
				presets[i].bands[j].gain,
				presets[i].bands[j].q,
				presets[i].bands[j].filter_type);
	}
	fclose(f);
}

static void load_presets(void)
{
	FILE *f = fopen(PRESET_FILE, "r");
	if (!f) return;
	if (fscanf(f, "%d", &num_presets) != 1) { num_presets = 0; fclose(f); return; }
	if (num_presets > MAX_PRESETS) num_presets = MAX_PRESETS;
	for (int i = 0; i < num_presets; i++) {
		fscanf(f, " %63[^\n]", presets[i].name);
		fscanf(f, "%lf", &presets[i].global_gain);
		for (int j = 0; j < NUM_BANDS; j++) {
			int en;
			fscanf(f, "%d %lf %lf %lf %d",
			       &en, &presets[i].bands[j].freq,
			       &presets[i].bands[j].gain,
			       &presets[i].bands[j].q,
			       &presets[i].bands[j].filter_type);
			presets[i].bands[j].enabled = en ? true : false;
		}
	}
	fclose(f);
}

/* ============================================================
 * Band defaults
 * ============================================================ */
static void init_default_bands(void)
{
	static const double default_freqs[NUM_BANDS] = { 32, 64, 125, 250, 500 };
	static const double default_gains[NUM_BANDS] = { 0, 0, 0, 0, 0 };
	static const double default_q[NUM_BANDS] = { 0.7, 0.7, 0.7, 0.7, 0.7 };
	static const int default_types[NUM_BANDS] = { FILTER_PK, FILTER_PK, FILTER_PK, FILTER_PK, FILTER_PK };
	for (int i = 0; i < NUM_BANDS; i++) {
		bands[i].enabled = true;
		bands[i].freq = default_freqs[i];
		bands[i].gain = default_gains[i];
		bands[i].q = default_q[i];
		bands[i].filter_type = default_types[i];
	}
	global_gain = 0.0;
	modified = false;
}

static void reset_flat(void)
{
	for (int i = 0; i < NUM_BANDS; i++) {
		bands[i].enabled = true;
		bands[i].gain = 0.0;
		bands[i].q = 0.7;
		bands[i].filter_type = FILTER_PK;
	}
	global_gain = 0.0;
	modified = true;
}

/* ============================================================
 * Filter type name
 * ============================================================ */
static const char *filter_type_name(int ft)
{
	switch (ft) {
	case FILTER_PK:  return "PK";
	case FILTER_LSQ: return "LSQ";
	case FILTER_HSQ: return "HSQ";
	default:         return "?";
	}
}

/* ============================================================
 * UI Rendering
 * ============================================================ */
static void draw_status_bar(WINDOW *win, int width)
{
	const Lang *l = &LANG;
	wattrset(win, A_REVERSE);
	mvwaddstr(win, 0, 0, " ");
	if (device_connected) {
		wattron(win, COLOR_PAIR(3));
		wprintw(win, " %s %s", l->connected, device_name);
		wattroff(win, COLOR_PAIR(3));
		wprintw(win, "  %s%.1f dB", l->preamp, global_gain);
		wprintw(win, "  %s%s", l->dac_filter, dac_filter_name(dac_filter));
		if (modified) {
			wattron(win, COLOR_PAIR(4));
			wprintw(win, "  %s", l->sync_pending);
			wattroff(win, COLOR_PAIR(4));
		} else {
			wprintw(win, "  %s", l->sync_ok);
		}
	} else {
		wattron(win, COLOR_PAIR(2));
		wprintw(win, " %s", l->disconnected);
		wattroff(win, COLOR_PAIR(2));
	}
	wattrset(win, A_NORMAL);
	whline(win, ' ', width - 1);
}

static void draw_table_headers(WINDOW *win, int width)
{
	const Lang *l = &LANG;
	int col = 2;
	mvwaddstr(win, 0, col, l->band_hdr);  col += 8;
	mvwaddstr(win, 0, col, l->freq_hdr);  col += 14;
	mvwaddstr(win, 0, col, l->gain_hdr);  col += 14;
	mvwaddstr(win, 0, col, l->q_hdr);      col += 14;
	mvwaddstr(win, 0, col, l->type_hdr);   col += 10;
	mvwaddstr(win, 0, col, l->status_hdr);
	mvwhline(win, 1, 0, ' ', width);
}

static void draw_band_row(WINDOW *win, int row, int band_idx, bool selected)
{
	char buf_freq[16], buf_gain[16], buf_q[16];
	char pre = ' ';
	char status[4] = "   ";
	(void)row;
	Band *b = &bands[band_idx];
	int col = 2;

	if (selected) {
		wattrset(win, A_REVERSE);
		pre = '>';
	} else {
		wattrset(win, A_NORMAL);
	}

	if (!b->enabled) {
		wattron(win, COLOR_PAIR(5));
		pre = 'x';
	}

	snprintf(buf_freq, sizeof(buf_freq), "%.0f", b->freq);
	snprintf(buf_gain, sizeof(buf_gain), "%+.1f", b->enabled ? b->gain : 0.0);
	snprintf(buf_q, sizeof(buf_q), "%.2f", b->enabled ? b->q : 0.7);
	strcpy(status, b->enabled ? "ON" : "OFF");

	mvwaddch(win, row, 0, pre);
	mvwaddstr(win, row, col, buf_freq);  col += 14;
	mvwaddstr(win, row, col, buf_gain);  col += 14;
	mvwaddstr(win, row, col, buf_q);      col += 14;
	mvwaddstr(win, row, col, filter_type_name(b->filter_type)); col += 10;
	wattron(win, b->enabled ? COLOR_PAIR(3) : COLOR_PAIR(5));
	mvwaddstr(win, row, col, status);
	wattroff(win, b->enabled ? COLOR_PAIR(3) : COLOR_PAIR(5));
	wattrset(win, A_NORMAL);
	whline(win, ' ', 80);
}

/* Bar chart for gain visualization */
static void draw_gain_bars(WINDOW *win, int start_row, int max_width)
{
	double max_abs = 15.0;
	int bar_width = (max_width - 10) / NUM_BANDS;
	if (bar_width < 5) bar_width = 5;
	int total_bar_area = bar_width * NUM_BANDS;
	if (total_bar_area > max_width - 10) total_bar_area = max_width - 10;

	int plot_height = 7;
	int plot_y = start_row;

	wattron(win, COLOR_PAIR(6));
	mvwhline(win, plot_y, 1, '=', total_bar_area + 2);
	mvwhline(win, plot_y + plot_height, 1, '=', total_bar_area + 2);
	wattroff(win, COLOR_PAIR(6));

	mvwaddstr(win, plot_y + 1, 1, "+");
	mvwaddstr(win, plot_y + plot_height - 1, 1, "+");

	for (int i = 0; i < NUM_BANDS; i++) {
		int x = 2 + i * bar_width + (bar_width - 3) / 2;
		double g = bands[i].enabled ? bands[i].gain : 0.0;
		int bar_h;
		char ch;
		if (g >= 0) {
			bar_h = (int)round((g / max_abs) * (plot_height - 2));
			if (bar_h > plot_height - 2) bar_h = plot_height - 2;
			ch = ACS_CKBOARD;
		} else {
			bar_h = (int)round((-g / max_abs) * (plot_height - 2));
			if (bar_h > plot_height - 2) bar_h = plot_height - 2;
			ch = ' ';
		}
		int y0 = (plot_height - 1) / 2;
		if (g >= 0) {
			for (int r = 0; r < bar_h; r++)
				mvwaddch(win, plot_y + y0 - r, x, ch);
		} else {
			for (int r = 0; r < bar_h; r++)
				mvwaddch(win, plot_y + y0 + 1 + r, x, ch);
		}
	}
}

static void draw_help(WINDOW *win, int start_row, int max_height)
{
	const Lang *l = &LANG;
	int col = 2;

	struct { const char *text; bool highlight; } lines[] = {
		{l->help_nav,       true},
		{l->help_arrows,    false},
		{l->help_coarse,    false},
		{l->help_fine,      false},
		{l->help_toggle,    false},
		{l->help_cycle,     false},
		{l->help_dev,       true},
		{l->help_apply,     false},
		{l->help_save,      false},
		{l->help_read,      false},
		{l->help_gain,      false},
		{l->help_filter,    false},
		{l->help_presets,   true},
		{l->help_psave,     false},
		{l->help_pload,     false},
		{l->help_pdel,      false},
		{l->help_other,     true},
		{l->help_reset_flat,false},
		{l->help_reset_def, false},
		{l->help_quit,      false},
	};
	int n = sizeof(lines)/sizeof(lines[0]);
	int total_rows = n + 2;

	/* Center the help box vertically if possible */
	int box_y = start_row;
	if (box_y + total_rows < max_height) {
		box_y = start_row + (max_height - start_row - total_rows) / 2;
	}

	mvwhline(win, box_y, 0, ' ', 80);
	wattron(win, A_BOLD);
	mvwaddstr(win, box_y, col, l->lang_name);
	wattroff(win, A_BOLD);
	mvwprintw(win, box_y, col + 20, "FiiO JA11 / KT02H20");
	box_y++;

	for (int i = 0; i < n; i++) {
		if (lines[i].highlight) {
			wattron(win, A_UNDERLINE);
			mvwaddstr(win, box_y, col, lines[i].text);
			wattroff(win, A_UNDERLINE);
		} else {
			mvwaddstr(win, box_y, col, lines[i].text);
		}
		box_y++;
	}
}

/* ============================================================
 * Status message line
 * ============================================================ */
static void set_status(const char *fmt, ...)
{
	va_list args;
	va_start(args, fmt);
	vsnprintf(status_msg, sizeof(status_msg), fmt, args);
	va_end(args);
}

static void draw_status_message(WINDOW *win, int row)
{
	if (status_msg[0]) {
		mvwaddstr(win, row, 2, status_msg);
	}
	status_msg[0] = 0;
}

/* ============================================================
 * Main loop
 * ============================================================ */
static void main_loop(WINDOW *main_win)
{
	const Lang *l = &LANG;
	int height, width;
	int ch;
	(void)height;

	load_presets();
	keypad(main_win, TRUE);
	nodelay(main_win, FALSE);
	curs_set(0);

	WINDOW *table_win = derwin(main_win, NUM_BANDS + 2, 80, 1, 0);
	WINDOW *bar_win   = derwin(main_win, 10, 80, NUM_BANDS + 3, 0);
	WINDOW *help_win  = derwin(main_win, 24, 80, NUM_BANDS + 13, 0);
	WINDOW *status_win= derwin(main_win, 1, 80, 0, 0);
	WINDOW *msg_win   = derwin(main_win, 1, 80, LINES - 1, 0);

	wclear(main_win);

	while (1) {
		getmaxyx(main_win, height, width);

		/* Status bar */
		draw_status_bar(status_win, width);

		/* Headers */
		draw_table_headers(table_win, width);

		/* Band rows */
		for (int i = 0; i < NUM_BANDS; i++)
			draw_band_row(table_win, i + 1, i, (i == current_band));

		/* Bar chart */
		draw_gain_bars(bar_win, 0, width);

		/* Help */
		draw_help(help_win, 0, 24);

		/* Status message */
		draw_status_message(msg_win, 0);

		wnoutrefresh(main_win);
		wnoutrefresh(status_win);
		wnoutrefresh(table_win);
		wnoutrefresh(bar_win);
		wnoutrefresh(help_win);
		wmove(main_win, current_band + 1, 2 + current_param * 14);
		wnoutrefresh(msg_win);
		doupdate();

		ch = wgetch(main_win);

		switch (ch) {
		case 'q':
		case 'Q':
			if (modified) {
				set_status("%s", l->modified_warn);
				continue;
			}
			goto exit_loop;

		case KEY_LEFT:
			if (current_param > 0) current_param--;
			break;
		case KEY_RIGHT:
			if (current_param < 3) current_param++;
			break;
		case KEY_UP:
			if (current_band > 0) current_band--;
			break;
		case KEY_DOWN:
			if (current_band < NUM_BANDS - 1) current_band++;
			break;

		case '+':
		case '=':
		{
			double *val = NULL;
			double coarse = 0;
			switch (current_param) {
			case 0: val = &bands[current_band].freq; coarse = 10.0;  break;
			case 1: val = &bands[current_band].gain; coarse = 1.0;   break;
			case 2: val = &bands[current_band].q;    coarse = 0.1;   break;
			default: break;
			}
			if (val) {
				if (current_param == 0) {
					*val += coarse;
					if (*val > FREQ_MAX) *val = FREQ_MAX;
				} else if (current_param == 1) {
					*val += coarse;
					if (*val > GAIN_MAX) *val = GAIN_MAX;
				} else if (current_param == 2) {
					*val += coarse;
					if (*val > Q_MAX) *val = Q_MAX;
				}
				modified = true;
			}
			break;
		}

		case '-':
		case '_':
		{
			double *val = NULL;
			double coarse = 0;
			switch (current_param) {
			case 0: val = &bands[current_band].freq; coarse = 10.0;  break;
			case 1: val = &bands[current_band].gain; coarse = 1.0;   break;
			case 2: val = &bands[current_band].q;    coarse = 0.1;   break;
			default: break;
			}
			if (val) {
				if (current_param == 0) {
					*val -= coarse;
					if (*val < FREQ_MIN) *val = FREQ_MIN;
				} else if (current_param == 1) {
					*val -= coarse;
					if (*val < GAIN_MIN) *val = GAIN_MIN;
				} else if (current_param == 2) {
					*val -= coarse;
					if (*val < Q_MIN) *val = Q_MIN;
				}
				modified = true;
			}
			break;
		}

		case '>':
		case '.':
		{
			double *val = NULL;
			switch (current_param) {
			case 0: val = &bands[current_band].freq; break;
			case 1: val = &bands[current_band].gain; break;
			case 2: val = &bands[current_band].q;    break;
			default: break;
			}
			if (val) {
				if (current_param == 0) {
					*val += 1.0;
					if (*val > FREQ_MAX) *val = FREQ_MAX;
				} else if (current_param == 1) {
					*val += 0.5;
					if (*val > GAIN_MAX) *val = GAIN_MAX;
				} else if (current_param == 2) {
					*val += 0.01;
					if (*val > Q_MAX) *val = Q_MAX;
				}
				modified = true;
			}
			break;
		}

		case '<':
		case ',':
		{
			double *val = NULL;
			switch (current_param) {
			case 0: val = &bands[current_band].freq; break;
			case 1: val = &bands[current_band].gain; break;
			case 2: val = &bands[current_band].q;    break;
			default: break;
			}
			if (val) {
				if (current_param == 0) {
					*val -= 1.0;
					if (*val < FREQ_MIN) *val = FREQ_MIN;
				} else if (current_param == 1) {
					*val -= 0.5;
					if (*val < GAIN_MIN) *val = GAIN_MIN;
				} else if (current_param == 2) {
					*val -= 0.01;
					if (*val < Q_MIN) *val = Q_MIN;
				}
				modified = true;
			}
			break;
		}

		case ' ':
			bands[current_band].enabled = !bands[current_band].enabled;
			modified = true;
			break;

		case 't':
		case 'T':
			bands[current_band].filter_type = (bands[current_band].filter_type + 1) % 3;
			modified = true;
			break;

		case 'a':
		case 'A':
			if (!device_connected) {
				set_status("%s", l->msg_no_device);
				break;
			}
			if (sync_all_bands()) {
				set_global_gain_cmd(global_gain);
				set_dac_filter_cmd(dac_filter);
				usleep(50000);
				apply_changes();
				modified = false;
				set_status("%s", l->msg_applied);
			} else {
				set_status("ERROR: HID send failed.");
			}
			break;

		case 's':
		{
			int c2;
			char buf[32];
			snprintf(buf, sizeof(buf), "%s", l->msg_confirm_save);
			set_status("%s", buf);
			/* Draw prompt */
			draw_status_message(msg_win, 0);
			wrefresh(msg_win);
			nodelay(main_win, TRUE);
			/* Wait for S */
			int waited = 0;
			while (waited < 500) {
				c2 = wgetch(main_win);
				if (c2 == 'S') break;
				if (c2 == 27 || c2 == 'q' || c2 == 'Q') { waited = 999; break; }
				usleep(10000);
				waited += 10;
			}
			nodelay(main_win, FALSE);
			if (waited >= 500 || c2 != 'S') {
				set_status("%s", l->msg_cancelled);
				break;
			}
			if (!device_connected) {
				set_status("%s", l->msg_no_device);
				break;
			}
			if (save_to_flash()) {
				modified = false;
				set_status("%s", l->msg_saved);
			} else {
				set_status("ERROR: Flash save failed.");
			}
			break;
		}

		case 'r':
			if (!device_connected) {
				set_status("%s", l->msg_no_device);
				break;
			}
			read_device_config();
			modified = false;
			set_status("%s", l->msg_read_ok);
			break;

		case 'R':
			if (!device_connected) {
				set_status("%s", l->msg_no_device);
				break;
			}
			read_device_config();
			modified = false;
			set_status("%s", l->msg_read_ok);
			break;

		case 'g':
		case 'G':
		{
			char input[16];
			char prompt[128];
			snprintf(prompt, sizeof(prompt),
				l->msg_prompt_gain,
				GLOBAL_GAIN_MIN, GLOBAL_GAIN_MAX, global_gain);
			set_status("%s", prompt);
			draw_status_message(msg_win, 0);
			wrefresh(msg_win);

			echo();
			curs_set(1);
			nodelay(main_win, TRUE);
			if (wgetnstr(msg_win, input, sizeof(input) - 1) == ERR)
				input[0] = 0;
			nodelay(main_win, FALSE);
			noecho();
			curs_set(0);

			if (input[0]) {
				double new_gain = atof(input);
				if (new_gain >= GLOBAL_GAIN_MIN && new_gain <= GLOBAL_GAIN_MAX) {
					global_gain = new_gain;
					modified = true;
					set_status(l->msg_gain_set, global_gain);
				} else {
					set_status("ERROR: Range %.0f..+%.0f dB",
						GLOBAL_GAIN_MIN, GLOBAL_GAIN_MAX);
				}
			} else {
				set_status("%s", l->msg_cancelled);
			}
			break;
		}

		case 'f':
		case 'F':
		{
			dac_filter = (dac_filter % DAC_FILTER_COUNT) + 1;
			modified = true;
			set_status(l->msg_filter_set, dac_filter_name(dac_filter));
			if (device_connected) {
				set_dac_filter_cmd(dac_filter);
				usleep(50000);
				apply_changes();
				modified = false;
			}
			break;
		}

		case 'p':
		{
			char pname[64];
			char prompt[80];
			snprintf(prompt, sizeof(prompt), "%s", l->msg_prompt_pname);
			set_status("%s", prompt);
			draw_status_message(msg_win, 0);
			wrefresh(msg_win);

			echo();
			curs_set(1);
			nodelay(main_win, TRUE);
			if (wgetnstr(msg_win, pname, sizeof(pname) - 1) == ERR)
				pname[0] = 0;
			nodelay(main_win, FALSE);
			noecho();
			curs_set(0);

			if (pname[0]) {
				save_current_preset(pname);
				save_presets();
				set_status(l->msg_preset_saved, pname);
			} else {
				set_status("%s", l->msg_cancelled);
			}
			break;
		}

		case 'P':
		{
			char input[8];
			char prompt[80];
			if (num_presets == 0) {
				set_status("%s", l->msg_no_presets);
				break;
			}
			snprintf(prompt, sizeof(prompt),
				l->msg_prompt_pload, num_presets);
			set_status("%s", prompt);
			draw_status_message(msg_win, 0);
			wrefresh(msg_win);

			echo();
			curs_set(1);
			nodelay(main_win, TRUE);
			if (wgetnstr(msg_win, input, sizeof(input) - 1) == ERR)
				input[0] = 0;
			nodelay(main_win, FALSE);
			noecho();
			curs_set(0);

			if (input[0]) {
				int idx = atoi(input) - 1;
				if (idx >= 0 && idx < num_presets) {
					load_preset(idx);
					set_status(l->msg_preset_loaded, presets[idx].name);
				} else {
					set_status("ERROR: Invalid preset number.");
				}
			} else {
				set_status("%s", l->msg_cancelled);
			}
			break;
		}

		case 'K':
		{
			if (current_preset < 0 || current_preset >= num_presets) {
				set_status("%s", l->msg_no_presets);
				break;
			}
			char confirm[64];
			snprintf(confirm, sizeof(confirm),
				l->msg_confirm_del, presets[current_preset].name);
			set_status("%s", confirm);
			draw_status_message(msg_win, 0);
			wrefresh(msg_win);

			nodelay(main_win, TRUE);
			int c2;
			int waited = 0;
			while (waited < 500) {
				c2 = wgetch(main_win);
				if (c2 == 'K') break;
				if (c2 == 27 || c2 == 'q' || c2 == 'Q') { waited = 999; break; }
				usleep(10000);
				waited += 10;
			}
			nodelay(main_win, FALSE);

			if (waited < 500 && c2 == 'K') {
				for (int i = current_preset; i < num_presets - 1; i++)
					presets[i] = presets[i + 1];
				num_presets--;
				current_preset = -1;
				save_presets();
				set_status("%s", l->msg_preset_deleted);
			} else {
				set_status("%s", l->msg_cancelled);
			}
			break;
		}

		case 'd':
			reset_flat();
			set_status("Reset: flat EQ (0 dB, Q=0.7).");
			break;

		case 'D':
			init_default_bands();
			set_status("Reset: default frequencies.");
			break;

		default:
			break;
		}
	}
exit_loop:
	delwin(table_win);
	delwin(bar_win);
	delwin(help_win);
	delwin(status_win);
	delwin(msg_win);
	save_presets();
}

/* ============================================================
 * Entry point
 * ============================================================ */
int main(int argc, char *argv[])
{
	const Lang *l;

	/* Parse command line */
	for (int i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--italian") || !strcmp(argv[i], "-it"))
			g_lang = LANG_IT;
		else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
			printf("Usage: %s [--italian|-it]\n", argv[0]);
			printf("  --italian, -it    UI in Italian (default: English)\n");
			printf("  --help, -h        This help\n");
			return 0;
		}
	}

	l = &LANG;

	/* ncurses init */
	setlocale(LC_ALL, "");
	initscr();
	if (has_colors()) {
		start_color();
		init_pair(1, COLOR_WHITE, COLOR_BLACK);
		init_pair(2, COLOR_RED, COLOR_BLACK);
		init_pair(3, COLOR_GREEN, COLOR_BLACK);
		init_pair(4, COLOR_YELLOW, COLOR_BLACK);
		init_pair(5, COLOR_BLUE, COLOR_BLACK);
		init_pair(6, COLOR_CYAN, COLOR_BLACK);
	}
	cbreak();
	noecho();
	curs_set(0);

	/* Title */
	WINDOW *main_win = newwin(LINES - 1, COLS, 1, 0);
	mvaddstr(0, 2, l->title);
	refresh();

	/* Init defaults */
	init_default_bands();

	/* Connect to device */
	if (!connect_device()) {
		mvaddstr(LINES - 1, 2, l->msg_no_device);
		mvaddstr(LINES - 0, 2, l->msg_udev_hint);
		refresh();
	}

	main_loop(main_win);

	/* Cleanup */
	disconnect_device();
	delwin(main_win);
	endwin();
	return 0;
}
