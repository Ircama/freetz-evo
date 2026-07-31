#ifndef JA11_CONFIG_TUI_H
#define JA11_CONFIG_TUI_H

#include <stdbool.h>
#include <stdint.h>

/*
 * Protocol constants for FiiO JA11 (KT02H20)
 * Based on reverse engineering from Audiocular-Aura:
 *   https://github.com/mandy321/Audiocular-Aura
 *
 * Raw HID protocol:
 *   - Report ID: 0x02 (output report - like Audiocular-Aura sendReport)
 *   - Set header: 0xaa 0x0a 0x00 0x00  <cmd> <len> [data...] 0xee
 *   - Read header: 0xbb 0x0b 0x00 0x00  <cmd> <sub> [data...] 0xee
 *   - Gain: fixed-point Q12 (value * 10) in 2 bytes big-endian
 *     (if negative: 16-bit complement: 65536 + value)
 *   - Global gain: value * 2560 in 2 bytes little-endian
 *   - Frequency: Hz in 2 bytes big-endian
 *   - Q: value * 100 in 2 bytes big-endian
 */

/* --- VID/PID --- */
#define FIIO_VID       0x2972
#define JA11_PID       0x0102  /* 258 */
#define JKALLY_VID     0x31b2
#define JM12_PID       0x0111

/* --- Report ID --- */
#define REPORT_ID_FIIO 0x02

/* --- Packet markers --- */
#define SET_HDR1      0xaa
#define SET_HDR2      0x0a
#define READ_HDR1     0xbb
#define READ_HDR2     0x0b
#define FOOTER        0xee

/* --- Commands --- */
#define CMD_FILTER_PARAMS 21  /* 0x15 - write band PEQ */
#define CMD_GLOBAL_GAIN   23  /* 0x17 - read/write global gain */
#define CMD_APPLY         24  /* 0x18 - commit to RAM */
#define CMD_SAVE_FLASH    25  /* 0x19 - save to flash permanently */
#define CMD_READ_PARAM    21  /* 0x15 - read params (sub: 1=band) */
#define CMD_READ_GAIN     23  /* 0x17 - read gain (sub: 0) */
#define CMD_DAC_FILTER    17  /* 0x11 - DAC digital filter (Savitech cmd, adapted for JA11) */
#define CMD_AMP_MODE      29  /* 0x1D - amplifier mode (Class H/AB) */
#define CMD_GAIN_MODE     25  /* 0x19 - gain mode (Low/High) - same as save? */

/* --- Payload lengths --- */
#define FILTER_PARAMS_LEN   8
#define GLOBAL_GAIN_LEN     2
#define APPLY_LEN           1
#define SAVE_FLASH_LEN      1
#define DAC_FILTER_LEN      1
#define AMP_MODE_LEN        1

/* --- Filter types (PEQ) --- */
#define FILTER_PK   0
#define FILTER_LSQ  1
#define FILTER_HSQ  2

/* --- DAC digital filter presets --- */
#define DAC_FILTER_FAST_LL  1  /* Fast roll-off, linear phase (low latency) */
#define DAC_FILTER_FAST_PC  2  /* Fast roll-off, phase compensation */
#define DAC_FILTER_SLOW_LL  3  /* Slow roll-off, linear phase (low latency) */
#define DAC_FILTER_SLOW_PC  4  /* Slow roll-off, phase compensation */
#define DAC_FILTER_NON_OS   5  /* Non-oversampling (NOS) */
#define DAC_FILTER_COUNT    5

/* --- DAC filter names --- */
#define DAC_FILTER_NAME_FAST_LL "FAST-LL"
#define DAC_FILTER_NAME_FAST_PC "FAST-PC"
#define DAC_FILTER_NAME_SLOW_LL "Slow-LL"
#define DAC_FILTER_NAME_SLOW_PC "Slow-PC"
#define DAC_FILTER_NAME_NON_OS  "NON-OS "

/* --- Limits --- */
#define NUM_BANDS        5
#define FREQ_MIN     20.0
#define FREQ_MAX  20000.0
#define GAIN_MIN   -24.0
#define GAIN_MAX    12.0
#define Q_MIN        0.1
#define Q_MAX       10.0
#define GLOBAL_GAIN_MIN  -12.0
#define GLOBAL_GAIN_MAX   12.0
#define BALANCE_MIN  -15
#define BALANCE_MAX   15

/* --- Default frequencies for JA11 --- */
#define DEFAULT_FREQ_0   100.0
#define DEFAULT_FREQ_1   500.0
#define DEFAULT_FREQ_2  1000.0
#define DEFAULT_FREQ_3  2500.0
#define DEFAULT_FREQ_4 10000.0
#define DEFAULT_Q        0.7

/* --- Presets --- */
#define MAX_PRESET_NAME 64
#define MAX_PRESETS     16
#define PRESET_FILE     "/tmp/ja11-presets.conf"

/* --- i18n language codes --- */
#define LANG_EN 0
#define LANG_IT 1

/* --- Data structures --- */

typedef struct {
	bool enabled;
	double freq;        /* Hz */
	double gain;        /* dB */
	double q;
	int filter_type;    /* FILTER_PK, FILTER_LSQ, FILTER_HSQ */
} Band;

typedef struct {
	char name[MAX_PRESET_NAME];
	Band bands[NUM_BANDS];
	double global_gain;
} Preset;

#endif /* JA11_CONFIG_TUI_H */
