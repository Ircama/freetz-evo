/*
 * ja11-config-tui.c - Full-featured TUI configurator for FiiO JA11 (KT02H20)
 *
 * Communicates via HID with the KT02H20 chip inside
 * the FiiO JadeAudio JA11 to configure the 5-band parametric EQ,
 * DAC digital filters, global gain, and more.
 *
 * Inspired from Audiocular-Aura: https://github.com/mandy321/Audiocular-Aura
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
	const char *help_tab;
	const char *help_edit;
	const char *help_log;
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
	/* Numeric editor popup: key names and action words of the two hint
	 * lines (key names are drawn in a different color than the actions) */
	const char *edit_hint_key[4];
	const char *edit_hint_val[4];
	const char *edit_title_freq;
	const char *edit_title_gain;
	const char *edit_title_q;
	const char *edit_title_ggain;
	/* Preset list screen */
	const char *preset_list_title;
	const char *preset_file_label;
	const char *preset_footer_load;
	const char *preset_footer_save;
	const char *preset_no_presets;
	/* Device selection screen */
	const char *dev_sel_title;
	const char *dev_sel_hint;
	const char *help_connect;
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
	.help_tab       = "  Tab/Shift-Tab Move fwd/back across all cells",
	.help_edit      = "  e             Edit value numerically (popup)",
	.help_log       = "  l             Show HID traffic log",
	.help_dev       = "=== DEVICE ACTIONS ===",
	.help_apply     = "  a             Apply changes to RAM",
	.help_save      = "  s (then S)    Save to flash (permanent)",
	.help_read      = "  r / R         Reload config from device",
	.help_gain      = "  g / G         Set global preamp gain",
	.help_filter    = "  f / F         Cycle DAC digital filter",
	.help_connect   = "  c             Connect / switch HID device",
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
	.msg_no_device   = "ERROR: device not accessible.",
	.msg_udev_hint   = "  No HID device found. Check USB (lsusb: 2972:0102 / 31b2:0111).",
	.edit_hint_key   = { "Enter", "Esc", "Left/Right", "Backspace" },
	.edit_hint_val   = { "ok", "cancel", "move", "delete" },
	.edit_title_freq = "Band %d: Frequency (Hz)",
	.edit_title_gain = "Band %d: Gain (dB)",
	.edit_title_q    = "Band %d: Q",
	.edit_title_ggain= "Global gain (dB)",
	.preset_list_title = "Presets",
	.preset_file_label = "File: %s",
	.preset_footer_load = "Enter: load    q: close",
	.preset_footer_save = "Enter: continue    q: close",
	.preset_no_presets  = "(no presets)",
	.dev_sel_title   = "Select HID device",
	.dev_sel_hint    = "Up/Down: move    Enter: connect    q: quit",
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
	.help_arrows    = "  Cursore       Spostamento tra bande/parametri",
	.help_coarse    = "  +/-           Modifica valore (passo veloce)",
	.help_fine      = "  </>           Modifica valore (passo fine)",
	.help_toggle    = "  Spazio        Abilita/disabilita banda",
	.help_cycle     = "  t             Cicla tipo filtro (PK/LSQ/HSQ)",
	.help_tab       = "  Tab/Maiusc-Tab  Sposta avanti/indietro tra le celle",
	.help_edit      = "  e             Modifica valore con popup numerico",
	.help_log       = "  l             Mostra log traffico HID",
	.help_dev       = "=== AZIONI DISPOSITIVO ===",
	.help_apply     = "  a             Applica modifiche alla RAM",
	.help_save      = "  s (poi S)     Salva su flash (permanente)",
	.help_read      = "  r / R         Ricarica config. dal dispositivo",
	.help_gain      = "  g / G         Imposta guadagno globale",
	.help_filter    = "  f / F         Cicla filtro DAC digitale",
	.help_connect   = "  c             Connetti / cambia dispositivo HID",
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
	.msg_no_device   = "ERRORE: dispositivo non accessibile.",
	.msg_udev_hint   = "  Nessun dispositivo HID trovato. Controlla USB (lsusb: 2972:0102 / 31b2:0111).",
	.edit_hint_key   = { "Invio", "Esc", "Sin/Dx", "Backspace" },
	.edit_hint_val   = { "ok", "annulla", "sposta", "cancella" },
	.edit_title_freq = "Banda %d: Frequenza (Hz)",
	.edit_title_gain = "Banda %d: Guadagno (dB)",
	.edit_title_q    = "Banda %d: Q",
	.edit_title_ggain= "Guadagno globale (dB)",
	.preset_list_title = "Preset",
	.preset_file_label = "File: %s",
	.preset_footer_load = "Invio: carica    q: chiudi",
	.preset_footer_save = "Invio: continua    q: chiudi",
	.preset_no_presets  = "(nessun preset)",
	.dev_sel_title   = "Seleziona dispositivo HID",
	.dev_sel_hint    = "Su/Giù: sposta    Invio: connetti    q: esci",
};

static const Lang lang_fr = {
	.lang_name      = "Français",
	.title          = "FiiO JA11 (KT02H20) - Configurateur PEQ Complet",
	.connected      = "CONNECTÉ :",
	.disconnected   = "DÉCONNECTÉ",
	.preamp         = "Préamp Global :",
	.band_hdr       = "Bande",
	.freq_hdr       = "Freq (Hz)",
	.gain_hdr       = "Gain (dB)",
	.q_hdr          = "Q",
	.type_hdr       = "Type",
	.status_hdr     = "État",
	.dac_filter     = "Filtre DAC Numérique :",
	.sync_ok        = "Synchronisé avec l'appareil",
	.sync_pending   = "** MODIFICATIONS NON APPLIQUÉES **",
	.modified_warn  = "Modifications non appliquées. Appuyez à nouveau sur q pour quitter.",
	.status_conn    = "ÉTAT : Connecté",
	.status_disconn = "ÉTAT : NON connecté",
	.preset_label   = "Preset :",
	/* Help */
	.help_nav       = "=== NAVIGATION ===",
	.help_arrows    = "  Flèches       Déplacer entre bandes/paramètres",
	.help_coarse    = "  +/-           Modifier la valeur (pas large)",
	.help_fine      = "  </>           Modifier la valeur (pas fin)",
	.help_toggle    = "  Espace        Activer/désactiver la bande",
	.help_cycle     = "  t             Changer le type de filtre (PK/LSQ/HSQ)",
	.help_tab       = "  Tab/Maj-Tab   Avancer/reculer entre les cellules",
	.help_edit      = "  e             Modifier la valeur numériquement (popup)",
	.help_log       = "  l             Afficher le journal HID",
	.help_dev       = "=== ACTIONS APPAREIL ===",
	.help_apply     = "  a             Appliquer les modifications à la RAM",
	.help_save      = "  s (puis S)    Sauvegarder en flash (permanent)",
	.help_read      = "  r / R         Recharger la config. depuis l'appareil",
	.help_gain      = "  g / G         Définir le gain préamp global",
	.help_filter    = "  f / F         Changer le filtre DAC numérique",
	.help_connect   = "  c             Connecter / changer d'appareil HID",
	.help_presets   = "=== PRESETS ===",
	.help_psave     = "  p             Sauvegarder le preset courant",
	.help_pload     = "  P             Charger un preset",
	.help_pdel      = "  K             Supprimer le preset courant",
	.help_other     = "=== AUTRE ===",
	.help_reset_flat= "  d             Réinitialiser à plat (0 dB, Q=0.7)",
	.help_reset_def = "  D             Réinitialiser aux défauts (freq optimales)",
	.help_quit      = "  q / Q         Quitter",
	/* Messages */
	.msg_filter_set = "Filtre DAC défini sur : %s",
	.msg_applied    = "OK : Modifications appliquées à la RAM.",
	.msg_saved      = "OK : Configuration sauvegardée en flash (permanente).",
	.msg_read_ok    = "OK : Configuration rechargée depuis l'appareil.",
	.msg_gain_set   = "Gain global défini sur %.1f dB.",
	.msg_prompt_gain= "Gain global (%.0f..+%.0f dB) [actuel : %+.1f] : ",
	.msg_prompt_pname= "Nom du preset : ",
	.msg_prompt_pload= "Charger le preset (1-%d) : ",
	.msg_confirm_save= "Sauvegarder en flash ? Appuyez sur S (MAJ) pour confirmer : ",
	.msg_confirm_del= "Supprimer le preset '%s' ? Appuyez sur K (MAJ) pour confirmer : ",
	.msg_no_presets = "Aucun preset disponible.",
	.msg_preset_saved= "Preset '%s' sauvegardé.",
	.msg_preset_loaded= "Preset '%s' chargé.",
	.msg_preset_deleted= "Preset supprimé.",
	.msg_cancelled   = "Annulé.",
	.msg_no_device   = "ERREUR : appareil inaccessible.",
	.msg_udev_hint   = "  Aucun appareil HID trouvé. Vérifiez USB (lsusb: 2972:0102 / 31b2:0111).",
	.edit_hint_key   = { "Entrée", "Échap", "Gauche/Droite", "Retour" },
	.edit_hint_val   = { "ok", "annuler", "déplacer", "supprimer" },
	.edit_title_freq = "Bande %d : Fréquence (Hz)",
	.edit_title_gain = "Bande %d : Gain (dB)",
	.edit_title_q    = "Bande %d : Q",
	.edit_title_ggain= "Gain global (dB)",
	.preset_list_title = "Presets",
	.preset_file_label = "Fichier : %s",
	.preset_footer_load = "Entrée : charger    q : fermer",
	.preset_footer_save = "Entrée : continuer    q : fermer",
	.preset_no_presets  = "(aucun preset)",
	.dev_sel_title   = "Sélectionner l'appareil HID",
	.dev_sel_hint    = "Haut/Bas : déplacer    Entrée : connecter    q : quitter",
};

static const Lang lang_de = {
	.lang_name      = "Deutsch",
	.title          = "FiiO JA11 (KT02H20) - Vollständiger PEQ-Konfigurator",
	.connected      = "VERBUNDEN:",
	.disconnected   = "GETRENNT",
	.preamp         = "Globaler Vorverstärker:",
	.band_hdr       = "Band",
	.freq_hdr       = "Freq (Hz)",
	.gain_hdr       = "Gain (dB)",
	.q_hdr          = "Q",
	.type_hdr       = "Typ",
	.status_hdr     = "Status",
	.dac_filter     = "DAC-Digitalfilter:",
	.sync_ok        = "Mit Gerät synchronisiert",
	.sync_pending   = "** ÄNDERUNGEN NICHT ANGEWENDET **",
	.modified_warn  = "Nicht angewendete Änderungen. Zum Beenden erneut q drücken.",
	.status_conn    = "STATUS: Verbunden",
	.status_disconn = "STATUS: NICHT verbunden",
	.preset_label   = "Preset:",
	/* Help */
	.help_nav       = "=== NAVIGATION ===",
	.help_arrows    = "  Pfeile        Zwischen Bändern/Parametern bewegen",
	.help_coarse    = "  +/-           Wert ändern (großer Schritt)",
	.help_fine      = "  </>           Wert ändern (feiner Schritt)",
	.help_toggle    = "  Leertaste     Band ein/aus",
	.help_cycle     = "  t             Filtertyp wechseln (PK/LSQ/HSQ)",
	.help_tab       = "  Tab/Umsch-Tab Vor/zurück zwischen allen Zellen",
	.help_edit      = "  e             Wert numerisch bearbeiten (Popup)",
	.help_log       = "  l             HID-Verlauf anzeigen",
	.help_dev       = "=== GERÄTEAKTIONEN ===",
	.help_apply     = "  a             Änderungen im RAM anwenden",
	.help_save      = "  s (dann S)    In Flash speichern (permanent)",
	.help_read      = "  r / R         Konfiguration vom Gerät laden",
	.help_gain      = "  g / G         Globalen Vorverstärker-Gain setzen",
	.help_filter    = "  f / F         DAC-Digitalfilter wechseln",
	.help_connect   = "  c             Verbinden / HID-Gerät wechseln",
	.help_presets   = "=== PRESETS ===",
	.help_psave     = "  p             Aktuelles Preset speichern",
	.help_pload     = "  P             Preset laden",
	.help_pdel      = "  K             Aktuelles Preset löschen",
	.help_other     = "=== SONSTIGES ===",
	.help_reset_flat= "  d             Auf flach zurücksetzen (0 dB, Q=0.7)",
	.help_reset_def = "  D             Auf Standard zurücksetzen (optimale Freq)",
	.help_quit      = "  q / Q         Beenden",
	/* Messages */
	.msg_filter_set = "DAC-Filter gesetzt auf: %s",
	.msg_applied    = "OK: Änderungen im RAM angewendet.",
	.msg_saved      = "OK: Konfiguration im Flash gespeichert (permanent).",
	.msg_read_ok    = "OK: Konfiguration vom Gerät geladen.",
	.msg_gain_set   = "Globaler Gain auf %.1f dB gesetzt.",
	.msg_prompt_gain= "Globaler Gain (%.0f..+%.0f dB) [aktuell: %+.1f]: ",
	.msg_prompt_pname= "Presetname: ",
	.msg_prompt_pload= "Preset laden (1-%d): ",
	.msg_confirm_save= "In Flash speichern? Zum Bestätigen S (UMSCHALT) drücken: ",
	.msg_confirm_del= "Preset '%s' löschen? Zum Bestätigen K (UMSCHALT) drücken: ",
	.msg_no_presets = "Keine Presets verfügbar.",
	.msg_preset_saved= "Preset '%s' gespeichert.",
	.msg_preset_loaded= "Preset '%s' geladen.",
	.msg_preset_deleted= "Preset gelöscht.",
	.msg_cancelled   = "Abgebrochen.",
	.msg_no_device   = "FEHLER: Gerät nicht zugänglich.",
	.msg_udev_hint   = "  Kein HID-Gerät gefunden. USB prüfen (lsusb: 2972:0102 / 31b2:0111).",
	.edit_hint_key   = { "Enter", "Esc", "Links/Rechts", "Rücktaste" },
	.edit_hint_val   = { "ok", "abbrechen", "bewegen", "löschen" },
	.edit_title_freq = "Band %d: Frequenz (Hz)",
	.edit_title_gain = "Band %d: Gain (dB)",
	.edit_title_q    = "Band %d: Q",
	.edit_title_ggain= "Globaler Gain (dB)",
	.preset_list_title = "Presets",
	.preset_file_label = "Datei: %s",
	.preset_footer_load = "Enter: laden    q: schließen",
	.preset_footer_save = "Enter: weiter    q: schließen",
	.preset_no_presets  = "(keine Presets)",
	.dev_sel_title   = "HID-Gerät auswählen",
	.dev_sel_hint    = "Auf/Ab: bewegen    Enter: verbinden    q: beenden",
};

static const Lang lang_es = {
	.lang_name      = "Español",
	.title          = "FiiO JA11 (KT02H20) - Configurador PEQ Completo",
	.connected      = "CONECTADO:",
	.disconnected   = "DESCONECTADO",
	.preamp         = "Preamplificador Global:",
	.band_hdr       = "Banda",
	.freq_hdr       = "Freq (Hz)",
	.gain_hdr       = "Gan. (dB)",
	.q_hdr          = "Q",
	.type_hdr       = "Tipo",
	.status_hdr     = "Estado",
	.dac_filter     = "Filtro DAC Digital:",
	.sync_ok        = "Sincronizado con el dispositivo",
	.sync_pending   = "** CAMBIOS NO APLICADOS **",
	.modified_warn  = "Cambios sin aplicar. Pulse q de nuevo para salir.",
	.status_conn    = "ESTADO: Conectado",
	.status_disconn = "ESTADO: NO conectado",
	.preset_label   = "Preset:",
	/* Help */
	.help_nav       = "=== NAVEGACIÓN ===",
	.help_arrows    = "  Flechas       Moverse entre bandas/parámetros",
	.help_coarse    = "  +/-           Cambiar valor (paso grande)",
	.help_fine      = "  </>           Cambiar valor (paso fino)",
	.help_toggle    = "  Espacio       Activar/desactivar banda",
	.help_cycle     = "  t             Cambiar tipo de filtro (PK/LSQ/HSQ)",
	.help_tab       = "  Tab/Mayús-Tab Avanzar/retroceder entre celdas",
	.help_edit      = "  e             Editar valor numéricamente (popup)",
	.help_log       = "  l             Mostrar registro HID",
	.help_dev       = "=== ACCIONES DEL DISPOSITIVO ===",
	.help_apply     = "  a             Aplicar cambios a la RAM",
	.help_save      = "  s (luego S)   Guardar en flash (permanente)",
	.help_read      = "  r / R         Recargar config. desde el dispositivo",
	.help_gain      = "  g / G         Establecer ganancia preamp global",
	.help_filter    = "  f / F         Cambiar filtro DAC digital",
	.help_connect   = "  c             Conectar / cambiar dispositivo HID",
	.help_presets   = "=== PRESETS ===",
	.help_psave     = "  p             Guardar preset actual",
	.help_pload     = "  P             Cargar preset",
	.help_pdel      = "  K             Eliminar preset actual",
	.help_other     = "=== OTRO ===",
	.help_reset_flat= "  d             Restablecer a plano (0 dB, Q=0.7)",
	.help_reset_def = "  D             Restablecer a valores predeterminados (freq óptimas)",
	.help_quit      = "  q / Q         Salir",
	/* Messages */
	.msg_filter_set = "Filtro DAC establecido en: %s",
	.msg_applied    = "OK: Cambios aplicados a la RAM.",
	.msg_saved      = "OK: Configuración guardada en flash (permanente).",
	.msg_read_ok    = "OK: Configuración recargada desde el dispositivo.",
	.msg_gain_set   = "Ganancia global establecida en %.1f dB.",
	.msg_prompt_gain= "Ganancia global (%.0f..+%.0f dB) [actual: %+.1f]: ",
	.msg_prompt_pname= "Nombre del preset: ",
	.msg_prompt_pload= "Cargar preset (1-%d): ",
	.msg_confirm_save= "¿Guardar en flash? Pulse S (MAYÚS) para confirmar: ",
	.msg_confirm_del= "¿Eliminar preset '%s'? Pulse K (MAYÚS) para confirmar: ",
	.msg_no_presets = "No hay presets disponibles.",
	.msg_preset_saved= "Preset '%s' guardado.",
	.msg_preset_loaded= "Preset '%s' cargado.",
	.msg_preset_deleted= "Preset eliminado.",
	.msg_cancelled   = "Cancelado.",
	.msg_no_device   = "ERROR: dispositivo no accesible.",
	.msg_udev_hint   = "  No se encontró ningún dispositivo HID. Compruebe USB (lsusb: 2972:0102 / 31b2:0111).",
	.edit_hint_key   = { "Enter", "Esc", "Izq/Der", "Retroceso" },
	.edit_hint_val   = { "ok", "cancelar", "mover", "eliminar" },
	.edit_title_freq = "Banda %d: Frecuencia (Hz)",
	.edit_title_gain = "Banda %d: Ganancia (dB)",
	.edit_title_q    = "Banda %d: Q",
	.edit_title_ggain= "Ganancia global (dB)",
	.preset_list_title = "Presets",
	.preset_file_label = "Archivo: %s",
	.preset_footer_load = "Enter: cargar    q: cerrar",
	.preset_footer_save = "Enter: continuar    q: cerrar",
	.preset_no_presets  = "(sin presets)",
	.dev_sel_title   = "Seleccionar dispositivo HID",
	.dev_sel_hint    = "Arriba/Abajo: mover    Enter: conectar    q: salir",
};

static const Lang *langs[] = { &lang_en, &lang_it, &lang_fr, &lang_de, &lang_es };
static int g_lang = LANG_EN;
#define LANG (*langs[g_lang])

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

/* Preset file path (configurable with --presets / --preset-file) */
static char preset_file[256] = PRESET_FILE_DEFAULT;

/* Quit confirmation: first q with unapplied changes warns, a second q
 * (without any other key in between) exits. */
static bool quitting = false;

/* "Strip" navigation: editing the status-bar values (global preamp gain and
 * DAC digital filter) directly instead of a band row. */
static bool in_strip = false;
static int strip_param = 0;      /* 0 = global preamp gain, 1 = DAC filter */

/* ============================================================
 * HID traffic log
 * ============================================================ */
#define MAX_LOG_LINES 512
#define LOG_LINE_LEN  120
static char log_lines[MAX_LOG_LINES][LOG_LINE_LEN];
static int log_count = 0;

static void log_add(const char *fmt, ...)
{
	va_list args;
	int idx;

	if (log_count < MAX_LOG_LINES)
		idx = log_count;
	else
		idx = log_count % MAX_LOG_LINES;

	va_start(args, fmt);
	vsnprintf(log_lines[idx], LOG_LINE_LEN, fmt, args);
	va_end(args);
	log_lines[idx][LOG_LINE_LEN - 1] = 0;
	log_count++;
}

static const char *hid_cmd_name(int c)
{
	switch (c) {
	case CMD_FILTER_PARAMS: return "FILTER_PARAMS";
	case CMD_GLOBAL_GAIN:   return "GLOBAL_GAIN";
	case CMD_APPLY:         return "APPLY";
	case CMD_SAVE_FLASH:    return "SAVE_FLASH";
	case CMD_DAC_FILTER:    return "DAC_FILTER";
	case CMD_AMP_MODE:      return "AMP_MODE";
	default:                return "?";
	}
}

/* Log one HID exchange (dir = "TX" or "RX"). Bytes are raw protocol bytes;
 * a leading HID report-ID byte (0x02) is skipped for readability. */
static void log_hid(const char *dir, const unsigned char *data, int len)
{
	char hex[3 * 64 + 1];
	char ts[16], hdr[8];
	time_t t;
	struct tm *tm;
	int n = len < 64 ? len : 64;
	int off = 0, i, cmd;

	if (n >= 3 && data[0] == REPORT_ID_FIIO &&
	    (data[1] == READ_HDR1 || data[1] == SET_HDR1) &&
	    (data[2] == READ_HDR2 || data[2] == SET_HDR2))
		off = 1;

	hex[0] = 0;
	for (i = 0; i < n; i++) {
		char tmp[4];
		snprintf(tmp, sizeof(tmp), "%02x ", data[i]);
		strncat(hex, tmp, sizeof(hex) - strlen(hex) - 1);
	}
	if (n > 0)
		hex[strlen(hex) - 1] = 0;   /* strip trailing space */

	t = time(NULL);
	tm = localtime(&t);
	if (tm)
		strftime(ts, sizeof(ts), "%H:%M:%S", tm);
	else
		snprintf(ts, sizeof(ts), "--:--:--");

	cmd = (off + 4 < n) ? data[off + 4] : -1;
	if (off + 1 < n)
		snprintf(hdr, sizeof(hdr), "%02x%02x", data[off], data[off + 1]);
	else
		snprintf(hdr, sizeof(hdr), "??");

	if (cmd >= 0)
		log_add("%s  %s  %s %-14s len=%d  %s",
			ts, dir, hdr, hid_cmd_name(cmd), n, hex);
	else
		log_add("%s  %s  %s len=%d  %s", ts, dir, hdr, n, hex);
}

/* ============================================================
 * HID Low-Level
 * ============================================================ */
/* KT02H20 (FiiO JA11) commands are sent as OUTPUT reports on the interrupt
 * OUT endpoint (hid_write) - exactly like Audiocular-Aura's
 * device.sendReport(2, packet) and hidws's cmd_send_report.
 * The chip does not use feature reports; the response comes back as an
 * INPUT report (interrupt IN), read by read_input_report(). */
static bool send_output_report(const unsigned char *data, int len)
{
	unsigned char buf[65];
	if (!device_handle) return false;
	memset(buf, 0, sizeof(buf));
	buf[0] = REPORT_ID_FIIO;
	if (len > 64) len = 64;
	memcpy(&buf[1], data, len);
	log_hid("TX", data, len);
	return (hid_write(device_handle, buf, len + 1) != -1);
}

static int read_input_report(unsigned char *buf, int len, int timeout_ms)
{
	int ret;
	if (!device_handle) return -1;
	ret = hid_read_timeout(device_handle, buf, len, timeout_ms);
	if (ret > 0)
		log_hid("RX", buf, ret);
	return ret;
}

/* hidapi's libusb backend returns the report ID byte (0x02) as the first
 * byte of a numbered INPUT report - exactly like the WebSocket bridge
 * (aura-bridged / hidws) forwards the raw hid_read buffer. WebHID strips
 * that byte, so the web apps (kt02h20-control, Audiocular-Aura, ...) strip
 * it too. Detect and skip the leading report ID so the protocol packet
 * starts at 0xBB. */
static int find_packet_start(const unsigned char *buf, int len)
{
	if (len >= 3 && buf[0] == REPORT_ID_FIIO &&
		buf[1] == READ_HDR1 && buf[2] == READ_HDR2)
		return 1;                        /* [0x02, 0xBB, 0x0B, ...] */
	if (len >= 3 && buf[1] == READ_HDR1 && buf[2] == READ_HDR2)
		return 1;                        /* unknown report id prefix */
	if (len >= 2 && buf[0] == READ_HDR1 && buf[1] == READ_HDR2)
		return 0;                        /* no report id (raw packet) */
	return 0;
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
	return send_output_report(pkt, sizeof(pkt));
}

static bool apply_changes(void)
{
	unsigned char pkt[] = { SET_HDR1, SET_HDR2, 0, 0,
		CMD_APPLY, APPLY_LEN, 1, 0, FOOTER };
	return device_handle ? send_output_report(pkt, sizeof(pkt)) : false;
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
	return send_output_report(pkt, sizeof(pkt));
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
	send_output_report(pkt, sizeof(pkt));
}

static void set_dac_filter_cmd(int filter_idx)
{
	unsigned char pkt[] = { SET_HDR1, SET_HDR2, 0, 0,
		CMD_DAC_FILTER, DAC_FILTER_LEN, (unsigned char)filter_idx, 0, FOOTER };
	if (!device_handle) return;
	send_output_report(pkt, sizeof(pkt));
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
		if (send_output_report(cmd, sizeof(cmd))) {
			memset(resp, 0, sizeof(resp));
			ret = read_input_report(resp, sizeof(resp), 500);
			if (ret > 0) {
				int off = find_packet_start(resp, ret);
				if (resp[off + 4] == CMD_GLOBAL_GAIN) {
					int raw = (resp[off + 7] << 8) | resp[off + 6];
					if (raw > 32767) raw -= 65536;
					global_gain = (double)raw / 2560.0;
				}
			}
		}
	}
	/* Read DAC filter (from input report) */
	{
		unsigned char cmd[] = { READ_HDR1, READ_HDR2, 0, 0,
			CMD_DAC_FILTER, 0, 0, FOOTER };
		if (send_output_report(cmd, sizeof(cmd))) {
			memset(resp, 0, sizeof(resp));
			ret = read_input_report(resp, sizeof(resp), 500);
			if (ret > 0) {
				int off = find_packet_start(resp, ret);
				if (resp[off + 4] == CMD_DAC_FILTER) {
					int val = resp[off + 6];
					if (val >= 1 && val <= DAC_FILTER_COUNT)
						dac_filter = val;
				}
			}
		}
	}
	/* Read each band */
	for (int i = 0; i < NUM_BANDS; i++) {
		unsigned char cmd[] = { READ_HDR1, READ_HDR2, 0, 0,
			CMD_READ_PARAM, 1, i, FOOTER };
		if (send_output_report(cmd, sizeof(cmd))) {
			memset(resp, 0, sizeof(resp));
			ret = read_input_report(resp, sizeof(resp), 500);
			if (ret > 0) {
				int off = find_packet_start(resp, ret);
				if (resp[off + 4] == CMD_READ_PARAM) {
					int idx = resp[off + 6];
					if (idx >= 0 && idx < NUM_BANDS) {
						int rg = (resp[off + 7] << 8) | resp[off + 8];
						if (rg > 32767) rg -= 65536;
						bands[idx].gain = (double)rg / 10.0;
						bands[idx].freq = (double)((resp[off + 9] << 8) | resp[off + 10]);
						int rq = (resp[off + 11] << 8) | resp[off + 12];
						bands[idx].q = (double)rq / 100.0;
						bands[idx].filter_type = resp[off + 13] & 0x03;
						bands[idx].enabled = true;
					}
				}
			}
		}
	}
	return true;
}

/* ============================================================
 * HID device enumeration & selection
 * (libusb backend, mirrors hidws: enumerate all, open selected)
 * ============================================================ */
#define MAX_DEVICES 32

typedef struct {
	char path[256];
	unsigned short vendor_id;
	unsigned short product_id;
	char product_string[128];
	int compatible;
} DeviceEntry;

static DeviceEntry devices[MAX_DEVICES];
static int num_devices = 0;

static int device_is_compatible(unsigned short vid, unsigned short pid,
                                const char *product)
{
	if ((vid == FIIO_VID && pid == JA11_PID) ||
	    (vid == JKALLY_VID && pid == JM12_PID))
		return 1;
	if (product &&
	    (strstr(product, "JA11") || strstr(product, "ja11") ||
	     strstr(product, "KT02H20") || strstr(product, "JM12")))
		return 1;
	return 0;
}

/* Like hidws cmd_list: enumerate ALL HID devices (no VID/PID filter) */
static int enumerate_devices(void)
{
	struct hid_device_info *devs;
	struct hid_device_info *cur;

	num_devices = 0;
	if (hid_init() != 0) return 0;
	devs = hid_enumerate(0, 0);
	for (cur = devs; cur && num_devices < MAX_DEVICES; cur = cur->next) {
		DeviceEntry *d = &devices[num_devices];
		snprintf(d->path, sizeof(d->path), "%s",
		         cur->path ? cur->path : "");
		d->vendor_id = cur->vendor_id;
		d->product_id = cur->product_id;
		if (cur->product_string)
			wcstombs(d->product_string, cur->product_string,
			         sizeof(d->product_string) - 1);
		else
			d->product_string[0] = 0;
		d->product_string[sizeof(d->product_string) - 1] = 0;
		d->compatible = device_is_compatible(d->vendor_id,
		                                     d->product_id,
		                                     d->product_string);
		num_devices++;
	}
	hid_free_enumeration(devs);
	return num_devices;
}

static bool connect_to_entry(const DeviceEntry *d)
{
	if (!d || !d->path[0]) return false;
	if (device_handle) { hid_close(device_handle); device_handle = NULL; }
	device_handle = hid_open_path(d->path);
	if (!device_handle) return false;
	device_connected = true;
	device_vid = d->vendor_id;
	device_pid = d->product_id;
	if (d->product_string[0])
		snprintf(device_name, sizeof(device_name), "%s",
		         d->product_string);
	else
		snprintf(device_name, sizeof(device_name), "0x%04x:0x%04x",
		         d->vendor_id, d->product_id);
	read_device_config();
	return true;
}

/* ncurses picker: lists available HID devices, lets the user choose one.
 * Returns the selected index, or -1 if cancelled. */
static int select_device_menu(void)
{
	const Lang *l = &LANG;
	int sel = 0, ch;
	int h, w, y, x;

	if (num_devices <= 0) return -1;
	/* Pre-select a known-compatible device if present */
	for (int i = 0; i < num_devices; i++)
		if (devices[i].compatible) { sel = i; break; }

	h = num_devices + 6;
	w = 74;
	y = (LINES - h) / 2;
	x = (COLS - w) / 2;
	if (h > LINES) h = LINES;
	if (w > COLS) w = COLS;
	if (y < 0) y = 0;
	if (x < 0) x = 0;

	WINDOW *win = newwin(h, w, y, x);
	keypad(win, TRUE);
	box(win, 0, 0);
	wattron(win, A_BOLD);
	mvwaddstr(win, 0, 2, l->dev_sel_title);
	wattroff(win, A_BOLD);
	mvwaddstr(win, 2, 2, "   VID:PID     Product");
	mvwaddstr(win, h - 2, 2, l->dev_sel_hint);

	while (1) {
		for (int i = 0; i < num_devices; i++) {
			char line[128];
			const DeviceEntry *d = &devices[i];
			snprintf(line, sizeof(line), "%04X:%04X  %s",
			         d->vendor_id, d->product_id,
			         d->product_string[0] ? d->product_string
			                              : "(no name)");
			mvwaddstr(win, 3 + i, 2, line);
			mvwaddch(win, 3 + i, 1, d->compatible ? '*' : ' ');
			if (i == sel) {
				wattron(win, A_REVERSE);
				mvwaddstr(win, 3 + i, 2, line);
				wattroff(win, A_REVERSE);
			} else if (d->compatible) {
				wattron(win, COLOR_PAIR(3));
				mvwaddstr(win, 3 + i, 2, line);
				wattroff(win, COLOR_PAIR(3));
			}
		}
		wnoutrefresh(win);
		doupdate();

		ch = wgetch(win);
		if (ch == KEY_UP) {
			if (sel > 0) sel--;
		} else if (ch == KEY_DOWN) {
			if (sel < num_devices - 1) sel++;
		} else if (ch == 'q' || ch == 'Q' || ch == 27) {
			delwin(win);
			return -1;
		} else if (ch == '\n' || ch == '\r' || ch == KEY_ENTER) {
			int idx = sel;
			delwin(win);
			return idx;
		}
	}
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
	FILE *f = fopen(preset_file, "w");
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
	FILE *f = fopen(preset_file, "r");
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
 * Device helpers (shared by table and strip editing)
 * ============================================================ */
static void set_status(const char *fmt, ...);   /* defined later */

static void cycle_dac_filter(void)
{
	const Lang *l = &LANG;
	dac_filter = (dac_filter % DAC_FILTER_COUNT) + 1;
	/* Leave the change "pending": do NOT auto-apply to RAM, so the
	 * "** MODIFICATIONS NOT APPLIED **" warning is shown until the user
	 * presses 'a' (consistent with band edits). */
	modified = true;
	set_status(l->msg_filter_set, dac_filter_name(dac_filter));
}

static void apply_global_gain(double v)
{
	const Lang *l = &LANG;
	global_gain = v;
	/* Leave the change "pending": do NOT auto-apply to RAM, so the
	 * "** MODIFICATIONS NOT APPLIED **" warning is shown until the user
	 * presses 'a' (consistent with band and DAC-filter edits). */
	modified = true;
	set_status(l->msg_gain_set, global_gain);
}

/* Adjust the currently selected strip parameter by dir (+1/-1). */
static void adjust_strip(int dir)
{
	if (strip_param == 0) {
		global_gain += dir * 0.5;
		if (global_gain > GLOBAL_GAIN_MAX) global_gain = GLOBAL_GAIN_MAX;
		if (global_gain < GLOBAL_GAIN_MIN) global_gain = GLOBAL_GAIN_MIN;
		apply_global_gain(global_gain);
	} else {
		cycle_dac_filter();
	}
}

/* ============================================================
 * Numeric popup editor
 * ============================================================ */
/* Draw one popup hint line: the two key names in cyan/bold and the two
 * action words in yellow, so the keys stand out from their meaning. */
static void draw_hint_pair(WINDOW *win, int row, int k0, int k1)
{
	const Lang *l = &LANG;
	int col = 2;
	int idx[2] = { k0, k1 };

	for (int i = 0; i < 2; i++) {
		int k = idx[i];
		wattron(win, COLOR_PAIR(6) | A_BOLD);
		mvwaddstr(win, row, col, l->edit_hint_key[k]);
		col += (int)strlen(l->edit_hint_key[k]);
		wattroff(win, COLOR_PAIR(6) | A_BOLD);
		mvwaddstr(win, row, col, ": ");
		col += 2;
		wattron(win, COLOR_PAIR(4));
		mvwaddstr(win, row, col, l->edit_hint_val[k]);
		col += (int)strlen(l->edit_hint_val[k]);
		wattroff(win, COLOR_PAIR(4));
		if (i == 0) {
			mvwaddstr(win, row, col, "    ");
			col += 4;
		}
	}
}

/* Digit-by-digit numeric editor popup. The current value is pre-filled;
 * each character can be edited with the cursor, Backspace deletes, new
 * digits insert. Enter accepts (if within [minv,maxv]), Esc cancels. */
static bool edit_numeric(double *out, double minv, double maxv, int dec,
                         const char *title)
{
	char buf[40], rng[64], fmt[8];
	int len, pos = 0, ch;
	int h = 10, w = 56;
	int y = (LINES - h) / 2, x = (COLS - w) / 2;
	bool ok = false;

	snprintf(fmt, sizeof(fmt), "%%.%df", dec);
	snprintf(buf, sizeof(buf), fmt, *out);
	len = (int)strlen(buf);
	snprintf(rng, sizeof(rng), "%.*f .. %.*f", dec, minv, dec, maxv);

	if (y < 0) y = 0;
	if (x < 0) x = 0;

	WINDOW *win = newwin(h, w, y, x);
	keypad(win, TRUE);
	box(win, 0, 0);
	wattron(win, A_BOLD);
	mvwaddstr(win, 0, 2, title);
	wattroff(win, A_BOLD);
	mvwaddstr(win, 2, 2, rng);
	draw_hint_pair(win, h - 3, 0, 1);   /* Enter/Esc line */
	draw_hint_pair(win, h - 2, 2, 3);   /* Left-Right/Backspace line */

	while (1) {
		int i;
		mvwaddstr(win, 2, 2, rng);      /* redraw range every pass */
		mvwhline(win, 4, 2, ' ', w - 4);
		wmove(win, 4, 2);
		for (i = 0; i < len; i++) {
			if (i == pos) wattron(win, A_REVERSE);
			waddch(win, buf[i]);
			if (i == pos) wattroff(win, A_REVERSE);
		}
		if (pos >= len) {
			wattron(win, A_REVERSE);
			waddch(win, ' ');
			wattroff(win, A_REVERSE);
		}
		wnoutrefresh(win);
		doupdate();

		ch = wgetch(win);
		if (ch == 27) {
			ok = false;
			break;
		} else if (ch == '\n' || ch == '\r' || ch == KEY_ENTER) {
			double v = atof(buf);
			if (v >= minv - 1e-9 && v <= maxv + 1e-9) {
				*out = v;
				ok = true;
				break;
			}
			/* Out of range: show a brief error and keep editing */
			wattron(win, A_BOLD | COLOR_PAIR(2));
			mvwaddstr(win, 2, 2, "OUT OF RANGE!");
			wattroff(win, A_BOLD | COLOR_PAIR(2));
			wnoutrefresh(win);
			doupdate();
			usleep(400000);
		} else if (ch == KEY_LEFT) {
			if (pos > 0) pos--;
		} else if (ch == KEY_RIGHT) {
			if (pos < len) pos++;
		} else if (ch == KEY_HOME) {
			pos = 0;
		} else if (ch == KEY_END) {
			pos = len;
		} else if (ch == 127 || ch == KEY_BACKSPACE || ch == 8) {
			if (pos > 0) {
				memmove(&buf[pos - 1], &buf[pos], len - pos + 1);
				pos--;
				len--;
			}
		} else if (ch == KEY_DC) {
			if (pos < len) {
				memmove(&buf[pos], &buf[pos + 1], len - pos + 1);
				len--;
			}
		} else if ((ch >= '0' && ch <= '9') || ch == '-' || ch == '.') {
			if (len < (int)sizeof(buf) - 2) {
				memmove(&buf[pos + 1], &buf[pos], len - pos + 1);
				buf[pos] = (char)ch;
				pos++;
				len++;
			}
		}
		if (pos > len) pos = len;
	}
	delwin(win);
	return ok;
}

/* General text popup editor (like edit_numeric, but accepts any printable
 * characters). Enter accepts, Esc cancels, arrows/Home/End move, Backspace
 * deletes. */
static bool edit_text(char *out, int outlen, const char *title)
{
	char buf[64];
	int len, pos = 0, ch;
	int h = 10, w = 56;
	int y = (LINES - h) / 2, x = (COLS - w) / 2;
	bool ok = false;

	strncpy(buf, out, sizeof(buf) - 1);
	buf[sizeof(buf) - 1] = 0;
	len = (int)strlen(buf);

	if (y < 0) y = 0;
	if (x < 0) x = 0;

	WINDOW *win = newwin(h, w, y, x);
	keypad(win, TRUE);
	box(win, 0, 0);
	wattron(win, A_BOLD);
	mvwaddstr(win, 0, 2, title);
	wattroff(win, A_BOLD);
	draw_hint_pair(win, h - 3, 0, 1);
	draw_hint_pair(win, h - 2, 2, 3);

	while (1) {
		int i;
		mvwhline(win, 4, 2, ' ', w - 4);
		wmove(win, 4, 2);
		for (i = 0; i < len; i++) {
			if (i == pos) wattron(win, A_REVERSE);
			waddch(win, buf[i]);
			if (i == pos) wattroff(win, A_REVERSE);
		}
		if (pos >= len) {
			wattron(win, A_REVERSE);
			waddch(win, ' ');
			wattroff(win, A_REVERSE);
		}
		wnoutrefresh(win);
		doupdate();

		ch = wgetch(win);
		if (ch == 27) {
			ok = false;
			break;
		} else if (ch == '\n' || ch == '\r' || ch == KEY_ENTER) {
			if (len > 0) {
				strncpy(out, buf, outlen - 1);
				out[outlen - 1] = 0;
				ok = true;
			}
			break;
		} else if (ch == KEY_LEFT) {
			if (pos > 0) pos--;
		} else if (ch == KEY_RIGHT) {
			if (pos < len) pos++;
		} else if (ch == KEY_HOME) {
			pos = 0;
		} else if (ch == KEY_END) {
			pos = len;
		} else if (ch == 127 || ch == KEY_BACKSPACE || ch == 8) {
			if (pos > 0) {
				memmove(&buf[pos - 1], &buf[pos], len - pos + 1);
				pos--;
				len--;
			}
		} else if (ch == KEY_DC) {
			if (pos < len) {
				memmove(&buf[pos], &buf[pos + 1], len - pos + 1);
				len--;
			}
		} else if (ch >= 32 && ch <= 126) {
			if (len < (int)sizeof(buf) - 2) {
				memmove(&buf[pos + 1], &buf[pos], len - pos + 1);
				buf[pos] = (char)ch;
				pos++;
				len++;
			}
		}
		if (pos > len) pos = len;
	}
	delwin(win);
	return ok;
}

/* Open the numeric popup on the currently selected strip parameter. */
static void edit_strip(void)
{
	const Lang *l = &LANG;
	if (strip_param == 0) {
		double v = global_gain;
		if (edit_numeric(&v, GLOBAL_GAIN_MIN, GLOBAL_GAIN_MAX, 1,
		                 l->edit_title_ggain)) {
			apply_global_gain(v);
		} else {
			set_status("%s", l->msg_cancelled);
		}
	} else {
		cycle_dac_filter();
	}
}

/* Open the numeric popup on the currently selected table cell. */
static void edit_current_cell(void)
{
	const Lang *l = &LANG;
	double v;
	char label[48];
	const char *edit_title = NULL;
	double lo, hi;
	int dec;

	switch (current_param) {
	case 0:
		edit_title = l->edit_title_freq;
		lo = FREQ_MIN; hi = FREQ_MAX; dec = 0;
		break;
	case 1:
		edit_title = l->edit_title_gain;
		lo = GAIN_MIN; hi = GAIN_MAX; dec = 1;
		break;
	case 2:
		edit_title = l->edit_title_q;
		lo = Q_MIN; hi = Q_MAX; dec = 2;
		break;
	default:
		edit_title = NULL;
		break;
	}
	if (edit_title) {
		snprintf(label, sizeof(label), edit_title, current_band + 1);
		switch (current_param) {
		case 0: v = bands[current_band].freq; break;
		case 1: v = bands[current_band].gain; break;
		default: v = bands[current_band].q; break;
		}
		if (edit_numeric(&v, lo, hi, dec, label)) {
			switch (current_param) {
			case 0: bands[current_band].freq = v; break;
			case 1: bands[current_band].gain = v; break;
			case 2: bands[current_band].q    = v; break;
			}
			modified = true;
		} else {
			set_status("%s", l->msg_cancelled);
		}
	}
}

/* ============================================================
 * HID log viewer (l)
 * ============================================================ */
static void show_log_screen(void)
{
	int h = LINES - 2, w = COLS - 2;
	int top = 0, vis, ch, total, start, i;

	if (h < 8) h = 8;
	if (w < 44) w = 44;
	if (h > LINES - 1) h = LINES - 1;

	WINDOW *win = newwin(h, w, 1, 1);
	keypad(win, TRUE);
	vis = h - 2;
	if (vis < 1) vis = 1;

	total = log_count < MAX_LOG_LINES ? log_count : MAX_LOG_LINES;
	start = log_count < MAX_LOG_LINES ? 0 : (log_count % MAX_LOG_LINES);
	if (total > vis) top = total - vis;   /* auto-follow newest */

	while (1) {
		int shown = total - top;
		if (shown > vis) shown = vis;

		werase(win);
		box(win, 0, 0);
		wattron(win, A_BOLD);
		mvwaddstr(win, 0, 2, "HID Log");
		wattroff(win, A_BOLD);
		mvwaddstr(win, 0, w - 12, "q: close");
		for (i = 0; i < shown; i++) {
			int idx = (start + top + i) % MAX_LOG_LINES;
			mvwaddstr(win, 1 + i, 2, log_lines[idx]);
		}
		if (total == 0)
			mvwaddstr(win, h - 1, 2, "No HID traffic yet.   q: close");
		else
			mvwprintw(win, h - 1, 2,
				"[%d-%d/%d]  Up/Down: scroll   PgUp/PgDn   Home/End   q: close",
				top + 1, top + shown, total);
		wnoutrefresh(win);
		doupdate();

		ch = wgetch(win);
		if (ch == 'q' || ch == 'Q' || ch == 27)
			break;
		else if (ch == KEY_UP || ch == 'k') {
			if (top > 0) top--;
		} else if (ch == KEY_DOWN || ch == 'j') {
			if (top + vis < total) top++;
		} else if (ch == KEY_PPAGE || ch == 'b') {
			top -= vis;
			if (top < 0) top = 0;
		} else if (ch == KEY_NPAGE || ch == ' ') {
			top += vis;
			if (top > total - vis) top = total - vis;
			if (top < 0) top = 0;
		} else if (ch == KEY_HOME) {
			top = 0;
		} else if (ch == KEY_END) {
			top = total - vis;
			if (top < 0) top = 0;
		}
	}
	delwin(win);
}

/* Full-screen, scrollable list of the saved presets, showing the preset
 * file path. Returns: selected preset index on Enter, -2 when closed with
 * 'q', -1 when cancelled with Esc. */
static int show_preset_list(int sel, bool save_mode)
{
	const Lang *l = &LANG;
	int h = LINES - 2, w = COLS - 2;
	int top = 0, vis, ch, total = num_presets;
	int ret = -1;

	if (h < 8) h = 8;
	if (w < 44) w = 44;
	if (h > LINES - 1) h = LINES - 1;

	WINDOW *win = newwin(h, w, 1, 1);
	keypad(win, TRUE);
	vis = h - 5;
	if (vis < 1) vis = 1;

	if (sel < 0) sel = 0;
	if (total > 0 && sel >= total) sel = total - 1;
	if (sel > top + vis - 1) top = sel - vis + 1;
	if (top < 0) top = 0;

	while (1) {
		int shown = total - top;
		if (shown > vis) shown = vis;

		werase(win);
		box(win, 0, 0);
		wattron(win, A_BOLD);
		mvwaddstr(win, 0, 2, l->preset_list_title);
		wattroff(win, A_BOLD);
		mvwaddstr(win, 0, w - 12, "q: close");
		mvwprintw(win, 1, 2, l->preset_file_label, preset_file);
		mvwaddstr(win, 2, 2, " #  Name");
		for (int i = 0; i < shown; i++) {
			int idx = top + i;
			char line[96];
			snprintf(line, sizeof(line), "%2d  %s",
			         idx + 1, presets[idx].name);
			if (idx == sel) wattron(win, A_REVERSE);
			mvwaddstr(win, 3 + i, 2, line);
			if (idx == sel) wattroff(win, A_REVERSE);
		}
		if (total == 0)
			mvwaddstr(win, 3, 2, l->preset_no_presets);
		if (total > 0)
			mvwprintw(win, h - 1, 2, "[%d/%d]  %s", sel + 1, total,
				save_mode ? l->preset_footer_save : l->preset_footer_load);
		else
			mvwaddstr(win, h - 1, 2,
				save_mode ? l->preset_footer_save : l->preset_footer_load);
		wnoutrefresh(win);
		doupdate();

		ch = wgetch(win);
		if (ch == 27) {
			ret = -1;
			break;
		} else if (ch == 'q' || ch == 'Q') {
			ret = -2;
			break;
		} else if (ch == '\n' || ch == '\r' || ch == KEY_ENTER) {
			ret = sel;
			break;
		} else if (ch == KEY_UP || ch == 'k') {
			if (sel > 0) sel--;
			if (sel < top) top = sel;
		} else if (ch == KEY_DOWN || ch == 'j') {
			if (sel < total - 1) sel++;
			if (sel >= top + vis) top = sel - vis + 1;
		} else if (ch == KEY_PPAGE) {
			sel -= vis;
			if (sel < 0) sel = 0;
			top = sel;
		} else if (ch == KEY_NPAGE) {
			sel += vis;
			if (sel >= total) sel = total - 1;
			top = sel - vis + 1;
			if (top < 0) top = 0;
		} else if (ch == KEY_HOME) {
			sel = 0;
			top = 0;
		} else if (ch == KEY_END) {
			sel = total - 1;
			if (sel < 0) sel = 0;
			top = sel - vis + 1;
			if (top < 0) top = 0;
		}
	}
	delwin(win);
	return ret;
}

/* ============================================================
 * UI Rendering
 * ============================================================ */
/* Table column layout (shared by headers and rows so they align) */
#define COL_MARKER  0
#define COL_BAND    2
#define COL_FREQ   10
#define COL_GAIN   24
#define COL_Q      38
#define COL_TYPE   52
#define COL_STATUS 62

static int cell_col(int param)
{
	switch (param) {
	case 0: return COL_FREQ;
	case 1: return COL_GAIN;
	case 2: return COL_Q;
	case 3: return COL_TYPE;
	case 4: return COL_STATUS;
	default: return COL_FREQ;
	}
}

static void draw_cell(WINDOW *win, int row, int col, const char *text, bool hl)
{
	if (hl) wattron(win, A_REVERSE);
	mvwaddstr(win, row, col, text);
	if (hl) wattroff(win, A_REVERSE);
}

/* Status bar doubles as an editable "strip": when in_strip is set the
 * selected value (global preamp gain or DAC filter) is drawn non-reversed
 * so it stands out against the reversed bar. */
static void draw_status_bar(WINDOW *win, int width, bool strip_active,
                            int strip_param_idx)
{
	const Lang *l = &LANG;
	wattrset(win, A_REVERSE);
	mvwaddstr(win, 0, 0, " ");
	if (device_connected) {
		wattron(win, COLOR_PAIR(3));
		wprintw(win, " %s %s", l->connected, device_name);
		wattroff(win, COLOR_PAIR(3));
		wprintw(win, "  %s", l->preamp);
		if (strip_active && strip_param_idx == 0)
			wattron(win, A_NORMAL | A_BOLD);
		wprintw(win, "%.1f dB", global_gain);
		if (strip_active && strip_param_idx == 0)
			wattroff(win, A_NORMAL | A_BOLD);
		wprintw(win, "  %s", l->dac_filter);
		if (strip_active && strip_param_idx == 1)
			wattron(win, A_NORMAL | A_BOLD);
		wprintw(win, "%s", dac_filter_name(dac_filter));
		if (strip_active && strip_param_idx == 1)
			wattroff(win, A_NORMAL | A_BOLD);
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
	mvwhline(win, 0, 0, ' ', getmaxx(win));
	wattron(win, A_BOLD | COLOR_PAIR(6));
	mvwaddstr(win, 0, COL_BAND, l->band_hdr);
	mvwaddstr(win, 0, COL_FREQ, l->freq_hdr);
	mvwaddstr(win, 0, COL_GAIN, l->gain_hdr);
	mvwaddstr(win, 0, COL_Q, l->q_hdr);
	mvwaddstr(win, 0, COL_TYPE, l->type_hdr);
	mvwaddstr(win, 0, COL_STATUS, l->status_hdr);
	wattroff(win, A_BOLD | COLOR_PAIR(6));
	mvwhline(win, 1, 0, ' ', width);
}

static void draw_band_row(WINDOW *win, int row, int band_idx, bool selected,
                          int sel_param)
{
	char buf_freq[16], buf_gain[16], buf_q[16];
	char pre = ' ';
	char status[4] = "   ";
	Band *b = &bands[band_idx];

	mvwhline(win, row, 0, ' ', getmaxx(win));

	if (selected)
		pre = '>';
	else if (!b->enabled)
		pre = 'x';

	/* Selector marker */
	if (selected) wattron(win, A_REVERSE);
	mvwaddch(win, row, COL_MARKER, pre);
	if (selected) wattroff(win, A_REVERSE);

	/* Band number */
	wattron(win, COLOR_PAIR(6));
	mvwprintw(win, row, COL_BAND + 1, "%d", band_idx + 1);
	wattroff(win, COLOR_PAIR(6));

	snprintf(buf_freq, sizeof(buf_freq), "%.0f", b->freq);
	snprintf(buf_gain, sizeof(buf_gain), "%+.1f", b->enabled ? b->gain : 0.0);
	snprintf(buf_q, sizeof(buf_q), "%.2f", b->enabled ? b->q : 0.7);
	strcpy(status, b->enabled ? "ON" : "OFF");

	/* Values; only the currently edited cell is highlighted */
	draw_cell(win, row, COL_FREQ, buf_freq, selected && sel_param == 0);
	draw_cell(win, row, COL_GAIN, buf_gain, selected && sel_param == 1);
	draw_cell(win, row, COL_Q,    buf_q,    selected && sel_param == 2);
	draw_cell(win, row, COL_TYPE, filter_type_name(b->filter_type),
	          selected && sel_param == 3);

	if (selected && sel_param == 4) wattron(win, A_REVERSE);
	wattron(win, b->enabled ? COLOR_PAIR(3) : COLOR_PAIR(5));
	mvwaddstr(win, row, COL_STATUS, status);
	wattroff(win, b->enabled ? COLOR_PAIR(3) : COLOR_PAIR(5));
	if (selected && sel_param == 4) wattroff(win, A_REVERSE);

	wattrset(win, A_NORMAL);
}

/* Bar chart for gain visualization */
static const double EQ_TWO_PI = 6.28318530717958647692; /* 2 * pi */

/* Real biquad magnitude (dB) at frequency f for one band. Uses the RBJ
 * Audio EQ Cookbook coefficients - the same function as the FiiO Control
 * web app / Audiocular-Aura / fiiocontrol-oss visualizers - evaluated at
 * 48 kHz. The total response at f is the sum of each band's magnitude. */
static double biquad_magnitude_db(int filter_type, double freq, double gain,
                                  double q, double f, double fs)
{
        double b0 = 1.0, b1 = 0.0, b2 = 0.0, a0 = 1.0, a1 = 0.0, a2 = 0.0;
        double w0, A, s, sinw, cosw, alpha;

        if (gain == 0.0)
                return 0.0;

        w0    = EQ_TWO_PI * freq / fs;
        A     = pow(10.0, gain / 40.0);
        s     = sqrt(A);
        sinw  = sin(w0);
        cosw  = cos(w0);
        alpha = sinw / (2.0 * q);

        switch (filter_type) {
        case FILTER_PK:
                b0 = 1.0 + alpha * A; b1 = -2.0 * cosw; b2 = 1.0 - alpha * A;
                a0 = 1.0 + alpha / A; a1 = -2.0 * cosw; a2 = 1.0 - alpha / A;
                break;
        case FILTER_LSQ:
                b0 = A * (A + 1.0 - (A - 1.0) * cosw + 2.0 * s * alpha);
                b1 = 2.0 * A * (A - 1.0 - (A + 1.0) * cosw);
                b2 = A * (A + 1.0 - (A - 1.0) * cosw - 2.0 * s * alpha);
                a0 = A + 1.0 + (A - 1.0) * cosw + 2.0 * s * alpha;
                a1 = -2.0 * (A - 1.0 + (A + 1.0) * cosw);
                a2 = A + 1.0 + (A - 1.0) * cosw - 2.0 * s * alpha;
                break;
        case FILTER_HSQ:
                b0 = A * (A + 1.0 + (A - 1.0) * cosw + 2.0 * s * alpha);
                b1 = -2.0 * A * (A - 1.0 + (A + 1.0) * cosw);
                b2 = A * (A + 1.0 + (A - 1.0) * cosw - 2.0 * s * alpha);
                a0 = A + 1.0 - (A - 1.0) * cosw + 2.0 * s * alpha;
                a1 = 2.0 * (A - 1.0 - (A + 1.0) * cosw);
                a2 = A + 1.0 - (A - 1.0) * cosw - 2.0 * s * alpha;
                break;
        default:
                return 0.0;
        }

        {
                double w = EQ_TWO_PI * f / fs;
                double c1 = cos(w), s1 = sin(w), c2 = cos(2.0 * w), s2 = sin(2.0 * w);
                double numR = b0 + b1 * c1 + b2 * c2;
                double numI = -(b1 * s1 + b2 * s2);
                double denR = a0 + a1 * c1 + a2 * c2;
                double denI = -(a1 * s1 + a2 * s2);
                double numM2 = numR * numR + numI * numI;
                double denM2 = denR * denR + denI * denI;
                if (denM2 <= 0.0)
                        return 0.0;
                return 10.0 * log10(numM2 / denM2);
        }
}

/* Total frequency response (dB) at f: sum of every enabled band's biquad
 * magnitude, matching the FiiO Control reference curve. */
static double response_db(double f)
{
        double db = 0.0;
        for (int i = 0; i < NUM_BANDS; i++) {
                const Band *b = &bands[i];
                if (!b->enabled || b->gain == 0.0)
                        continue;
                db += biquad_magnitude_db(b->filter_type, b->freq, b->gain,
                                          b->q, f, 48000.0);
        }
        return db;
}

/* Draw the real frequency-response curve of the active bands on a log
 * frequency axis (20 Hz - 20 kHz) with dB grid lines. Recomputed on every
 * redraw, so it updates live while editing (like ktmicro_tui.py). */
static void draw_response_curve(WINDOW *win, int start_row, int max_width)
{
        /* Draw the real frequency-response curve of the active EQ bands on a
         * logarithmic frequency axis (20 Hz - 20 kHz) with a dB scale, decade
         * grid lines and frequency labels - the same UX as ktmicro_tui.py.
         * Recomputed on every redraw so it updates live while editing.
         *
         * All glyphs are single-byte ACS characters because freetz ncurses is
         * built with --disable-widec: multibyte UTF-8 glyphs would be split by
         * ncurses' byte-level diffing on every redraw.  The UTF-8 terminal of
         * the user renders these as box-drawing chars (─, │, ·). */
        const double dbmax = 12.0;
        const double fmin  = FREQ_MIN;   /* 20 Hz  */
        const double fmax  = FREQ_MAX;   /* 20 kHz */
        const int left     = 7;          /* room for "+12 │" style labels */
        const double gridf[3] = { 100.0, 1000.0, 10000.0 };
        const int dbs[5] = { 12, 6, 0, -6, -12 };
        int win_h = getmaxy(win);
        int win_w = getmaxx(win);
        int plot_w = win_w - left - 1;   /* curve columns (0 .. plot_w-1) */
        int height = win_h - 1;          /* curve rows (0 .. height-1) */
        int zero;                        /* row of the 0 dB reference line */
        int gc[3];                       /* grid columns: 100 Hz, 1 kHz, 10 kHz */
        int r, c, i;
        int prev = -1;

        (void)start_row;
        (void)max_width;

        if (plot_w < 10 || height < 5) {
                mvwaddstr(win, 0, 1, "(terminal too small for graph)");
                return;
        }

        /* Decade grid columns (log positions of 100 Hz, 1 kHz, 10 kHz). */
        for (i = 0; i < 3; i++)
                gc[i] = (int)lround(log10(gridf[i] / fmin)
                                    / log10(fmax / fmin) * (double)(plot_w - 1));

        /* Clear the whole plot area first so no stale curve pixels remain. */
        for (r = 0; r <= height; r++)
                mvwhline(win, r, left, ' ', plot_w);

        /* dB axis labels (+12 .. -12) with a vertical axis separator. */
        for (i = 0; i < 5; i++) {
                int y = (int)lround(((dbmax - dbs[i]) / (2.0 * dbmax))
                                    * (double)(height - 1));
                if (y < 0) y = 0;
                if (y > height - 1) y = height - 1;
                wattron(win, COLOR_PAIR(6));
                mvwprintw(win, y, 1, "%+4d", dbs[i]);
                mvwaddch(win, y, left - 1, ACS_VLINE);
                wattroff(win, COLOR_PAIR(6));
        }

        zero = (int)lround((dbmax / (2.0 * dbmax)) * (double)(height - 1));

        /* 0 dB reference line, with a dot at decade crossings. */
        wattron(win, COLOR_PAIR(6));
        for (c = 0; c < plot_w; c++) {
                int is_grid = 0;
                for (i = 0; i < 3; i++)
                        if (c == gc[i]) { is_grid = 1; break; }
                mvwaddch(win, zero, left + c, is_grid ? ACS_BULLET : ACS_HLINE);
        }
        wattroff(win, COLOR_PAIR(6));

        /* Vertical decade grid lines (dimmed cyan), skipping the 0 dB row. */
        for (i = 0; i < 3; i++) {
                for (r = 0; r < height; r++) {
                        if (r == zero) continue;
                        wattron(win, A_DIM | COLOR_PAIR(6));
                        mvwaddch(win, r, left + gc[i], ACS_VLINE);
                        wattroff(win, A_DIM | COLOR_PAIR(6));
                }
        }

        /* Frequency-response curve: '@' at each sample, vertical connector
         * between consecutive samples. */
        for (c = 0; c < plot_w; c++) {
                double lf = log10(fmin) + (log10(fmax) - log10(fmin))
                                * (double)c / (double)(plot_w - 1);
                double f  = pow(10.0, lf);
                double db = response_db(f);
                int y;

                if (db < -dbmax) db = -dbmax;
                if (db >  dbmax) db =  dbmax;
                y = (int)lround(((dbmax - db) / (2.0 * dbmax)) * (double)(height - 1));
                if (y < 0) y = 0;
                if (y > height - 1) y = height - 1;

                if (prev != -1) {
                        int r0 = prev < y ? prev : y;
                        int r1 = prev < y ? y : prev;
                        for (r = r0; r <= r1; r++)
                                mvwaddch(win, r, left + c,
                                         r == y ? '@' : ACS_VLINE);
                } else {
                        mvwaddch(win, y, left + c, '@');
                }
                prev = y;
        }

        /* Frequency labels (bottom row): 20, 100, 1k, 10k, 20k. */
        wattron(win, COLOR_PAIR(6));
        mvwaddstr(win, height, left, "20");
        mvwaddstr(win, height, left + gc[0] - 1, "100");
        mvwaddstr(win, height, left + gc[1] - 2, "1k");
        mvwaddstr(win, height, left + gc[2] - 2, "10k");
        mvwaddstr(win, height, left + plot_w - 3, "20k");
        wattroff(win, COLOR_PAIR(6));
}


/* Full-screen, scrollable help (opened with ? / h / H). Works on any
 * terminal size. */
static void show_full_help(void)
{
	const Lang *l = &LANG;
	const char *lines[] = {
		l->help_nav,        l->help_arrows,     l->help_coarse,
		l->help_fine,       l->help_toggle,     l->help_cycle,
		l->help_tab,        l->help_edit,       l->help_log,
		l->help_dev,        l->help_apply,      l->help_save,
		l->help_read,       l->help_gain,       l->help_filter,
		l->help_connect,
		l->help_presets,    l->help_psave,      l->help_pload,
		l->help_pdel,
		l->help_other,      l->help_reset_flat, l->help_reset_def,
		l->help_quit,
	};
	int n = (int)(sizeof(lines) / sizeof(lines[0]));
	static const int hdr[] = { 0, 9, 16, 20 };
	int nh = (int)(sizeof(hdr) / sizeof(hdr[0]));
	int h = LINES - 2;
	int w = COLS - 2;
	int top = 0, vis, ch;

	if (h < 8) h = 8;
	if (w < 44) w = 44;
	if (h > LINES - 1) h = LINES - 1;

	WINDOW *win = newwin(h, w, 1, 1);
	keypad(win, TRUE);
	vis = h - 2;
	if (vis < 1) vis = 1;

	while (1) {
		werase(win);
		box(win, 0, 0);
		mvwaddstr(win, 0, 2, l->title);
		mvwaddstr(win, 0, w - 14, "q: close");
		for (int i = 0; i < vis && top + i < n; i++) {
			int idx = top + i;
			int is_hdr = 0;
			for (int k = 0; k < nh; k++)
				if (hdr[k] == idx) { is_hdr = 1; break; }
			if (is_hdr) wattron(win, A_UNDERLINE);
			mvwaddstr(win, 1 + i, 2, lines[idx]);
			if (is_hdr) wattroff(win, A_UNDERLINE);
		}
		int last = top + vis; if (last > n) last = n;
		mvwprintw(win, h - 1, 2,
			"[%d-%d/%d]  Up/Down: scroll   PgUp/PgDn   Home/End   q: close",
			top + 1, last, n);
		wnoutrefresh(win);
		doupdate();

		ch = wgetch(win);
		if (ch == 'q' || ch == 'Q' || ch == 27)
			break;
		else if (ch == KEY_UP || ch == 'k') {
			if (top > 0) top--;
		} else if (ch == KEY_DOWN || ch == 'j') {
			if (top + vis < n) top++;
		} else if (ch == KEY_PPAGE || ch == 'b') {
			top -= vis; if (top < 0) top = 0;
		} else if (ch == KEY_NPAGE || ch == ' ') {
			top += vis; if (top >= n) top = n - 1;
		} else if (ch == KEY_HOME) {
			top = 0;
		} else if (ch == KEY_END) {
			top = n - vis; if (top < 0) top = 0;
		}
	}
	delwin(win);
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
		{l->help_tab,       false},
		{l->help_edit,      false},
		{l->help_log,       false},
		{l->help_dev,       true},
		{l->help_apply,     false},
		{l->help_save,      false},
		{l->help_read,      false},
		{l->help_gain,      false},
		{l->help_filter,    false},
		{l->help_connect,   false},
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
	/* Always clear the whole line first so a short message never leaves
	 * the tail of a previous (longer) one on screen. */
	mvwhline(win, row, 0, ' ', getmaxx(win));
	if (status_msg[0])
		mvwaddstr(win, row, 2, status_msg);
	status_msg[0] = 0;
}

/* Adjust the current cell by dir (+1 increase, -1 decrease).
 * Handles every column: Freq, Gain, Q, Type (cycle) and Status (toggle). */
static void adjust_param(int dir)
{
	Band *b = &bands[current_band];

	switch (current_param) {
	case 0: /* Freq */
		b->freq += dir * 10.0;
		if (b->freq > FREQ_MAX) b->freq = FREQ_MAX;
		if (b->freq < FREQ_MIN) b->freq = FREQ_MIN;
		break;
	case 1: /* Gain */
		b->gain += dir * 1.0;
		if (b->gain > GAIN_MAX) b->gain = GAIN_MAX;
		if (b->gain < GAIN_MIN) b->gain = GAIN_MIN;
		break;
	case 2: /* Q */
		b->q += dir * 0.1;
		if (b->q > Q_MAX) b->q = Q_MAX;
		if (b->q < Q_MIN) b->q = Q_MIN;
		break;
	case 3: /* Type */
		b->filter_type = (b->filter_type + dir + 3) % 3;
		break;
	case 4: /* Status */
		b->enabled = !b->enabled;
		break;
	default:
		break;
	}
	modified = true;
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

	int mrows = getmaxy(main_win);
	int winw  = getmaxx(main_win);
	int table_h = NUM_BANDS + 2;
	int msg_row = mrows - 1;
	int help_row;
	int help_h = 0;
	int bar_h = 12;

	/* Give the response-curve graph as much height as the terminal allows
	 * (up to 16 rows, like the Python TUI); the leftover space goes to the
	 * inline help panel. */
	{
		int avail = msg_row - (1 + table_h) - 1;   /* rows for bar+help */
		if (avail >= 28)      { bar_h = 16; help_h = avail - bar_h; }
		else if (avail >= 22) { bar_h = 14; help_h = avail - bar_h; }
		else if (avail >= 20) { bar_h = 12; help_h = avail - bar_h; }
		else                  { bar_h = avail; help_h = 0; }
		if (bar_h < 8) bar_h = 8;
		if (bar_h > 16) bar_h = 16;
		if (help_h > 24) help_h = 24;
		if (help_h < 10) help_h = 0;
	}
	help_row = 1 + table_h + bar_h;
	if (help_h > 0 && help_row + help_h > msg_row)
		help_h = msg_row - help_row;
	if (help_h < 10) help_h = 0;

	/* All windows are as wide as the terminal so the graph spans the full
	 * width (no fixed 80-column window). */
	WINDOW *table_win = derwin(main_win, table_h, winw, 1, 0);
	WINDOW *bar_win   = derwin(main_win, bar_h, winw, 1 + table_h, 0);
	WINDOW *help_win  = help_h > 0 ? derwin(main_win, help_h, winw, help_row, 0) : NULL;
	WINDOW *status_win= derwin(main_win, 1, winw, 0, 0);
	WINDOW *msg_win   = derwin(main_win, 1, winw, msg_row, 0);

	/* Force a full redraw of every window (e.g. after an overlapping
	 * popup/help/log window is closed, so no residue stays behind). */
#define TOUCH_ALL_WINDOWS \
	do { \
		touchwin(main_win); \
		touchwin(table_win); \
		touchwin(bar_win); \
		if (help_win) touchwin(help_win); \
		touchwin(status_win); \
		touchwin(msg_win); \
	} while (0)

	wclear(main_win);

	while (1) {
		getmaxyx(main_win, height, width);

		/* Status bar (doubles as an editable strip when in_strip) */
		draw_status_bar(status_win, width, in_strip, strip_param);

		/* Headers */
		draw_table_headers(table_win, width);

		/* Band rows */
		for (int i = 0; i < NUM_BANDS; i++)
			draw_band_row(table_win, i + 1, i, (i == current_band),
			              current_param);

		/* Bar chart */
		draw_response_curve(bar_win, 0, width);

		/* Help */
		if (help_win)
			draw_help(help_win, 0, help_h);
		else if (help_row < msg_row)
			mvwaddstr(main_win, help_row, 2, "Press ? or h for full help");

		/* Status message */
		draw_status_message(msg_win, 0);

		wnoutrefresh(main_win);
		wnoutrefresh(status_win);
		wnoutrefresh(table_win);
		wnoutrefresh(bar_win);
		if (help_win)
			wnoutrefresh(help_win);
		wmove(main_win, current_band + 1, cell_col(current_param));
		wnoutrefresh(msg_win);
		doupdate();

		ch = wgetch(main_win);

		/* Quit handling: with unapplied changes the first q warns and a
		 * second consecutive q confirms. Any other key resets the
		 * confirmation. */
		if ((ch == 'q' || ch == 'Q') && modified) {
			if (quitting)
				goto exit_loop;
			quitting = true;
			set_status("%s", l->modified_warn);
			continue;
		}
		if (ch == 'q' || ch == 'Q')
			goto exit_loop;
		quitting = false;

		/* "Strip" editing of the status-bar values (global gain / DAC
		 * filter). Handled keys are consumed here; everything else falls
		 * through to the normal key handling below. */
		if (in_strip) {
			bool strip_handled = true;
			switch (ch) {
			case KEY_DOWN:
				in_strip = false;
				current_band = 0;
				break;
			case KEY_UP:
				break;                     /* stay in strip */
			case KEY_LEFT:
				if (strip_param > 0) strip_param--;
				break;
			case KEY_RIGHT:
				if (strip_param < 1) strip_param++;
				break;
			case '\t':
			case KEY_BTAB:
				strip_param = (strip_param == 0) ? 1 : 0;
				break;
			case '\n':
			case '\r':
			case KEY_ENTER:
				edit_strip();
				TOUCH_ALL_WINDOWS;
				break;
			case '+':
			case '=':
				adjust_strip(1);
				break;
			case '-':
			case '_':
				adjust_strip(-1);
				break;
			case '>':
			case '.':
			case KEY_NPAGE:
				adjust_strip(1);
				break;
			case '<':
			case ',':
			case KEY_PPAGE:
				adjust_strip(-1);
				break;
			case 'f':
			case 'F':
			case 't':
			case 'T':
				strip_param = 1;
				cycle_dac_filter();
				break;
			case 'e':
			case 'E':
				edit_strip();
				TOUCH_ALL_WINDOWS;
				break;
			default:
				strip_handled = false;
				break;
			}
			if (strip_handled)
				continue;
		}

		switch (ch) {
		case '?':
		case 'h':
		case 'H':
show_full_help();
			/* The help window overlaps the whole screen; force a full
			 * redraw of every window so no residue stays behind. */
			touchwin(main_win);
			touchwin(table_win);
			touchwin(bar_win);
			if (help_win) touchwin(help_win);
			touchwin(status_win);
			touchwin(msg_win);
			break;

		case 'l':
		case 'L':
			show_log_screen();
			/* The log window overlaps the whole screen; force a full
			 * redraw of every window so no residue stays behind. */
			touchwin(main_win);
			touchwin(table_win);
			touchwin(bar_win);
			if (help_win) touchwin(help_win);
			touchwin(status_win);
			touchwin(msg_win);
			break;

		case 'e':
		case 'E':
			edit_current_cell();
			TOUCH_ALL_WINDOWS;
			break;

		case '\n':
		case '\r':
		case KEY_ENTER:
			/* Enter opens the popup on the current value (like 'e');
			 * on Type/Status it cycles/toggles the cell. */
			if (current_param == 3) {
				bands[current_band].filter_type =
					(bands[current_band].filter_type + 1) % 3;
				modified = true;
			} else if (current_param == 4) {
				bands[current_band].enabled =
					!bands[current_band].enabled;
				modified = true;
			} else {
				edit_current_cell();
				TOUCH_ALL_WINDOWS;
			}
			break;

		case KEY_LEFT:
			if (current_param > 0) current_param--;
			break;
		case KEY_RIGHT:
			if (current_param < NUM_PARAMS - 1) current_param++;
			break;
		case KEY_UP:
			if (current_band > 0)
				current_band--;
			else {
				in_strip = true;   /* up from band 1 -> strip */
				strip_param = 0;
			}
			break;
		case KEY_DOWN:
			if (current_band < NUM_BANDS - 1) current_band++;
			break;

		case '\t': /* Tab: move forward across all cells */
			if (current_param < NUM_PARAMS - 1)
				current_param++;
			else {
				current_param = 0;
				current_band = (current_band + 1) % NUM_BANDS;
			}
			break;
		case KEY_BTAB: /* Shift+Tab: move backward across all cells */
			if (current_param > 0)
				current_param--;
			else {
				current_param = NUM_PARAMS - 1;
				current_band = (current_band - 1 + NUM_BANDS) % NUM_BANDS;
			}
			break;

		case '+':
		case '=':
			adjust_param(1);
			break;

		case '-':
		case '_':
			adjust_param(-1);
			break;

		case '>':
		case '.':
		case KEY_NPAGE:
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
		case KEY_PPAGE:
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

		case 'c':
		case 'C':
		{
			int sel;
			/* Disconnect current device (if any) */
			disconnect_device();
			enumerate_devices();
			if (num_devices == 0) {
				set_status("%s", l->msg_no_device);
				break;
			}
			sel = select_device_menu();
			if (sel < 0) {
				set_status("%s", l->msg_cancelled);
				break;
			}
			if (connect_to_entry(&devices[sel]))
				set_status("%s", l->status_conn);
			else
				set_status("%s", l->msg_no_device);
			break;
		}

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
			double v = global_gain;
			if (edit_numeric(&v, GLOBAL_GAIN_MIN, GLOBAL_GAIN_MAX, 1,
			                 l->edit_title_ggain)) {
				apply_global_gain(v);
			} else {
				set_status("%s", l->msg_cancelled);
			}
			touchwin(main_win);
			touchwin(table_win);
			touchwin(bar_win);
			if (help_win) touchwin(help_win);
			touchwin(status_win);
			touchwin(msg_win);
			break;
		}

		case 'f':
		case 'F':
			cycle_dac_filter();
			break;

		case 'p':
		{
			char pname[64];
			int r = show_preset_list(current_preset, true);
			if (r == -1) {          /* Esc: cancel entirely */
				set_status("%s", l->msg_cancelled);
				TOUCH_ALL_WINDOWS;
				break;
			}
			/* Enter or 'q' on the list: show the name prompt */
			pname[0] = 0;
			if (edit_text(pname, sizeof(pname), l->msg_prompt_pname)) {
				save_current_preset(pname);
				save_presets();
				set_status(l->msg_preset_saved, pname);
			} else {
				set_status("%s", l->msg_cancelled);
			}
			TOUCH_ALL_WINDOWS;
			break;
		}

		case 'P':
		{
			int r = show_preset_list(current_preset, false);
			if (r >= 0 && r < num_presets) {
				load_preset(r);
				set_status(l->msg_preset_loaded, presets[r].name);
			} else {
				set_status("%s", l->msg_cancelled);
			}
			TOUCH_ALL_WINDOWS;
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
	if (help_win) delwin(help_win);
	delwin(status_win);
	if (msg_win) delwin(msg_win);
	save_presets();
}

/* ============================================================
 * Entry point
 * ============================================================ */
/* Non-interactive report mode: print the device configuration as plain
 * text to stdout without touching ncurses.
 * Usage: ja11-config-tui --report */
static int run_report_mode(void)
{
	init_default_bands();
	if (hid_init() != 0) {
		fprintf(stderr, "Failed to initialize hidapi\n");
		return 1;
	}
	enumerate_devices();
	int sel = -1;
	for (int i = 0; i < num_devices; i++)
		if (devices[i].compatible) { sel = i; break; }
	if (sel < 0) {
		fprintf(stderr, "No compatible HID device found.\n");
		hid_exit();
		return 1;
	}
	if (!connect_to_entry(&devices[sel])) {
		fprintf(stderr, "Failed to open device.\n");
		hid_exit();
		return 1;
	}
	read_device_config();
	printf("FiiO JA11 (KT02H20) - configuration report\n");
	printf("Device: %s (%04X:%04X)\n", device_name, device_vid, device_pid);
	printf("Global Preamp: %.1f dB\n", global_gain);
	printf("DAC Digital Filter: %s\n", dac_filter_name(dac_filter));
	printf("\n%-5s %7s %-7s %5s  %-5s %s\n",
		"Band", "Freq(Hz)", "Gain(dB)", "Q", "Type", "Status");
	for (int i = 0; i < NUM_BANDS; i++) {
		printf("%-6d %7.0f %+7.1f %6.2f  %-5s %s\n",
			i + 1,
			bands[i].freq,
			bands[i].gain,
			bands[i].q,
			filter_type_name(bands[i].filter_type),
			bands[i].enabled ? "ON" : "OFF");
	}
	disconnect_device();
	return 0;
}

int main(int argc, char *argv[])
{
	const Lang *l;

	/* Parse command line */
	for (int i = 1; i < argc; i++) {
		if (!strcmp(argv[i], "--english") || !strcmp(argv[i], "-en"))
			g_lang = LANG_EN;
		else if (!strcmp(argv[i], "--italian") || !strcmp(argv[i], "-it"))
			g_lang = LANG_IT;
		else if (!strcmp(argv[i], "--french") || !strcmp(argv[i], "-fr"))
			g_lang = LANG_FR;
		else if (!strcmp(argv[i], "--german") || !strcmp(argv[i], "-de"))
			g_lang = LANG_DE;
		else if (!strcmp(argv[i], "--spanish") || !strcmp(argv[i], "-es"))
			g_lang = LANG_ES;
		else if ((!strcmp(argv[i], "--presets") ||
		          !strcmp(argv[i], "--preset-file")) && i + 1 < argc) {
			strncpy(preset_file, argv[++i], sizeof(preset_file) - 1);
			preset_file[sizeof(preset_file) - 1] = 0;
		}
		else if (!strcmp(argv[i], "--report"))
			return run_report_mode();
		else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
			printf("Usage: %s [--english|-en] [--italian|-it] [--french|-fr] [--german|-de] [--spanish|-es] [--presets <path>] [--report]\n", argv[0]);
			printf("  --english, -en    UI in English (default)\n");
			printf("  --italian, -it    UI in Italian\n");
			printf("  --french, -fr     UI in French\n");
			printf("  --german, -de     UI in German\n");
			printf("  --spanish, -es    UI in Spanish\n");
			printf("  --presets <path>  Preset file path (default: %s)\n",
			       PRESET_FILE_DEFAULT);
			printf("  --report          Print device configuration report and exit (no TUI)\n");
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

	/* Enumerate HID devices and let the user pick one to connect to
	 * (libusb backend, like hidws) */
	enumerate_devices();
	if (num_devices > 0) {
		int sel = select_device_menu();
		if (sel < 0) {
			/* User cancelled the picker: clean exit */
			disconnect_device();
			delwin(main_win);
			endwin();
			return 0;
		}
		if (!connect_to_entry(&devices[sel])) {
			mvaddstr(LINES - 1, 2, l->msg_no_device);
			mvaddstr(LINES - 0, 2, l->msg_udev_hint);
			refresh();
		}
	} else {
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
