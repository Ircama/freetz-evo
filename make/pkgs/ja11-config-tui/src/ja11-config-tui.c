/*
 * ja11-config-tui.c - Configuratore TUI completo per FiiO JA11 (KT02H20)
 *
 * Comunica via HID (backend hidraw) con il chip KT02H20 presente
 * nel FiiO JadeAudio JA11 per configurare l'equalizzatore
 * parametrico a 5 bande e tutti i controlli del dispositivo.
 *
 * Basato sul reverse engineering di Audiocular-Aura:
 *   https://github.com/mandy321/Audiocular-Aura
 *
 * Copyright (C) 2026
 * SPDX-License-Identifier: GPL-3.0-or-later
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

#include "ja11-config-tui.h"

/* ============================================================
 * Variabili Globali
 * ============================================================ */
static Band bands[NUM_BANDS];
static int current_band = 0;
static int current_param = 0;   /* 0:Freq 1:Gain 2:Q 3:Tipo */
static double global_gain = 0.0;
static bool modified = false;
static bool device_connected = false;
static hid_device *device_handle = NULL;

static Preset presets[MAX_PRESETS];
static int num_presets = 0;
static int current_preset = -1;

static int device_vid = 0;
static int device_pid = 0;
static char device_name[256] = "";

/* Stato UI */
// static int status_line = 0; unused
static char status_msg[256] = "";

/* ============================================================
 * Funzioni di Comunicazione HID - Low Level
 * ============================================================ */

static bool send_feature_report(const unsigned char *data, int len)
{
	unsigned char buf[65];
	int ret;

	if (!device_handle) return false;

	memset(buf, 0, sizeof(buf));
	buf[0] = REPORT_ID_FIIO;
	if (len > 64) len = 64;
	memcpy(&buf[1], data, len);

	ret = hid_send_feature_report(device_handle, buf, len + 1);
	return (ret != -1);
}

static int read_input_report(unsigned char *buf, int len, int timeout_ms)
{
	if (!device_handle) return -1;
	return hid_read_timeout(device_handle, buf, len, timeout_ms);
}

/* ============================================================
 * HID - Set Commands (host -> device)
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

/* ============================================================
 * HID - Read Commands (device -> host)
 * ============================================================ */

static bool read_device_config(void)
{
	unsigned char resp[64];
	int ret;

	if (!device_handle) return false;

	/* Leggi guadagno globale */
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

	/* Leggi ogni banda */
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
 * Connessione Dispositivo
 * ============================================================ */

static bool connect_device(void)
{
	if (hid_init() != 0) return false;

	device_handle = hid_open(FIIO_VID, JA11_PID, NULL);
	if (!device_handle)
		device_handle = hid_open(JKALLY_VID, JM12_PID, NULL);

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
				snprintf(device_name, sizeof(device_name), "%ls",
					 info->product_string);
			else
				snprintf(device_name, sizeof(device_name),
					 "FiiO JA11 (0x%04x:0x%04x)",
					 device_vid, device_pid);
		} else {
			device_vid = FIIO_VID;
			device_pid = JA11_PID;
			snprintf(device_name, sizeof(device_name),
				 "FiiO JA11 (0x%04x:0x%04x)", device_vid, device_pid);
		}
		read_device_config();
		return true;
	}
	return false;
}

static void disconnect_device(void)
{
	if (device_handle) {
		hid_close(device_handle);
		device_handle = NULL;
	}
	device_connected = false;
	hid_exit();
}

/* ============================================================
 * Preset Management
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

static void save_presets_to_file(void)
{
	FILE *f = fopen(PRESET_FILE, "w");
	if (!f) return;
	fprintf(f, "%d\n", num_presets);
	for (int i = 0; i < num_presets; i++) {
		fprintf(f, "%s\n", presets[i].name);
		fprintf(f, "%.1f\n", presets[i].global_gain);
		for (int j = 0; j < NUM_BANDS; j++) {
			fprintf(f, "%d %.0f %.1f %.2f %d\n",
				presets[i].bands[j].enabled ? 1 : 0,
				presets[i].bands[j].freq,
				presets[i].bands[j].gain,
				presets[i].bands[j].q,
				presets[i].bands[j].filter_type);
		}
	}
	fclose(f);
}

static void load_presets_from_file(void)
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
 * TUI - ncurses
 * ============================================================ */

static void set_status(const char *fmt, ...)
{
	va_list args;
	va_start(args, fmt);
	vsnprintf(status_msg, sizeof(status_msg), fmt, args);
	va_end(args);
}

static void init_ncurses(void)
{
	initscr();
	cbreak();
	noecho();
	keypad(stdscr, TRUE);
	curs_set(0);
	start_color();

	init_pair(1, COLOR_BLACK, COLOR_CYAN);    /* Selezione */
	init_pair(2, COLOR_YELLOW, COLOR_BLACK);  /* Titoli */
	init_pair(3, COLOR_GREEN, COLOR_BLACK);   /* Successo */
	init_pair(4, COLOR_RED, COLOR_BLACK);     /* Errore */
	init_pair(5, COLOR_WHITE, COLOR_BLUE);    /* Intestazione */
	init_pair(6, COLOR_CYAN, COLOR_BLACK);    /* Valori */
	init_pair(7, COLOR_BLACK, COLOR_GREEN);   /* ON */
	init_pair(8, COLOR_BLACK, COLOR_RED);     /* OFF */
}

static const char *ftype_name(int t)
{
	switch (t) {
	case FILTER_PK:  return "PK ";
	case FILTER_LSQ: return "LSQ";
	case FILTER_HSQ: return "HSQ";
	default: return "???";
	}
}

static int get_max_y(void) { return LINES; }

static void draw_ui(void)
{
	int y = 0, x = 2;
	clear();

	/* --- Titolo --- */
	attron(COLOR_PAIR(2) | A_BOLD);
	mvprintw(y++, x, "FiiO JA11 (KT02H20) - Configuratore PEQ Completo");
	attroff(COLOR_PAIR(2) | A_BOLD);
	mvprintw(y++, x, "==================================================");
	y++;

	/* --- Info Device --- */
	if (device_connected) {
		attron(COLOR_PAIR(3));
		mvprintw(y, x, "CONNESSO: %s", device_name);
		attroff(COLOR_PAIR(3));
	} else {
		attron(COLOR_PAIR(4));
		mvprintw(y, x, "DISCONNESSO");
		attroff(COLOR_PAIR(4));
	}
	mvprintw(y, x + 40, "VID: 0x%04x  PID: 0x%04x", device_vid, device_pid);
	y++;

	/* --- Guadagno Globale --- */
	mvprintw(y++, x, "----------------------------------------------");
	mvprintw(y, x, "Preamp Globale: ");
	if (global_gain >= 0)
		mvprintw(y, x + 16, "+%.1f dB", global_gain);
	else
		mvprintw(y, x + 16, "%.1f dB", global_gain);

	/* Barra visuale guadagno globale */
	{
		int bar_x = x + 30;
		int bar_w = 30;
		double norm = (global_gain - GLOBAL_GAIN_MIN) /
			      (GLOBAL_GAIN_MAX - GLOBAL_GAIN_MIN);
		int pos = (int)(norm * bar_w);
		if (pos < 0) pos = 0;
		if (pos > bar_w) pos = bar_w;
		mvaddch(y, bar_x, '[');
		for (int i = 0; i < bar_w; i++) {
			if (i == pos)
				mvaddch(y, bar_x + 1 + i, '#');
			else
				mvaddch(y, bar_x + 1 + i, '-');
		}
		mvaddch(y, bar_x + bar_w + 1, ']');
	}
	y += 2;

	/* --- Tabella Bande --- */
	attron(COLOR_PAIR(5) | A_BOLD);
	mvprintw(y, x,     "Banda");
	mvprintw(y, x + 8, "Frequenza");
	mvprintw(y, x + 22, "Guadagno");
	mvprintw(y, x + 36, "Q");
	mvprintw(y, x + 48, "Tipo");
	mvprintw(y, x + 58, "Stato");
	attroff(COLOR_PAIR(5) | A_BOLD);
	y++;
	mvprintw(y++, x, "----- ---------- -------- ----- ---- -----");

	for (int i = 0; i < NUM_BANDS; i++) {
		bool sel = (i == current_band);

		/* Banda */
		if (sel) attron(COLOR_PAIR(1));
		mvprintw(y, x, "Banda %d", i + 1);
		if (sel) attroff(COLOR_PAIR(1));

		/* Freq */
		if (sel && current_param == 0) attron(COLOR_PAIR(1));
		mvprintw(y, x + 8, "%8.0f Hz", bands[i].freq);
		if (sel && current_param == 0) attroff(COLOR_PAIR(1));

		/* Gain */
		if (sel && current_param == 1) attron(COLOR_PAIR(1));
		mvprintw(y, x + 22, "%+.1f dB", bands[i].gain);
		if (sel && current_param == 1) attroff(COLOR_PAIR(1));

		/* Q */
		if (sel && current_param == 2) attron(COLOR_PAIR(1));
		mvprintw(y, x + 36, "%.2f", bands[i].q);
		if (sel && current_param == 2) attroff(COLOR_PAIR(1));

		/* Tipo */
		if (sel && current_param == 3) attron(COLOR_PAIR(1));
		mvprintw(y, x + 48, "%s", ftype_name(bands[i].filter_type));
		if (sel && current_param == 3) attroff(COLOR_PAIR(1));

		/* Stato */
		if (bands[i].enabled) {
			attron(COLOR_PAIR(7));
			mvprintw(y, x + 58, " ON ");
			attroff(COLOR_PAIR(7));
		} else {
			attron(COLOR_PAIR(8));
			mvprintw(y, x + 58, " OFF");
			attroff(COLOR_PAIR(8));
		}
		y++;
	}
	y++;

	/* --- Stato modifica --- */
	if (modified) {
		attron(COLOR_PAIR(2) | A_BLINK);
		mvprintw(y++, x, "** MODIFICHE NON APPLICATE **");
		attroff(COLOR_PAIR(2) | A_BLINK);
	} else {
		attron(COLOR_PAIR(3));
		mvprintw(y++, x, "Sincronizzato con il dispositivo");
		attroff(COLOR_PAIR(3));
	}
	y++;

	/* --- Presets --- */
	if (num_presets > 0) {
		mvprintw(y++, x, "Preset: ");
		for (int i = 0; i < num_presets && i < 4; i++) {
			if (i == current_preset)
				attron(A_REVERSE);
			mvprintw(y - 1, x + 8 + i * 20, "[%d] %s", i + 1, presets[i].name);
			if (i == current_preset)
				attroff(A_REVERSE);
		}
		y++;
	}

	/* --- Comandi --- */
	int cx = x;
	attron(A_UNDERLINE);
	mvprintw(y++, cx, "=== NAVIGAZIONE ===");
	attroff(A_UNDERLINE);
	mvprintw(y++, cx, "  Freccette    Spostamento bande/parametri");
	mvprintw(y++, cx, "  +/-          Increm./decrem. (passo veloce)");
	mvprintw(y++, cx, "  </>          Increm./decrem. (passo fine)");
	mvprintw(y++, cx, "  Spazio       Abilita/disabilita banda");
	mvprintw(y++, cx, "  t            Cicla tipo filtro (PK/LSQ/HSQ)");

	mvaddstr(y++, cx, " ");
	attron(A_UNDERLINE);
	mvprintw(y++, cx, "=== AZIONI DISPOSITIVO ===");
	attroff(A_UNDERLINE);
	mvprintw(y++, cx, "  a            Applica modifiche alla RAM");
	mvprintw(y++, cx, "  s (poi S)    Salva su flash (permanente)");
	mvprintw(y++, cx, "  r            Ricarica configurazione dal device");
	mvprintw(y++, cx, "  g            Imposta guadagno globale");

	mvaddstr(y++, cx, " ");
	attron(A_UNDERLINE);
	mvprintw(y++, cx, "=== PRESET ===");
	attroff(A_UNDERLINE);
	mvprintw(y++, cx, "  p            Salva preset corrente");
	mvprintw(y++, cx, "  P (MAIUSC)   Carica preset");
	mvprintw(y++, cx, "  K            Elimina preset corrente");

	mvaddstr(y++, cx, " ");
	attron(A_UNDERLINE);
	mvprintw(y++, cx, "=== ALTRO ===");
	attroff(A_UNDERLINE);
	mvprintw(y++, cx, "  d            Reset a flat (0 dB, Q=0.7)");
	mvprintw(y++, cx, "  D (MAIUSC)   Reset a default (freq ottimali)");
	mvprintw(y++, cx, "  q            Esci");

	/* --- Status --- */
	y = get_max_y() - 2;
	attron(COLOR_PAIR(5));
	mvhline(y, 0, ' ', COLS);
	mvprintw(y, x, " %s", status_msg);
	attroff(COLOR_PAIR(5));

	refresh();
}

/* ============================================================
 * Input Handling
 * ============================================================ */

static void prompt_global_gain(void)
{
	echo();
	curs_set(1);
	char input[16] = {0};
	mvprintw(LINES - 2, 2, "Guadagno globale (%.0f..+%.0f dB) [corr: %+.1f]: ",
		 GLOBAL_GAIN_MIN, GLOBAL_GAIN_MAX, global_gain);
	getnstr(input, sizeof(input) - 1);
	if (strlen(input) > 0) {
		double val = atof(input);
		if (val < GLOBAL_GAIN_MIN) val = GLOBAL_GAIN_MIN;
		if (val > GLOBAL_GAIN_MAX) val = GLOBAL_GAIN_MAX;
		global_gain = val;
		set_global_gain_cmd(global_gain);
	}
	noecho();
	curs_set(0);
}

static void prompt_save_preset(void)
{
	echo();
	curs_set(1);
	char input[MAX_PRESET_NAME] = {0};
	mvprintw(LINES - 2, 2, "Nome preset: ");
	getnstr(input, sizeof(input) - 1);
	if (strlen(input) > 0) {
		save_current_preset(input);
		save_presets_to_file();
		set_status("Preset '%s' salvato.", input);
	} else {
		set_status("Salvataggio annullato.");
	}
	noecho();
	curs_set(0);
}

static void prompt_load_preset(void)
{
	if (num_presets == 0) {
		set_status("Nessun preset disponibile.");
		return;
	}
	echo();
	curs_set(1);
	char input[16] = {0};
	mvprintw(LINES - 2, 2, "Carica preset (1-%d): ", num_presets);
	getnstr(input, sizeof(input) - 1);
	if (strlen(input) > 0) {
		int idx = atoi(input) - 1;
		if (idx >= 0 && idx < num_presets) {
			load_preset(idx);
			set_status("Preset '%s' caricato.", presets[idx].name);
		} else {
			set_status("Indice non valido.");
		}
	}
	noecho();
	curs_set(0);
}

static void prompt_delete_preset(void)
{
	if (num_presets == 0 || current_preset < 0) {
		set_status("Nessun preset da eliminare.");
		return;
	}
	mvprintw(LINES - 2, 2, "Eliminare preset '%s'? (MAIUSC per confermare): ",
		 presets[current_preset].name);
	int c = getch();
	if (c == 'R') {
		for (int i = current_preset; i < num_presets - 1; i++)
			presets[i] = presets[i + 1];
		num_presets--;
		current_preset = (num_presets > 0) ? 0 : -1;
		save_presets_to_file();
		set_status("Preset eliminato.");
	} else {
		set_status("Eliminazione annullata.");
	}
}

static void reset_to_flat(void)
{
	for (int i = 0; i < NUM_BANDS; i++) {
		bands[i].enabled = true;
		bands[i].gain = 0.0;
		bands[i].q = 0.7;
		bands[i].filter_type = FILTER_PK;
	}
	global_gain = 0.0;
	modified = true;
	set_status("Reset a flat (0 dB). Applicare con 'a'.");
}

static void reset_to_defaults(void)
{
	const double df[] = { 100.0, 500.0, 1000.0, 2500.0, 10000.0 };
	for (int i = 0; i < NUM_BANDS; i++) {
		bands[i].enabled = true;
		bands[i].freq = df[i];
		bands[i].gain = 0.0;
		bands[i].q = 0.7;
		bands[i].filter_type = FILTER_PK;
	}
	global_gain = 0.0;
	modified = true;
	set_status("Reset a default. Applicare con 'a'.");
}

static void handle_input(void)
{
	int ch = getch();
	double coarse = 1.0, fine = 0.1;

	switch (ch) {
	/* Navigazione */
	case KEY_UP:
		current_band = (current_band - 1 + NUM_BANDS) % NUM_BANDS;
		break;
	case KEY_DOWN:
		current_band = (current_band + 1) % NUM_BANDS;
		break;
	case KEY_LEFT:
		current_param = (current_param - 1 + 4) % 4;
		break;
	case KEY_RIGHT:
		current_param = (current_param + 1) % 4;
		break;

	/* Modifica passo veloce */
	case '+': case '=':
		if (current_param == 0) {
			double s = (bands[current_band].freq > 1000) ? 100.0 : 10.0;
			bands[current_band].freq += s;
			if (bands[current_band].freq > FREQ_MAX) bands[current_band].freq = FREQ_MAX;
		} else if (current_param == 1) {
			bands[current_band].gain += coarse;
			if (bands[current_band].gain > GAIN_MAX) bands[current_band].gain = GAIN_MAX;
		} else if (current_param == 2) {
			bands[current_band].q += coarse;
			if (bands[current_band].q > Q_MAX) bands[current_band].q = Q_MAX;
		}
		modified = true;
		break;
	case '-': case '_':
		if (current_param == 0) {
			double s = (bands[current_band].freq > 1000) ? 100.0 : 10.0;
			bands[current_band].freq -= s;
			if (bands[current_band].freq < FREQ_MIN) bands[current_band].freq = FREQ_MIN;
		} else if (current_param == 1) {
			bands[current_band].gain -= coarse;
			if (bands[current_band].gain < GAIN_MIN) bands[current_band].gain = GAIN_MIN;
		} else if (current_param == 2) {
			bands[current_band].q -= coarse;
			if (bands[current_band].q < Q_MIN) bands[current_band].q = Q_MIN;
		}
		modified = true;
		break;

	/* Modifica passo fine */
	case '<': case ',':
		if (current_param == 0) {
			double s = (bands[current_band].freq > 1000) ? 10.0 : 1.0;
			bands[current_band].freq -= s;
			if (bands[current_band].freq < FREQ_MIN) bands[current_band].freq = FREQ_MIN;
		} else if (current_param == 1) {
			bands[current_band].gain -= fine;
			if (bands[current_band].gain < GAIN_MIN) bands[current_band].gain = GAIN_MIN;
		} else if (current_param == 2) {
			bands[current_band].q -= fine;
			if (bands[current_band].q < Q_MIN) bands[current_band].q = Q_MIN;
		}
		modified = true;
		break;
	case '>': case '.':
		if (current_param == 0) {
			double s = (bands[current_band].freq > 1000) ? 10.0 : 1.0;
			bands[current_band].freq += s;
			if (bands[current_band].freq > FREQ_MAX) bands[current_band].freq = FREQ_MAX;
		} else if (current_param == 1) {
			bands[current_band].gain += fine;
			if (bands[current_band].gain > GAIN_MAX) bands[current_band].gain = GAIN_MAX;
		} else if (current_param == 2) {
			bands[current_band].q += fine;
			if (bands[current_band].q > Q_MAX) bands[current_band].q = Q_MAX;
		}
		modified = true;
		break;

	/* Toggle banda */
	case ' ':
		bands[current_band].enabled = !bands[current_band].enabled;
		modified = true;
		break;

	/* Cicla tipo filtro */
	case 't': case 'T':
		bands[current_band].filter_type = (bands[current_band].filter_type + 1) % 3;
		modified = true;
		break;

	/* Azioni dispositivo */
	case 'a': case 'A':
		if (sync_all_bands()) {
			modified = false;
			set_status("OK: Modifiche applicate alla RAM.");
		} else {
			set_status("ERRORE: Impossibile applicare modifiche.");
		}
		break;

	case 's': {
		mvprintw(LINES - 2, 2, "Salvare su flash? Premi S (MAIUSC) per confermare: ");
		int c2 = getch();
		if (c2 == 'S') {
			if (save_to_flash()) {
				modified = false;
				set_status("OK: Configurazione salvata su flash (permanente).");
			} else {
				set_status("ERRORE: Salvataggio su flash fallito.");
			}
		} else {
			set_status("Salvataggio annullato.");
		}
		break;
	}

	case 'r': case 'R':        /* read config */
		if (read_device_config()) {
			modified = false;
			set_status("OK: Configurazione ricaricata dal dispositivo.");
		} else {
			set_status("ERRORE: Lettura configurazione fallita.");
		}
		break;

	case 'g': case 'G':
		prompt_global_gain();
		set_status("Guadagno globale impostato a %.1f dB.", global_gain);
		break;

	/* Preset */
	case 'p':
		prompt_save_preset();
		break;

	case 'P':
		prompt_load_preset();
		break;

	case 'K':       /* delete preset */
		prompt_delete_preset();
		break;

	/* Reset */
	case 'd':
		reset_to_flat();
		break;
	case 'D':
		reset_to_defaults();
		break;

	/* Esci */
	case 'q': case 'Q':
		if (modified) {
			mvprintw(LINES - 2, 2, "Modifiche non applicate. Premi q di nuovo per uscire. ");
			int c2 = getch();
			if (c2 != 'q' && c2 != 'Q') break;
		}
		endwin();
		disconnect_device();
                break;
        }
}
/* ============================================================
 * Main
 * ============================================================ */

static void init_default_bands(void)
{
    const double df[] = { 100.0, 500.0, 1000.0, 2500.0, 10000.0 };
    for (int i = 0; i < NUM_BANDS; i++) {
        bands[i].enabled = true;
        bands[i].freq = df[i];
        bands[i].gain = 0.0;
        bands[i].q = 0.7;
        bands[i].filter_type = FILTER_PK;
    }
}

int main(void)
{

    init_default_bands();
	/* Carica preset salvati */
	load_presets_from_file();

	/* Connessione */
	if (!connect_device()) {
		fprintf(stderr, "ERRORE: FiiO JA11 non trovato.\n");
		fprintf(stderr, "Verifica che sia connesso (VID 0x%04x PID 0x%04x).\n",
			FIIO_VID, JA11_PID);
		fprintf(stderr, "Potrebbe essere necessario un driver udev:\n");
		fprintf(stderr, "  SUBSYSTEM==\"hidraw\", ATTRS{idVendor}==\"2972\", MODE=\"0660\", GROUP=\"plugdev\"\n");
		return 1;
	}

	init_ncurses();
	set_status("Connesso a %s. Premi 'a' per applicare le modifiche.", device_name);

	while (1) {
		draw_ui();
		handle_input();
	}

	return 0;
}
