#ifndef JA11_CONFIG_TUI_H
#define JA11_CONFIG_TUI_H

#include <stdbool.h>
#include <stdint.h>

/*
 * Costanti del protocollo FiiO JA11 (KT02H20)
 * Basato sul reverse engineering di Audiocular-Aura
 * https://github.com/mandy321/Audiocular-Aura
 *
 * Protocollo raw HID:
 *   - Report ID: 0x02 (feature report)
 *   - Set command header: 0xaa 0x0a 0x00 0x00
 *   - Read command header: 0xbb 0x0b 0x00 0x00
 *   - Footer: 0xee
 *   - Guadagno: fixed-point Q12 (valore * 10) in 2 byte big-endian
 *     (se negativo: complemento a 16 bit: 65536 + valore)
 *   - Guadagno globale: fixed-point Q? (valore * 2560) in 2 byte LE
 *   - Frequenza: Hz in 2 byte big-endian
 *   - Q: valore * 100 in 2 byte big-endian
 */

/* --- VID/PID --- */
#define FIIO_VID       0x2972  /* FiiO */
#define JA11_PID       0x0102  /* FiiO JadeAudio JA11 (258) */
#define JKALLY_VID     0x31b2  /* JKALLY / KT Micro */
#define JM12_PID       0x0111  /* JKALLY JM12 / KT02H20 */

/* --- Report ID --- */
#define REPORT_ID_FIIO 0x02

/* --- Intestazione e chiusura dei pacchetti --- */
#define SET_HDR1      0xaa
#define SET_HDR2      0x0a
#define READ_HDR1     0xbb
#define READ_HDR2     0x0b
#define FOOTER        0xee

/* --- Comandi set --- */
#define CMD_FILTER_PARAMS 21  /* 0x15 — Scrittura parametri filtro (banda) */
#define CMD_GLOBAL_GAIN   23  /* 0x17 — Lettura/scrittura guadagno globale */
#define CMD_APPLY         24  /* 0x18 — Applica modifiche (commit in RAM) */
#define CMD_SAVE_FLASH    25  /* 0x19 — Salvataggio permanente su flash */
#define CMD_READ_PARAM    21  /* 0x15 — Lettura parametri (sub: 1=banda, 0=?) */
#define CMD_READ_GAIN     23  /* 0x17 — Lettura guadagno (sub: 0) */

/* --- Valori payload comandi --- */
#define FILTER_PARAMS_LEN   8
#define GLOBAL_GAIN_LEN     2
#define APPLY_LEN           1
#define SAVE_FLASH_LEN      1

/* --- Tipi di filtro --- */
#define FILTER_PK   0  /* Peaking */
#define FILTER_LSQ  1  /* Low Shelf */
#define FILTER_HSQ  2  /* High Shelf */

/* --- Limiti --- */
#define NUM_BANDS        5
#define DEFAULT_SAMPLE_RATE 48000.0

#define FREQ_MIN     20.0
#define FREQ_MAX  20000.0
#define GAIN_MIN   -24.0
#define GAIN_MAX    12.0
#define Q_MIN        0.1
#define Q_MAX       10.0
#define GLOBAL_GAIN_MIN  -12.0
#define GLOBAL_GAIN_MAX   12.0

/* --- Frequenze e Q di default per JA11 --- */
#define DEFAULT_FREQ_0   100.0
#define DEFAULT_FREQ_1   500.0
#define DEFAULT_FREQ_2  1000.0
#define DEFAULT_FREQ_3  2500.0
#define DEFAULT_FREQ_4 10000.0
#define DEFAULT_Q        0.7

/* --- Dimensioni massime per preset --- */
#define MAX_PRESET_NAME 64
#define MAX_PRESETS     16
#define PRESET_FILE     "/tmp/ja11-presets.conf"

/* --- Strutture Dati --- */

typedef struct {
	bool enabled;
	double freq;        /* Hz */
	double gain;        /* dB */
	double q;           /* fattore Q */
	int filter_type;    /* FILTER_PK, FILTER_LSQ, FILTER_HSQ */
} Band;

typedef struct {
	char name[MAX_PRESET_NAME];
	Band bands[NUM_BANDS];
	double global_gain;
} Preset;

#endif /* JA11_CONFIG_TUI_H */
