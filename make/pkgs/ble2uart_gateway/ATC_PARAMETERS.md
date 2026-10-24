# ATC_MiThermometer: parametri, comandi GATT e patch

Per le revisioni necessarie del modulo Python e dei tracciati generati,
vedere l'analisi separata [ATC_CONSTRUCT_REVIEW.md](ATC_CONSTRUCT_REVIEW.md),
inclusa la distinzione fra protocollo Xiaomi nativo e protocollo ATC.

## Indice

* [Fonti e ambito](#1-ambito-e-fonti)
* [Modelli di richiesta CLI/CGI](#2-come-leggere-ed-eseguire-gli-esempi)
* [Configurazione principale e tutti i bit](#3-0x55-configurazione-principale)
* [Comfort](#4-comfort-0x20)
* [Trigger e reed](#5-trigger-e-ingressi-reed-0x44-0x45)
* [Layout corrente, nuovi parametri e default](#6-configurazione-corrente-flg3-eventi-e-layout-intero)
* [Calibrazione e famiglie sensori](#7-calibrazione-sensori-e-coefficienti)
* [Orologio e storico](#8-orologio-drift-e-storico)
* [Nome, MAC, chiavi e PIN](#9-nome-mac-chiavi-e-sicurezza)
* [Display](#10-display-esterno-buffer-e-notifiche)
* [Scansione periodica del sensore](#11-scansione-periodica-del-sensore-0x21)
* [Inventario completo degli ID](#12-inventario-degli-id-configurazione-azioni-e-sola-lettura)
* [Persistenza e incompatibilita' riscontrate](#13-persistenza-riavvio-risposte-e-differenze-importanti)
* [Schemi esterni di esempio](#14-appendice-schemi-esterni-di-esempio-senza-conversioni-lossy)
* [Riferimenti puntuali e verifiche](#15-riferimenti-puntuali-e-verifiche)

## 1. Ambito e fonti

Questo riferimento riguarda il protocollo applicativo del firmware **Telink
ATC_MiThermometer**, sulla caratteristica `00001f1f-0000-1000-8000-00805f9b34fb`,
e il suo uso attraverso `ble2uart-gateway`. Non e' un protocollo universale
per tutti i termometri Xiaomi, ne' per tutti i dispositivi elencati dal flasher.
Il flasher gestisce anche firmware originali, dispositivi Zigbee e altri
protocolli: la presenza di un controllo nella pagina non prova il supporto
nel binario installato.

Fonti consultate il **21 ottobre 2026**, fissate per rendere riproducibile
l'analisi:

* **C**: [pvvx/ATC_MiThermometer,
  b6b4c7bde322adc7538f1ec10fb32160a00df811](https://github.com/pvvx/ATC_MiThermometer/tree/b6b4c7bde322adc7538f1ec10fb32160a00df811).
* **JavaScript/HTML**:
  [TelinkMiFlasher.html, 9b588885f24be8e9d61adbd2e37ef04eaf7bf402](https://github.com/pvvx/pvvx.github.io/blob/9b588885f24be8e9d61adbd2e37ef04eaf7bf402/ATC_MiThermometer/TelinkMiFlasher.html).
  La copia pubblicata su
  [pvvx.github.io](https://pvvx.github.io/ATC_MiThermometer/TelinkMiFlasher.html)
  era identica byte per byte; SHA-256
  `3c87b641a8a698d22bb03c9aff55c8f80c28dd226f14a4a0142ec27319fe5d94`.
* **Python di confronto**, non autorita' per firmware piu' recenti:
  [atc_mi_config.py](https://github.com/Ircama/ATC_MiThermometer/blob/cb06199ac462bb233849a18b5fc793edebe45220/python-interface/atc_mi_interface/atc_mi_config.py)
  e [atc_mi_construct.py](https://github.com/Ircama/ATC_MiThermometer/blob/cb06199ac462bb233849a18b5fc793edebe45220/python-interface/atc_mi_interface/atc_mi_construct.py).
* **Gateway effettivo**: [schema incorporato](src/spec/codec.yaml),
  [motore GATT](src/src/gatt.rs) e [API CLI/CGI](src/README.md#persistent-sessions-and-atc-configuration).

Le tabelle separano tre cose diverse:

1. il significato sul filo stabilito dal C;
2. le conversioni, limitazioni e scelte di interfaccia del JavaScript;
3. i nomi e i limiti dello schema attualmente incorporato nel gateway.

**Avvertenza principale:** `codec: "cfg"` e' uno schema storico, non un
riconoscitore automatico delle versioni. Da ATC **4.7** i vecchi offset di
temperatura/umidita' non sono piu' quei parametri; da **4.8** cambia anche
l'identificazione hardware. Una decodifica senza errori non prova che i nomi
dei campi descrivano correttamente il firmware corrente.

## 2. Come leggere ed eseguire gli esempi

### 2.1 L'involucro JSON non e' la configurazione del sensore

| Parametro del gateway | Significato |
|---|---|
| `command: "gatt"` | Richiesta al daemon, non byte ATC |
| `mac` | Peer per una transazione con apertura/chiusura automatiche |
| `session` | Alternativa a `mac`: token di una connessione gia' aperta |
| `uuid: "1F1F"` | Caratteristica di comando del firmware ATC |
| `operation: "exchange"` | Sottoscrive, scrive, attende la notifica applicativa |
| `operation: "patch"` | Legge, decodifica, modifica, ricodifica e verifica la risposta |
| `value` | Richiesta iniziale in esadecimale, per esempio `"55"` |
| `prefix` | Prefisso esadecimale delle notifiche attese, non dell'UUID |
| `codec` | Nome di una struttura dello schema caricato nel daemon |
| `offset` | Byte iniziali da scartare dalla notifica prima della decodifica |
| `write_offset` | Byte iniziali della struttura codificata da non trasmettere |
| `write_prefix` | Prefisso del commit; se omesso, coincide con `value` |
| `patch` | Solo campi gia' presenti nella struttura decodificata |
| `coded` | PHY usato per **connettersi**, non abilita il Coded nel sensore |
| `timeout_ms` | Budget dell'operazione; 100..30000 ms, non un tempo di persistenza |

Il servizio deve essere attivo: si usa la sua connessione seriale, non si avvia
un secondo lettore UART. SCAN e TX ADV gestiti dal daemon sono sospesi e poi
ripristinati; una sessione aperta mantiene la sospensione fino alla chiusura.
Un TX ADV esterno di cui il daemon non conosce il payload non puo' essere
temporaneamente ripristinato in sicurezza: l'apertura viene rifiutata.
I pacchetti trasmessi da altri sensori durante la pausa non sono recuperabili.

### 2.2 Modello completo per tutte le patch `cfg` storiche

```sh
ble2uart-gateway --command '{
  "command":"gatt",
  "mac":"AA:BB:CC:DD:EE:FF",
  "operation":"patch",
  "uuid":"1F1F",
  "value":"55",
  "prefix":"55",
  "codec":"cfg",
  "offset":1,
  "write_offset":1,
  "patch":{"flg2":{"bt5phy":true,"longrange":true}}
}'
```

Nelle tabelle, la colonna **Patch** contiene il valore da sostituire al membro
`patch`, non un JSON completo da passare direttamente a `--command`.
Gli esempi cambiano un solo parametro salvo esplicita indicazione.
Non eseguire tutte le righe in sequenza: sono esempi alternativi.

Risposta `0x55`: `55 VERSIONE CFG[11]`. Scrittura: `55 CFG[11]`.
`offset:1` toglie `55`; `write_offset:1` toglie la versione, **non** il primo
flag. La proprieta' JSON `version:1` del codec e' invece metadato virtuale:
non consuma byte. `firmware_version` e' la versione realmente ricevuta.

Il gateway pretende un roundtrip byte-esatto **prima** di scrivere. Rifiuta
campi inesistenti, tipi errati, lunghezze incompatibili, modifiche a byte
omessi e trasformazioni non rappresentabili. Questo protegge la forma binaria,
ma non conosce i vincoli semantici del C e non riconosce un campo rinominato.
Se la verifica **dopo** la scrittura fallisce, il sensore potrebbe essere gia'
stato modificato: rileggere, non riprovare automaticamente.

Per la CGI si usano gli stessi parametri nella scheda Commands; il pulsante ATC
usa `cfg`. Le altre famiglie richiedono i controlli GATT generici e lo schema
corretto. Gli editor Ace non convertono automaticamente tra layout/versioni.

### 2.3 Lettura prima di qualsiasi modifica

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"00","prefix":"00"}'
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"55","prefix":"55"}'
```

Salvare privatamente risposta raw, modello, versione e configurazione iniziale.
`00` e' disponibile solo nei firmware che implementano l'identificazione
estesa: un timeout su vecchi firmware non equivale a un guasto di `55`.
Non pubblicare risposte contenenti chiavi o PIN.

## 3. `0x55`: configurazione principale

### 3.1 Layout e compatibilita'

Gli indici seguenti partono dal primo byte di `CFG`, **dopo** comando e versione
nella risposta e dopo il solo comando nella scrittura.

| Byte CFG | Campo storico incorporato | Evoluzione da verificare sul modello |
|---|---|---|
| 0 | `flg` | Bit di advertising e comportamento; alcuni bit LCD cambiano significato |
| 1 | `flg2` | Smiley/modo LCD, cifratura, flags ADV, PHY, schermo |
| 2 | `temp_offset` | Prima di 4.7: offset; firmware nuovi: `flg3`, non un offset |
| 3 | `humi_offset` | Prima di 4.7: offset; firmware nuovi: conteggio ADV evento |
| 4 | `advertising_interval` | Unita' raw 62.5 ms |
| 5 | `measure_interval` | Moltiplicatore dell'intervallo ADV |
| 6 | `rf_tx_power` | Codice di tabella radio, non dBm numerico |
| 7 | `connect_latency` | Latenza periferica; codec espone `(raw+1)*0.02` secondi |
| 8 | `min_step_time_update_lcd` | LCD: unita' 50 ms; alcuni layout vecchi lo riusano come ID esteso |
| 9 | `hw_cfg` | Informazione hardware; da 4.8 ID intero, non vecchi bitfield |
| 10 | `averaging_measurements` | Numero misure da mediare per il logger; 0 disabilita |

Non scrivere un profilo completo di un altro dispositivo: `hw_cfg` non e' una
selezione del modello da parte dell'utente. Le vecchie risposte piu' corte
non sono compatibili con la struttura incorporata da 12 byte.

### 3.2 `flg`: ogni parametro e relativo esempio

Per un LYWSD03MMC con layout classico:

| Bit | Campo `cfg` | Effetto/valori | Patch |
|---|---|---|---|
| 0..1 | `flg.advertising_type` | 0 ATC1441, 1 PVVX, 2 MI, 3 HA/BTHome secondo versione | `{"flg":{"advertising_type":"adv_type_custom"}}` |
| 2 | `flg.comfort_smiley` | Smiley automatico usando soglie comfort, se LCD disponibile | `{"flg":{"comfort_smiley":true}}` |
| 3 | `flg.blinking_time_smile` | Alternanza orologio/smiley, non selettore universale del display | `{"flg":{"blinking_time_smile":"blinking_time"}}` |
| 4 | `flg.temp_F_or_C` | Unita' **visualizzata**; non cambia le unita' dei dati GATT/ADV | `{"flg":{"temp_F_or_C":"temp_F"}}` |
| 5 | `flg.show_batt_enabled` | Mostra batteria sul display | `{"flg":{"show_batt_enabled":true}}` |
| 6 | `flg.tx_measures` | Abilita trasferimento misure nelle connessioni successive | `{"flg":{"tx_measures":true}}` |
| 7 | `flg.lp_measures` | Modalita' misura a basso consumo, secondo sensore compilato | `{"flg":{"lp_measures":true}}` |

Tutti i valori dell'enum advertising:

```json
{"flg":{"advertising_type":"adv_type_atc1441"}}
```
```json
{"flg":{"advertising_type":"adv_type_custom"}}
```
```json
{"flg":{"advertising_type":"adv_type_mi"}}
```
```json
{"flg":{"advertising_type":"adv_type_ha_ble"}}
```

Il nome storico `adv_type_ha_ble` non identifica una versione BTHome:
il flasher distingue HA su vecchie versioni, BTHome v1 da 3.7 e BTHome v2
da 4.5. Alcuni dispositivi senza LCD anteriori a 4.8 usano una mappatura
diversa (0 BTHome v2, 3 BTHome v1). Il formato deve coincidere con quello
supportato dal binario e dal ricevitore.

Gli altri valori degli enum LCD sono `blinking_smile` e `temp_C`.
Per disabilitare un booleano sostituire `true` con `false`.

**Alias hardware, non nuovi bit:**

| Hardware nel flasher | Differenza rispetto ai nomi storici | Esempio con `cfg` e sua interpretazione reale |
|---|---|---|
| MJWSD05MMC (9), MJWSD05MMC_EN (12) | Bit 3 = due decimali T/H | `{"flg":{"blinking_time_smile":"blinking_time"}}` imposta due decimali, **non** l'orologio |
| Stessi modelli | Bit 5 = orologio 12 ore | `{"flg":{"show_batt_enabled":true}}` abilita 12 ore, **non** la batteria |
| Hardware 49 | Bit 3 = batteria, bit 5 = 12 ore | Le stesse due patch abilitano rispettivamente batteria e 12 ore |

Questi alias servono a spiegare il filo; per automazioni preferire un codec
dedicato con nomi non ambigui. Non estendere gli alias ad altri modelli.

### 3.3 `flg2`: ogni parametro e relativo esempio

| Bit | Campo `cfg` | Significato | Patch |
|---|---|---|---|
| 0..2 | `flg2.smiley` | Simbolo manuale; comfort automatico puo' sostituirlo | `{"flg2":{"smiley":"smiley_p_happy"}}` |
| 3 | `flg2.adv_crypto` | Cifratura beacon con bindkey; predisporre prima la chiave nel ricevitore | `{"flg2":{"adv_crypto":true}}` |
| 4 | `flg2.adv_flags` | Inserisce AD Flags per compatibilita' ricevitori | `{"flg2":{"adv_flags":true}}` |
| 5 | `flg2.bt5phy` | Supporto PHY BLE5, non una misura della PHY effettivamente negoziata | `{"flg2":{"bt5phy":true}}` |
| 6 | `flg2.longrange` | Extended advertising Coded S8 nei firmware compatibili >=4.2 | `{"flg2":{"bt5phy":true,"longrange":true}}` |
| 7 | `flg2.screen_off` | Schermo spento, esposto dal flasher da 4.3; non spegne la radio | `{"flg2":{"screen_off":true}}` |

Enum smiley completo:

| Valore raw | Patch |
|---|---|
| 0 | `{"flg2":{"smiley":"smiley_off"}}` |
| 1 | `{"flg2":{"smiley":"smiley_happy"}}` |
| 2 | `{"flg2":{"smiley":"smiley_sad"}}` |
| 3 | `{"flg2":{"smiley":"smiley_ooo"}}` |
| 4 | `{"flg2":{"smiley":"smiley_p_off"}}` |
| 5 | `{"flg2":{"smiley":"smiley_p_happy"}}` |
| 6 | `{"flg2":{"smiley":"smiley_p_sad"}}` |
| 7 | `{"flg2":{"smiley":"smiley_p_ooo"}}` |

CGG1/CGDK2 possono usare il selettore per una linea invece dello smiley.
Sugli hardware 9/12 i valori 0..5 selezionano rispettivamente orologio,
temperatura, umidita', batteria %, batteria V e numero esterno:
per esempio `{"flg2":{"smiley":"smiley_sad"}}` scrive 2 e seleziona
**umidita'**, non una faccina triste.

Versioni storiche: bit 3 in 1.9 indicava registrazione flash, non cifratura;
bit 6 prima di 4.0 poteva indicare CSA2, mentre il controllo Long Range
compare da 4.2. Non abilitare Coded con una versione piu' vecchia basandosi
solo sul nome del codec.

### 3.4 Campi scalari storici

| Campo | Unita'/limite del codec e uso | Patch |
|---|---|---|
| `temp_offset` | Passi 0.1 °C, int8; flasher limita a -12.7..12.7; solo prima di 4.7 | `{"temp_offset":0.5}` |
| `humi_offset` | Passi 0.1 punti %RH, int8; stesso limite; solo prima di 4.7 | `{"humi_offset":1.0}` |
| `advertising_interval` | Secondi, passo 0.0625; non confondere con millisecondi mostrati dal flasher | `{"advertising_interval":2.5}` |
| `measure_interval` | Moltiplicatore intero, non secondi; 4 con ADV 2.5 s significa circa 10 s | `{"measure_interval":4}` |
| `rf_tx_power` | Enum radio, vedi tabella seguente | `{"rf_tx_power":"RF_POWER_Positive_3p01_dBm"}` |
| `connect_latency` | Secondi nel codec; 1.0 corrisponde a raw 49; non intervallo ADV | `{"connect_latency":1.0}` |
| `min_step_time_update_lcd` | Secondi, passo 0.05; UI 0.5..12.75; non frequenza in Hz | `{"min_step_time_update_lcd":2.5}` |
| `averaging_measurements` | 0..255; 0 spegne logger, 60 media 60 misure | `{"averaging_measurements":60}` |

Con ADV 2.5 s, moltiplicatore 4 e media 60 si registra approssimativamente
una media ogni 600 s. Il tempo reale include scheduling e, con Coded,
vincoli radio: non e' una garanzia metrologica di periodicita'.

`connect_latency` usa conversioni float con troncamento nell'encoder:
alcuni valori decodificati non ricodificano byte-esattamente. Il gateway
puo' quindi rifiutare anche una patch di un altro campo. Non disabilitare
la protezione: usare il layout intero dell'appendice, compatibile col firmware.

Anche il segno richiede attenzione nel codec attuale: nella prova offline
un offset H richiesto di -1.0 produce il byte `F6`, ma la decodifica nativa
lo riporta come 24.6 anziche' -1.0. La verifica patch lo rifiuta.
I valori negativi ammessi dal C non sono quindi tutti utilizzabili
tramite il codec incorporato corrente. Non confondere questo limite
del decoder con un intervallo ammesso dal firmware; per un commit raw
consapevole l'int8 -10 si rappresenta comunque come `F6`.

### 3.5 Potenza RF: catalogo completo del codec

Ogni nome seguente e' il valore stringa del membro `rf_tx_power`.
Per ciascuno l'esempio di patch e'
`{"rf_tx_power":"NOME_DELLA_RIGA"}`. La potenza nominale non equivale
alla potenza irradiata misurata; antenna, alimentazione e modello contano.

| Raw | Nome | Raw | Nome |
|---|---|---|---|
| 63 | `RF_POWER_Positive_10p46_dBm` | 191 | `RF_POWER_Positive_3p01_dBm` |
| 61 | `RF_POWER_Positive_10p29_dBm` | 189 | `RF_POWER_Positive_2p81_dBm` |
| 58 | `RF_POWER_Positive_10p01_dBm` | 187 | `RF_POWER_Positive_2p61_dBm` |
| 56 | `RF_POWER_Positive_9p81_dBm` | 185 | `RF_POWER_Positive_2p39_dBm` |
| 53 | `RF_POWER_Positive_9p48_dBm` | 182 | `RF_POWER_Positive_1p99_dBm` |
| 51 | `RF_POWER_Positive_9p24_dBm` | 180 | `RF_POWER_Positive_1p73_dBm` |
| 49 | `RF_POWER_Positive_8p97_dBm` | 178 | `RF_POWER_Positive_1p45_dBm` |
| 47 | `RF_POWER_Positive_8p73_dBm` | 176 | `RF_POWER_Positive_1p17_dBm` |
| 45 | `RF_POWER_Positive_8p44_dBm` | 174 | `RF_POWER_Positive_0p90_dBm` |
| 43 | `RF_POWER_Positive_8p13_dBm` | 172 | `RF_POWER_Positive_0p58_dBm` |
| 41 | `RF_POWER_Positive_7p79_dBm` | 169 | `RF_POWER_Positive_0p04_dBm` |
| 39 | `RF_POWER_Positive_7p41_dBm` | 168 | `RF_POWER_Negative_0p14_dBm` |
| 37 | `RF_POWER_Positive_7p02_dBm` | 164 | `RF_POWER_Negative_0p97_dBm` |
| 35 | `RF_POWER_Positive_6p60_dBm` | 162 | `RF_POWER_Negative_1p42_dBm` |
| 33 | `RF_POWER_Positive_6p14_dBm` | 160 | `RF_POWER_Negative_1p89_dBm` |
| 31 | `RF_POWER_Positive_5p65_dBm` | 158 | `RF_POWER_Negative_2p48_dBm` |
| 29 | `RF_POWER_Positive_5p13_dBm` | 156 | `RF_POWER_Negative_3p03_dBm` |
| 27 | `RF_POWER_Positive_4p57_dBm` | 154 | `RF_POWER_Negative_3p61_dBm` |
| 25 | `RF_POWER_Positive_3p94_dBm` | 152 | `RF_POWER_Negative_4p26_dBm` |
| 23 | `RF_POWER_Positive_3p23_dBm` | 150 | `RF_POWER_Negative_5p03_dBm` |
| | | 148 | `RF_POWER_Negative_5p81_dBm` |
| | | 146 | `RF_POWER_Negative_6p67_dBm` |
| | | 144 | `RF_POWER_Negative_7p65_dBm` |
| | | 142 | `RF_POWER_Negative_8p65_dBm` |
| | | 140 | `RF_POWER_Negative_9p89_dBm` |
| | | 138 | `RF_POWER_Negative_11p4_dBm` |
| | | 136 | `RF_POWER_Negative_13p29_dBm` |
| | | 134 | `RF_POWER_Negative_15p88_dBm` |
| | | 132 | `RF_POWER_Negative_19p27_dBm` |
| | | 130 | `RF_POWER_Negative_25p18_dBm` |
| | | 255 | `RF_POWER_Negative_30_dBm` |
| | | 128 | `RF_POWER_Negative_50_dBm` |

I codici 128 e 255 sono presenti nel codec ma non nel selettore RF corrente
del flasher: non dedurne che siano configurazioni raccomandate o mantenute
dal validatore C.

### 3.6 Campi non configurabili tramite `cfg`

* `firmware_version.major/minor`: descrizione del firmware ricevuto;
  non aggiorna il firmware. Il gateway rifiuta la modifica del byte omesso.
* `hw_cfg.sensor`, `hw_cfg.hwver`, `hw_cfg.reserved`: identificazione hardware
  o bit riservati. Il sensore li puo' ricalcolare; **non** usarli per scegliere
  un altro sensore/modello.
* `version`, `temperature_unit`, `humidity_unit`, `adv_int_unit`,
  `connect_latency_unit`, `min_s_t_upd_lcd_unit`: metadati virtuali, non parametri
  trasmessi. La modifica non produce una patch valida.

Per questi campi non esiste un esempio legittimo di patch di configurazione.
Anche un campo tecnicamente scrivibile nel JSON non e' necessariamente
modificabile dal protocollo applicativo.

## 4. Comfort (`0x20`)

Struttura `comfort_values`, `offset:1`, `write_offset:0`, richiesta/prefisso
`20`. Quattro word LE: Tmin/Tmax int16 in centesimi °C, Hmin/Hmax uint16
in centesimi %RH. I valori sensati rispettano min <= max e 0..100 %RH;
la capacita' del tipo non e' un'autorizzazione a usare 655.35 %RH.

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"patch","uuid":"1F1F","value":"20","prefix":"20","codec":"comfort_values","offset":1,"patch":{"temperature_low":20.0,"temperature_high":26.0,"humidity_low":30.0,"humidity_high":60.0}}'
```

| Parametro | Patch individuale |
|---|---|
| Limite inferiore temperatura | `{"temperature_low":20.0}` |
| Limite superiore temperatura | `{"temperature_high":26.0}` |
| Limite inferiore umidita' | `{"humidity_low":30.0}` |
| Limite superiore umidita' | `{"humidity_high":60.0}` |

Per ottenere lo smiley automatico attivare anche
`{"flg":{"comfort_smiley":true}}` con il modello `55`, non con `20`.
`native_comfort_values` descrive un altro layout/protocollo: non sostituirlo
a `comfort_values` sulla caratteristica ATC.

## 5. Trigger e ingressi reed (`0x44`, `0x45`)

Il trigger e' una funzione **del sensore**, non il filtro Discovery del gateway.
Dipende dai GPIO e servizi inclusi nel binario; un LYWSD03MMC non acquisisce
un rele' solo perche' viene impostata una soglia.

Layout classico moderno della risposta: `44`, soglia T int16, soglia H int16,
isteresi T int16, isteresi H int16, intervallo report uint16, modi reed uint8,
stato uint8. T/H sono in centesimi. Il comando di configurazione contiene
i primi **11 byte** di dati, non il byte finale di stato.

Lo schema incorporato `trigger` richiede cautela:

* tratta soglia/isteresi H come **unsigned**, mentre C/JS consentono
  isteresi negativa;
* `reserved_for_types` occupa anche i bit del secondo reed nei modelli
  che lo implementano;
* `flg` e' stato runtime, non l'insieme delle impostazioni da persistere;
* il motore patch non dispone di `write_length`/ritaglio finale. Usare
  ciecamente `codec:"trigger"` rispedisce anche lo stato e puo' richiedere
  la conferma di campi che il firmware aggiorna autonomamente.

Per una modifica conservativa leggere `44`, preservare i campi non modificati e inviare
esplicitamente `44 + dati[0:11]` con `exchange`, quindi rileggere e confrontare.
Non esiste una patch incorporata sicura e generale per tutti i layout trigger.

| Parametro C | Unita'/effetto | Modifica desiderata, campi del layout intero |
|---|---|---|
| `temp_threshold` | Centesimi °C; esempio 21 °C | `{"temp_threshold_raw":2100}` |
| `humi_threshold` | Centesimi %RH; esempio 50 %RH | `{"humi_threshold_raw":5000}` |
| `temp_hysteresis` | 0 disabilita; negativa attiva su discesa, positiva su salita | `{"temp_hysteresis_raw":-55}` |
| `humi_hysteresis` | Stessa regola, centesimi %RH | `{"humi_hysteresis_raw":100}` |
| `rds_time_report` | Secondi, 0 off, 1..65535 | `{"rds_time_report":3600}` |
| RS1 modo, bit 0..1 | 0 nessuno, 1 switch, 2 contatore; 3 solo dove implementato | `{"rds_bits":1}` partendo dagli altri bit a zero |
| RS2 modo, bit 2..3 | Secondo reed solo sui modelli che lo includono | `{"rds_bits":4}` partendo dagli altri bit a zero |
| RS1 inversione, bit 4 | Inverte evento | `{"rds_bits":17}` = RS1 switch + inversione |
| RS2 inversione, bit 5 | Inverte secondo ingresso | `{"rds_bits":36}` = RS2 switch + inversione |

I frammenti di questa tabella descrivono la modifica del blocco, **non**
sono richieste `operation:"patch"` eseguibili con lo schema incorporato.
Per bit condivisi calcolare `(vecchio & ~maschera) | nuovo`: non azzerare
gli altri ingressi come negli esempi a base zero.

Esempio raw completo per soglie 21 °C / 50 %RH, isteresi -0.55 °C / 0 %RH,
report 3600 s, RS1 switch, altri bit zero:

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"4434088813C9FF0000100E01","prefix":"44"}'
```

Non e' una patch: sostituisce l'intero blocco specificato. Non usarlo come
profilo universale. I bit finali `rds_input`, `trg_output`, `trigger_on`,
`temp_out_on`, `humi_out_on` sono letture di stato, non soglie aggiuntive.

`45 + byte` controlla l'uscita trigger runtime; per esempio `4501`
richiede uscita attiva, `4500` inattiva. Risposta con prefisso **45**
e byte di stato, non `44`. L'automatismo a soglie puo' poi aggiornare
l'uscita. Il byte stato comprende anche `key_pressed` e `rds2_input`
nelle build che li usano; non e' salvato nella configurazione persistente.
`0x4A` non e' un comando di questo parser.

## 6. Configurazione corrente: `flg3`, eventi e layout intero

Nel C esaminato `VERSION=0x59` (5.9); la selezione
`VERSION < 0x47` distingue offset storici da `flg3/event_adv_cnt`.
Il flasher espone i controlli delay/conteggio solo per versione >5.0:
questa condizione della **UI** non va confusa con il layout del C corrente.

Lo schema di esempio `atc_cfg_wire` in appendice conserva i byte senza
conversioni float e usa `flg3` con nomi corretti. Deve essere caricato
**nel daemon che esegue il comando**, prima dell'uso: aggiungerlo solo a un
processo CLI di controllo non cambia lo schema del servizio gia' in esecuzione.
Pianificare l'aggiornamento del codec come una normale modifica di
configurazione del gateway; non riavviare il servizio per ogni comando.

Modello alternativo per firmware moderno, **solo con lunghezza verificata**:

```json
{
  "command":"gatt",
  "mac":"AA:BB:CC:DD:EE:FF",
  "operation":"patch",
  "uuid":"1F1F",
  "value":"55",
  "prefix":"55",
  "codec":"atc_cfg_wire",
  "offset":1,
  "write_offset":1,
  "patch":{"flg3":{"adv_interval_delay":10}}
}
```

| Parametro | Significato | Patch nel modello `atc_cfg_wire` |
|---|---|---|
| `flg3.adv_interval_delay` | 0..15, unita' 0.625 ms, limite del ritardo pseudocasuale ADV | `{"flg3":{"adv_interval_delay":10}}` |
| `flg3.date_ddmm` | Bit 6, ordine data sui modelli che lo usano; UI DD/MM su MJWSD05MMC_EN | `{"flg3":{"date_ddmm":true}}` |
| `flg3.weekday_bit` | Bit 7: **nasconde** giorno su MJWSD05MMC/EN; **mostra** giorno su LYWSD02MMC | `{"flg3":{"weekday_bit":false}}` mostra giorno su MJWSD05MMC |
| Stesso bit, LYWSD02MMC | Polarita' inversa al caso precedente | `{"flg3":{"weekday_bit":true}}` mostra giorno su LYWSD02MMC |
| `event_adv_cnt` | Duplicati dei beacon evento; default 6, massimo 255 | `{"event_adv_cnt":6}` |
| `advertising_interval_raw` | 1..160, 62.5 ms per unita'; C limita a 10 s | `{"advertising_interval_raw":40}` |
| `measure_interval` | C minimo 2; massimo dinamico | `{"measure_interval":4}` |
| `rf_tx_power_raw` | Codice radio intero della tabella RF | `{"rf_tx_power_raw":191}` |
| `connect_latency_raw` | Latenza periferica intera, senza conversione float | `{"connect_latency_raw":49}` |
| `lcd_interval_raw` | 50 ms per unita', se il modello lo usa come intervallo LCD | `{"lcd_interval_raw":50}` |
| `averaging_measurements` | Media logger, 0..255 | `{"averaging_measurements":60}` |
| `flags1` | Byte completo dei bit `flg`, semantica come sezione 3.2 | `{"flags1":135}` solo se il profilo desiderato completo e' `0x87` |
| `flags2` | Byte completo dei bit `flg2` | `{"flags2":112}` solo se si desiderano tutti e soli i bit `0x70` |

`flags1/flags2` sono byte completi, non maschere da sommare. Per abilitare
Coded preservando gli altri bit calcolare `nuovo_flags2 = vecchio_flags2 | 0x60`
e usare quel numero nella patch. Con `cfg` invece la patch annidata preserva
automaticamente i bit non citati; i due modelli sono alternative.

**Validazione reale del firmware**, in
[test_config()](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.c#L439):

* Long Range forza anche `bt5phy`.
* ADV 0 diventa 1; valori >160 diventano 160. La UI JS consente fino a
  255 e alcuni tooltip dichiarano limiti diversi: prevale il C.
* Il moltiplicatore misura ha minimo 2 e un limite superiore calcolato
  per contenere il periodo entro circa 250 secondi.
* La potenza viene ricondotta all'intervallo dei codici della relativa
  alimentazione radio: 130..191 o 23..63, non a dBm arbitrari.
* Latenza/timeout connessione sono ricalcolati; batteria bassa puo' imporre
  la latenza di default. Raw 0 cambia anche la strategia di intervallo
  connessione: non significa soltanto "20 ms".
* Intervallo LCD minimo 10 unita' per LCD normali, minimo specifico per EPD.
* `hw_ver` viene ricalcolato. Bit riservati non diventano opzioni solo
  perche' il firmware li conserva.

Una patch fuori limite puo' **essere scritta e poi rifiutata dal gateway**
perche' la risposta normalizzata non coincide col valore richiesto.
Questo non e' un errore di trasporto: non ritentare automaticamente.

Default LYWSD03MMC nel C corrente: ADV 40 (2.5 s), misura 4, LCD 49
(2.45 s), media logger 180, latenza 49, potenza nominale +0.04 dBm,
tipo BTHome, comfort e low-power abilitati, delay 10, eventi 6.
Non confondere i valori iniziali dell'oggetto JS o dei campi HTML con
questi default: il flasher deve prima leggere il dispositivo.
Default comfort: 21..26 °C, 30..60 %RH.
Altri modelli hanno default diversi, per esempio MHO-C401 usa misura 8,
LCD 99 e media 90. `56` non significa "carica i default LYWSD03MMC".

## 7. Calibrazione sensori e coefficienti

### 7.1 Sensore principale: `0x25`, default `0x26`

La risposta corrente include coefficienti e informazioni del driver:

| Dati dopo ID comando | Tipo LE | Significato |
|---|---|---|
| Byte 0..3 | uint32 | `val1_k`: coefficiente prima grandezza, normalmente T |
| Byte 4..7 | uint32 | `val2_k`: coefficiente seconda grandezza, normalmente H |
| Byte 8..9 | int16 | `val1_z`: zero prima grandezza, centesimi |
| Byte 10..11 | int16 | `val2_z`: zero seconda grandezza, centesimi |
| Byte 12..15 | uint32 | ID sensore, informazione di rilevamento |
| Byte 16 | uint8 | Indirizzo I2C nella convenzione del firmware |
| Byte 17 | uint8 | Tipo sensore, layout recente |

Il flasher espone K/100 e Z/100, ma K **non e' un moltiplicatore da applicare
direttamente ai gradi letti**: la conversione dichiarata e'
`valore_raw * K / 65536 + Z`, nel dominio interno in centesimi.
K/Z di default dipendono dal sensore e dal driver.

| Parametro | Esempio di modifica individuale al blocco letto |
|---|---|
| Slope temperatura | `{"val1_k":17500}` (175.00 nella UI JS, non default universale) |
| Slope umidita' | `{"val2_k":10000}` (100.00 nella UI, solo esempio di scala) |
| Zero temperatura | `{"val1_z":-4500}` (-45.00 nella UI) |
| Zero umidita' | `{"val2_z":-600}` (-6.00 nella UI) |

Questi sono **delta logici**, non patch accettate da `codec:"cfg"`:
`cfg` non contiene tali campi e nessun codec CFS e' incorporato.
La risposta ha una coda informativa che non va rispedita come impostazione.
Il motore non ha un ritaglio finale: aggiungere un codec della risposta
non rende automaticamente sicura una patch.

Procedura: leggere `25`, modificare solo i coefficienti desiderati,
serializzare i primi 12 byte LE e usare `exchange`, poi rileggere e
confrontare. Esempio di **sostituzione completa**, non calibrazione consigliata:

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"255C440000102700006CEEA8FD","prefix":"25"}'
```

Il blocco rappresenta K1=17500, K2=10000, Z1=-4500, Z2=-600.
Non inviarlo senza conoscere driver e valori originali.
Per SCD41 il ramo C di `25` limita `val1_z` a 0..2000:
un offset negativo non e' valido su quel sensore.
`26` ripristina i coefficienti di default: e' un'azione, non una patch.

### 7.2 MY18B20: `0x27`, default `0x28`

K uint32 LE e Z int16 LE (sei byte di campi per sensore); UI K/100 e Z/100.
La struttura C non e' packed: verificare padding e dimensione con la
toolchain target prima di modellare l'intera risposta. Il comando `27`
trasmette anche metadati e un byte finale non presenti nella semplice
scrittura dei coefficienti; vedere il rapporto sui tracciati.
Delta logici: `{"temp_k":17500}` oppure `{"temp_z":-4500}`, preservando
il coefficiente non interessato. Non sono nomi del codec incorporato.
Esempio raw del blocco intero:

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"275C4400006CEE","prefix":"27"}'
```

Build con piu' sensori richiedono di verificare il layout effettivo.
`28` ripristina i valori di default.

### 7.3 Altri sensori, non opzioni di un LYWSD03MMC

I seguenti comandi appartengono a build condizionali, non a periferiche
che appaiono impostando un flag di configurazione.
I delta JSON sono **descrizioni di modifica**, da tradurre nel payload
raw preservando gli altri campi: non sono patch dello schema incorporato.

| ID/servizio | Parametro | Tipo e esempio individuale |
|---|---|---|
| `2B`/`2C`, INA3221 | K1, K2 dei canali aggiuntivi | uint32; `{"val1_k":10000}`, `{"val2_k":10000}` |
| Stessi | Z1, Z2 | int16; `{"val1_z":0}`, `{"val2_z":0}` |
| `2D`, XBR818 | `trg_ac` soglia radar | uint16; `{"trg_ac":100}` |
| Stesso | `time_s` tempo hold | uint16, 1..524 s; `{"time_s":30}` |
| `49`, HX71X | `zero` | uint32; `{"zero":0}` |
| Stesso | `coef` | uint32; `{"coef":1000}` |
| Stesso | `volume_10ml` | uint32, volume in 10 mL; `{"volume_10ml":10000}` = 100 L |
| `68`, SDM/DAC | `in_min` | int16; `{"in_min":0}` |
| Stesso | `in_max` | int16; `{"in_max":10000}` |
| Stesso | `out_min` | uint16; `{"out_min":0}` |
| Stesso | `out_max` | uint16; `{"out_max":32767}` |

HX71X: configurazione di 12 byte, risposta comprende anche ADC/lettura
runtime: non rispedire la coda. SDM: otto byte di configurazione; la risposta
include il coefficiente `k` int32 derivato, ricalcolato da `init_dac()`.
Non patchare `adc`, `value` o `k` come se fossero impostazioni.
Esempio radar completo soglia 100, hold 30 s: `2D64001E00`.
Esempio HX71X completo zero 0, coef 1000, volume 10000:
`4900000000E803000010270000`.
Esempio DAC completo 0..10000 -> 0..32767:
`68000010270000FF7F`. Rileggere e controllare prima di pilotare carichi.

### 7.4 SCD41: differenza concreta fra JavaScript e C

Il flasher pubblicato implementa `2E` (impostazioni), `2F` (default) e
`77` (funzioni sensore), **non presenti nel parser C del commit esaminato**.
Non dedurne il supporto solo perche' il repository contiene `scd41.c`.
E' una divergenza reale fra sorgenti pubblicate separatamente.

| Parametro JS `2E` | Serializzazione in sette word LE | Esempio di delta logico |
|---|---|---|
| Offset temperatura | uint16 `round(°C * 65535 / 175)` | 4 °C -> `{"temp_offset":1498}` |
| Altitudine | uint16 metri | `{"altitude":300}` |
| Target ASC CO2 | uint16 ppm | `{"asc_co2":400}` |
| ASC abilitata | uint16, UI 0/1 | `{"asc_ena":1}` |
| Periodo ASC iniziale | uint16, dominio driver SCD4x | `{"asc_ini_per":48}` |
| Periodo ASC standard | uint16, dominio driver SCD4x | `{"asc_std_per":168}` |
| Pressione | uint16 hPa; UI Pa divisa per 100 | 101300 Pa -> `{"pressure":1013}` |

Questi non sono comandi certificati sul C corrente, ne' campi di `cfg`.
Il JS `77` usa subcomando uint8 e argomento uint16 LE:
query stato (solo `77`); 2 ricalibrazione forzata con ppm; 3 lettura
impostazioni; 4 scrittura EEPROM sensore; 5 reload EEPROM;
6 factory reset; 7 self-test. Esempio 400 ppm: `77029001`.
La UI attende fino a **due minuti**: eccede il singolo `exchange` del
gateway (massimo 30 s). Dove il firmware supporta davvero queste operazioni,
usare una sessione persistente, sottoscrivere prima, scrivere una volta,
poi raccogliere notifiche in piu' operazioni rinnovando il lease.
Non aggiungere retry automatici.

## 8. Orologio, drift e storico

### 8.1 `0x23`: orologio

Scrittura `23 + uint32 LE`, secondi epoch.
Il nome C e' UTC, ma il flasher scrive
`Date.now()/1000 - timezoneOffset*60`: epoch **traslato all'ora locale**
per mostrare l'ora sul dispositivo. Non applicare il fuso due volte.
Decidere fra la convenzione del flasher e UTC reale; il firmware non
acquisisce un database timezone/DST.

Esempio dimostrativo 1700000000 secondi, non l'ora attuale:

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"2300F15365","prefix":"23"}'
```

`current_last_date` decodifica anche l'ultima impostazione e campi calcolati.
La modifica logica `{"Current_set_date_local":1700000000}` non va tradotta
in una patch integrale di otto byte: usare il commit raw di quattro byte.
`Last_set_date_local` e' informazione, non un parametro indipendente.

### 8.2 `0x24`: correzione drift

Scrittura: **delta int16 LE** rispetto a 16000000 tick/s, non il valore
uint32 assoluto restituito dalla lettura.
UI -32767..32767, unita' 1/16 microsecondo per secondo.
Delta +100 -> `246400`; delta -100 -> `249CFF`.

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"246400","prefix":"24"}'
```

Una modifica logica `{"delta":100}` si traduce cosi', non in una patch
`{"Time_Tick_Step":100}`. `time_tick_step` ha un uint32 assoluto e un delta
calcolato: ricodificarlo tutto produce il comando sbagliato.
Il flasher dopo la correzione reimposta l'orologio e richiede almeno tre
ore per la stima del drift. Il gateway non lo fa implicitamente.

### 8.3 Storico `0x35`, cancellazione `0x36`

| Parametro | Wire | Esempio |
|---|---|---|
| Numero record | uint16 LE dopo `35` | 50 -> `3532000000` |
| Indice iniziale | uint16 LE successivo | 10 con count 50 -> `3532000A00` |
| Cancellazione | Azione con magic, non patch | `36123400`, distruttivo |

Le notifiche `35` hanno contatore, tempo, misure e record finale corto.
Il `count` del gateway indica **notifiche** attese (massimo 64), non il
count logger. Nessun assemblaggio automatico in tabella, nessun codec
logger incorporato. Per letture lunghe usare sessione e lotti, evitando
la coda massima di 128 eventi. La capacita' 19632 citata nella UI non e'
un limite universale di ogni layout flash.

## 9. Nome, MAC, chiavi e sicurezza

### 9.1 Nome BLE (`0x01`)

`01 + nome` imposta; `0100` ripristina il nome automatico; `01` legge.
La UI ammette 1..18 caratteri ma serializza UTF-8: usare ASCII e rispettare
i limiti in **byte** del firmware. Esempio `ATC_Cucina`:

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"014154435F437563696E61","prefix":"01"}'
```

`device_name` incorporato include un byte nullo per il **Mi DevName**,
non e' lo schema del nome BLE `01`. Non applicarvi
`{"name":"ATC_Cucina"}` per cambiare il nome BLE.
Il motore patch rifiuta cambi di lunghezza: rinominare con `exchange`.

### 9.2 MAC (`0x10`)

Scrittura `10 SIZE MAC_LE [RAND16_LE]`, SIZE 6 o 8.
Esempio **illustrativo**, non identita' da riusare su piu' dispositivi:
pubblico `A4:C1:38:12:34:56`, random `ABCD`:
`100856341238C1A4CDAB`. Solo pubblico: `100656341238C1A4`.
Reset: `1000`, puo' cancellare il settore MAC.

| Parametro | Modifica logica | Traduzione |
|---|---|---|
| Pubblico | `{"MAC":"A4:C1:38:12:34:56"}` | Sei byte in ordine inverso |
| Random | `{"rand16":43981}` | Word LE `CDAB` |

Non presentare questi delta come patch universali `mac_address`.
La risposta ha lunghezza e byte random; l'identita' cambia al successivo
riavvio e l'esito puo' richiedere riconnessione al nuovo MAC.
Il vendor e' metadato, non scrivibile. In presenza di bonding anche il
client puo' dover dimenticare il vecchio peer. Prevedere recupero locale.

### 9.3 Bindkey beacon (`0x18`)

Lettura: `18 + 16 byte` se presente; `18FF` se assente.
Scrittura: `18 + 16 byte`, persistente.
Generare chiavi casuali e trasferirle privatamente al ricevitore.
Esempio sintattico con **chiave pubblica di test**:

```sh
ble2uart-gateway --command '{"command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"exchange","uuid":"1F1F","value":"18000102030405060708090A0B0C0D0E0F","prefix":"18"}'
```

Con `atc_bindkey_wire` dell'appendice e chiave gia' presente:
query/prefisso `18`, `offset:1`, `write_offset:0`, patch
`{"key":"000102030405060708090A0B0C0D0E0F"}`.
Se assente, il roundtrip rifiuta `FF` per lunghezza: inizializzare via raw.
Le risposte patch possono mostrare chiavi prima/dopo: proteggere log,
cronologia shell, CGI e backup.

### 9.4 Chiavi Mi (`0x11`..`0x17`)

| ID | Funzione | Parametri/esempio di modifica |
|---|---|---|
| `11` | Identificativo nome Mi | Blocco Mi, distinto dal nome BLE; nessuna patch incorporata generale |
| `12` | Token 12 byte + bindkey 16 byte | Delta logici `token` e `bindkey`, non campi di `cfg` |
| `13` | Configurazione Mi del key store | Blocco specifico Mi, non `55` |
| `14` | Chiavi marcate cancellate | Lettura/eventi, non un flag configurabile |
| `15` | Legge tutte le chiavi | Azione `15`, piu' tipi di risposta, segreti |
| `16` | Ripristina/scambia token e bindkey precedenti | Azione `16` |
| `17` | Cancella tutte le chiavi Mi | Azione `17`, distruttiva |

Scrittura `12`: **28 byte di dati**, senza byte lunghezza della risposta.
Per cambiare solo il token mantenere i 16 byte bindkey letti; per cambiare
solo bindkey mantenere i primi 12 byte token. L'esempio di forma e'
`12 || TOKEN_12_BYTE || BINDKEY_16_BYTE`, non contiene valori da copiare.
La risposta Mi ha ID/lunghezza e puo' essere frammentata. Il flasher
accumula i frammenti; il gateway non li assembla automaticamente.
`token_bind_mi_keys` puo' decodificare un blocco assemblato da 28 byte,
non giustifica una patch diretta su una notifica arbitraria.

La UI richiede una MTU sufficiente (`7120` nel protocollo sensore).
Per una scrittura `12` da 29 byte serve MTU ATT >=32.
Usare sessione, verificare MTU, sottoscrivere, inviare una volta e
assemblare/confrontare le risposte.

### 9.5 PIN (`0x70`)

PIN 0..999999 decimale, **uint32 LE**, non ASCII/BCD.
Zero disabilita. Esempio 123456 -> `7040E20100`;
disabilitazione -> `7000000000`.
La risposta e' un esito, non una lettura del PIN: niente patch
read-modify-write.

Cambiare lo stato abilitato/disabilitato cancella il pairing e programma
un reset alla disconnessione. Il JSON GATT del gateway non e' una UI di
inserimento passkey ne' una garanzia di pairing con ogni policy.
Non abilitare PIN senza verificare riconnessione e recupero reali.

## 10. Display esterno, buffer e notifiche

### 10.1 `0x22`: dati esterni temporanei

Sette byte: due numeri int16 LE, validita' uint16 LE, flag uint8.
Sugli hardware 9/12/49 i primi quattro byte sono un unico int32 LE.
Non sono misure del sensore, ne' coefficienti persistenti.

| Parametro | Classico | Hardware 9/12/49 | Esempio di patch con schema dedicato |
|---|---|---|---|
| Numero grande | int16, decimi | int32, centesimi | `{"big_raw":234}` = 23.4 classico; `{"big_raw":2345}` = 23.45 esteso |
| Numero piccolo | int16, intero; CGG1/CGDK2 decimi | Assente | `{"small_raw":55}` |
| Validita' | uint16 secondi | Uguale | `{"valid_seconds":600}` |
| Smiley | Bit 0..2 | Uguale | `{"symbols":1}` se altri bit erano zero |
| Percentuale | Bit 3 | Bit 7 nel JS | `{"symbols":8}` classico; `{"symbols":128}` esteso |
| Batteria | Bit 4 | Bit 3 | `{"symbols":16}` classico; `{"symbols":8}` esteso |
| Simbolo temperatura | Bit 5..7 | Bit 4..6 nel JS | `{"symbols":160}` classico codice 5; `{"symbols":48}` esteso codice 3 |

Preservare i bit simbolo non interessati. Segmenti e codici °C/°F variano
con il display. Il C esteso modella l'ultimo nibble come simbolo a quattro
bit, mentre il JS espone percentuale separata: non sono due campi C distinti.
La UI limita validita' a 2..65535 s; il C usa `FFFF` per validita' permanente.
Limiti numerici del display sono inferiori al range del tipo binario.

Con `atc_ext_wire` o `atc_ext32_wire` dell'appendice, query/prefisso `22`,
`offset:1`, `write_offset:0`, e risposta esattamente di sette byte dati:

```json
{
  "command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"patch",
  "uuid":"1F1F","value":"22","prefix":"22","offset":1,
  "codec":"atc_ext_wire",
  "patch":{"big_raw":234,"small_raw":55,"valid_seconds":600}
}
```

### 10.2 `0x60`/`0x61`: buffer LCD

`60` legge; `60 + segmenti` scrive il buffer, con dimensione e mappa
specifiche del display. Non e' una stringa UTF-8.
Modifica individuale: `buffer[i] = (vecchio & ~mask) | nuovi_bit`.
Nessun codec universale incorporato o byte affidabile per tutti i display.

`61` legge i flag del meccanismo dump/notifiche; `6100` e' il ripristino
rendering normale usato dal flasher. Sono flag runtime, non `screen_off`
di `55`. Le modifiche non rendono persistente un numero esterno.

## 11. Scansione periodica del sensore (`0x21`)

Non e' `scan-start` dell'ESP32. Richiede `SERVICE_SCANTIM` nel sensore.
Il blocco corrente e' intervallo uint32 LE + MAC[6] LE:

| Parametro | Uso | Patch `atc_scan_wire` |
|---|---|---|
| Intervallo | Secondi, 0 disabilita | `{"interval_seconds":60}` |
| MAC sorgente | Sei byte inversi | `{"peer_le":"56341238C1A4"}` per A4:C1:38:12:34:56 |

La UI espone TrSc da 5.3 su alcuni hardware LYWSD03MMC (0,3,4,5,10,14),
non su tutti i dispositivi della pagina.
Il C ha anche un possibile `SCAN_USE_BINDKEY`: nel commit e' 0, campo
assente. Se abilitato in una build aggiunge 16 byte e cambia il layout:
non usare automaticamente lo schema di dieci byte dell'appendice.
Il comando ferma la scansione locale prima di aggiornarne la configurazione
e persiste il blocco.

```json
{
  "command":"gatt","mac":"AA:BB:CC:DD:EE:FF","operation":"patch",
  "uuid":"1F1F","value":"21","prefix":"21","offset":1,
  "codec":"atc_scan_wire","patch":{"interval_seconds":60}
}
```

## 12. Inventario degli ID: configurazione, azioni e sola lettura

Fonte primaria:
[enum e protocollo](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.h#L6)
e [parser](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L288).
La tabella comprende anche diagnostica e ID dichiarati senza handler:
non sono tutti parametri per i quali avrebbe senso una patch.
Gli ID sono esadecimali. Una guardia di compilazione non e' un'opzione
attivabile da JSON.

| ID | Funzione | Supporto/uso corretto |
|---|---|---|
| `00` | Identificazione protocollo/hardware/software/servizi | Lettura; usare per scegliere il layout, nessuna patch |
| `01` | Nome BLE | Lettura/scrittura, sezione 9.1 |
| `02` | Indirizzi dispositivi interni | Lettura, lista dipendente dall'hardware |
| `03` | Scan I2C | Azione diagnostica se bus I2C compilato; non SCAN radio |
| `04` | Transazione I2C/SMBus universale | Accesso hardware raw, non una configurazione strutturata |
| `05` | Identificativo sensore | Lettura se servizi sensore disponibili |
| `06` | JEDEC ID flash | Lettura, non scelta del tipo flash |
| `0E`/`0F` | Registri radar XBR818 | Rami debug condizionali, non enum principale; non usarli su termometri |
| `10` | MAC pubblico/random | Sezione 9.2 |
| `11`..`17` | Archivio chiavi Mi | Solo `SERVICE_MI_KEYS`, sezione 9.4 |
| `18` | Bindkey beacon | Solo `SERVICE_BINDKEY`, sezione 9.3 |
| `20` | Comfort | Solo schermo, sezione 4 |
| `21` | Scansione periodica del sensore | Solo `SERVICE_SCANTIM`, sezione 11 |
| `22` | Dati esterni display | Solo schermo, sezione 10 |
| `23` | Orologio | Sezione 8.1 |
| `24` | Drift | Solo `SERVICE_TIME_ADJUST`, sezione 8.2 |
| `25`/`26` | Coefficienti sensore/default | Servizi sensore, sezione 7.1 |
| `27`/`28` | MY18B20/default | Solo `SERVICE_18B20`, sezione 7.2 |
| `29`/`2A` | Coefficienti/calibrazione RH | Servizi PWM RH/PLM, dettagli sotto |
| `2B`/`2C` | Canali 2/3 INA3221 | Build INA3221, sezione 7.3 |
| `2D` | Soglia/hold XBR818 | Build radar, sezione 7.3 |
| `2E`/`2F` | SCD41/default nel JS | **Assenti dal parser C fissato**, sezione 7.4 |
| `33` | Quantita' di misure da notificare nella connessione | `3300` ferma; `33FF` flusso continuo; valori intermedi limitano il trasferimento |
| `35` | Lettura logger | Solo storico, sezione 8.3 |
| `36` | Cancellazione logger | Azione distruttiva con magic |
| `40` | RDS, dichiarato nell'enum | Nessun handler del parser corrente; non inventare una patch |
| `44` | Trigger/reed | Solo servizi TH_TRG/RDS, sezione 5 |
| `45` | Uscita trigger/stato | Runtime, sezione 5 |
| `49` | HX71X | Build cella di carico/livello, sezione 7.3 |
| `55` | Configurazione principale | Sezioni 3 e 6 |
| `56` | Default configurazione principale | Azione; risposta con prefisso **55**, non 56 |
| `60`/`61` | Buffer/controllo LCD | Runtime, sezione 10.2 |
| `68` | SDM/DAC | Build con uscita SDM, sezione 7.3 |
| `70` | PIN | Solo `SERVICE_PINCODE`, sezione 9.5 |
| `71` | Richiesta MTU dal sensore | `7120` come nel JS; non un parametro persistente |
| `72` | Riavvio alla disconnessione | Azione; non chiude subito il link |
| `73` | Regione OTA estesa | Solo `SERVICE_OTA_EXT`; parametri boot/flash, non una patch di `cfg` |
| `77` | Funzioni SCD41 nel JS | **Assente dal parser C fissato** |
| `D1` | OTA clear | Dichiarato, senza handler corrente: non documentato come comando funzionante |
| `D3`/`D4`/`D5`/`D7` | Scrittura/lettura/erase flash e cambio boot | Dichiarati, senza handler corrente; non fornire payload assumendo supporto |
| `DC` | Lettura/scrittura EEP per ID | Raw, bypassa i validatori applicativi |
| `DD` | Reset Long Range | Azione speciale, risposta configurazione `55` |
| `DE` | Debug/lettura memoria flash | Non parametro configurabile |
| `DF` | Debug calibrazione RH | Ramo condizionale, non enum pubblico stabile |

### 12.1 RH/PLM: ogni parametro supplementare

Con `USE_SENSOR_PWMRH==2`, il blocco coefficienti e':
K uint32 LE, Z uint16 LE, D uint16 LE (otto byte);
la risposta aggiunge ADC RH e ADC D, entrambi uint16 di sola lettura.

| Parametro | Esempio di modifica logica | Uso |
|---|---|---|
| `coef.k` | `{"k":65536}` | Scala calibrazione, dipende dal driver |
| `coef.z` | `{"z":0}` | Zero raw |
| `coef.d` | `{"d":100}` | Delta raw |
| `adc_rh`, `adc_d` | Nessuna patch | Misure ADC |

Leggere `29`, modificare i soli coefficienti, inviare `29 + blocco`
e rileggere. Esempio completo di forma: `290000010000006400`.
Non e' una taratura consigliata. Le code ADC non devono essere rispedite
o richieste in una verifica di patch.
`2A02` richiede calibrazione 100%; `2A03` calibrazione 0%;
il subcomando 1 riguarda la calibrazione temperatura solo nel ramo
PWM RH che lo supporta. Sono azioni fisiche che richiedono una condizione
di riferimento, non setpoint dell'umidita' ambiente.

### 12.2 LCD: tutti i bit di controllo

In `lcd_flg`: bit 0 `ext_data_buf`, bit 1 `notify_on`, bit 2..6 riservati,
bit 7 `send_notify`.
Esempi di **scrittura byte completo**, con tutti gli altri bit a zero:
`6101` seleziona buffer esterno; `6102` imposta `notify_on`;
`6180` imposta `send_notify`; `6100` azzera i controlli e ripristina
il comportamento normale. Per modifiche a un solo bit preservare gli
altri leggendo prima `61`. L'implementazione puo' aggiornare flag runtime:
non promettere una patch persistente o un rendering uguale per ogni LCD.

### 12.3 OTA, EEP e bus: non sono normali parametri di patch

`73` descrive indirizzo e dimensione della regione OTA; la notifica contiene
anche uno stato/evento. I valori sono dipendenti dal layout flash e dalla
procedura di aggiornamento: non scegliere indirizzi "di esempio" da
scrivere su un dispositivo. La pagina esegue un workflow OTA con altre
caratteristiche e pacchetti: `exchange` su `1F1F` da solo non e' un flasher.

`04` permette transazioni I2C con indirizzo, sequenza di scrittura,
quantita' di lettura e controlli del bus. Sono operazioni sul chip,
non attributi di `cfg`. Gli indirizzi della lista `02`/`03` usano la
convenzione del firmware (spesso indirizzo a 8 bit): non confonderli
con un indirizzo I2C a 7 bit.

`DC` accede ai record persistenti per ID; una patch raw di EEP puo'
saltare `test_config()` e rendere il dispositivo non riconnettibile.
Per i parametri elencati usare sempre il comando applicativo dedicato.
`DE` e le diagnostiche non hanno esempi di patch perche' non sono
configurazioni. L'assenza di un handler per un ID dichiarato non
autorizza a dedurne il comportamento da un vecchio firmware.

## 13. Persistenza, riavvio, risposte e differenze importanti

### 13.1 Salvataggio non equivale ad applicazione

| Famiglia | Persistenza/effetto |
|---|---|
| `55`, `56` | Scrittura record EEP della configurazione; parametri radio possono richiedere reset |
| `20` | Record comfort EEP |
| `44` | Salva solo impostazioni, esclude l'ultimo byte di stato |
| `45`, `22`, `60`, `61`, `33` | Runtime; non trasformarli in impostazioni di boot |
| `18`, chiavi Mi, MAC, PIN | Persistenti, con procedure ed effetti specifici |
| `24`, coefficienti sensori, `21`, DAC, radar | Record di configurazione dedicati |
| `23` | Imposta il clock runtime, non garantisce mantenimento senza batteria |
| `72` | Programma reboot dopo disconnessione |

Nel C corrente cambiare i bit `bt5phy/longrange` programma gia' il reset
alla disconnessione; la risposta puo' arrivare prima dell'effetto radio.
`screen_off` reinizializza il display senza aspettare un reboot.

**Coded non e' necessariamente mantenuto dopo rimozione batteria**:
[inizializzazione cold boot](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.c#L906)
azzera `longrange` e salva la configurazione se il registro retention
non contiene il marker atteso. Un reset software/deep-sleep non equivale
a una vera interruzione di alimentazione. Anche la migrazione da versioni
<=4.1 azzera il bit. Non promettere "abilitato per sempre" dopo un
solo `patch_verified:true`.

### 13.2 Discrepanza di lunghezza `55` nel sorgente corrente

Questo dettaglio impedisce di trattare l'esempio iniziale come una
garanzia su qualunque firmware:

* `cfg_t` logico corrente: 11 byte.
* Buffer `my_RxTx_Data`: dichiarato lungo `sizeof(cfg)+2`, cioe' 13 byte.
* Contenuto previsto: `55`, versione, 11 byte di configurazione.
* [ble_send_cfg()](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/ble.h#L242)
  passa invece `sizeof(cfg)+3` come lunghezza della notifica: **14 byte**,
  uno oltre il buffer dichiarato in
  [app_att.c](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app_att.c#L431).

E' un'incoerenza del C pubblicato, non un byte configurabile documentato.
Il JS legge i campi noti per indice e non richiede consumo esatto:
puo' quindi mostrare valori apparentemente corretti anche con una coda
in piu'. Il gateway invece **deve rifiutare** tale risposta con `cfg`
e con lo schema canonico dell'appendice: dopo `offset:1` rimangono
13 byte, ma la struttura ne descrive 12.

Non aggirare il problema aggiungendo un campo "padding" da riscrivere,
non scartare una coda di significato ignoto automaticamente e non
considerarla una nuova versione di configurazione.
Verificare la lunghezza realmente ricevuta dal binario del dispositivo.
Per il sorgente in questione serve una correzione upstream della lunghezza
o una build verificata; questo documento non modifica il firmware.

### 13.3 Il JavaScript non e' una copia uno-a-uno del C

| Evidenza | Conseguenza |
|---|---|
| SCD41 `2E`/`2F`/`77` nel JS, non nel parser C fissato | Tool e firmware possono provenire da revisioni diverse |
| Alias bit per hardware 9/12/49 | Stesso byte, significati diversi; codec storico non basta |
| Offset storici riusati da `flg3/event_adv_cnt` | Modificare `temp_offset` su firmware nuovo puo' cambiare flags radio/display |
| `hw_ver` intero recente contro bitfield storico | Identificazione storica puo' risultare plausibile ma falsa |
| UI ADV fino a 255 contro C massimo 160 | La UI non e' il validatore definitivo |
| UI temperatura/umidita' in float contro coefficienti/tick interi C | Serve controllare scale, arrotondamento e verso conversione |
| JS accumula frammenti Mi; gateway no | Un codec di struttura non sostituisce il protocollo di assemblaggio |
| JS accetta code extra, gateway esige roundtrip esatto | Stessa lettura visuale non prova compatibilita' patch |

### 13.4 Procedura operativa per Coded sul LYWSD03MMC

1. Verificare modello, versione >=4.2 e firmware compatibile; leggere raw
   `55`, annotare lunghezza e byte originali.
2. Scegliere un codec byte-esatto con semantica corretta; niente patch se
   il firmware invia la coda anomala appena descritta.
3. Con servizio attivo usare la patch `bt5phy=true,longrange=true`.
   Per versioni moderne scegliere il layout intero e modificare solo
   il byte interessato con maschera `0x60`, preservando gli altri bit.
4. Attendere conferma applicativa, non soltanto ATT write complete.
5. Chiudere la sessione: il firmware puo' ora riavviarsi. Un `72` aggiuntivo
   va inviato solo se serve esplicitamente, non dopo ogni parametro.
6. Verificare gli advertisement ricevuti con primary/secondary PHY `3`
   e la configurazione riletta. `coded:true` della connessione non prova
   advertising Coded.
7. Se interessa la persistenza, provare anche il vero power-cycle:
   il C esaminato disabilita Long Range al cold boot.

Il gateway non conferma persistenza flash dopo interruzione di alimentazione,
consumo reale, portata o supporto di ogni sensore solo perche' la patch
e' stata confermata.

## 14. Appendice: schemi esterni di esempio senza conversioni lossy

Questo blocco YAML e' un **overlay opzionale**, non uno schema gia'
installato dal pacchetto. Salvarlo, per esempio, come `atc-wire.yaml`
e caricarlo nella configurazione/avvio del daemon secondo la
[guida codec](CODEC.md).
Non sostituisce la selezione per versione/modello e non corregge la
lunghezza anomala del C descritta nella sezione 13.2.
Non contiene schemi trigger/CFS perche' le code di risposta non possono
essere ritagliate dal motore patch attuale.

```yaml
version: 1
structures:
  atc_cfg_wire:
    kind: struct
    fields:
      - {name: firmware_version_raw, kind: int, fmt: "<B"}
      - {name: flags1, kind: int, fmt: "<B"}
      - {name: flags2, kind: int, fmt: "<B"}
      - name: flg3
        kind: transform
        func: bytes2bits
        sub:
          kind: struct
          fields:
            - {name: weekday_bit, kind: boolean}
            - {name: date_ddmm, kind: boolean}
            - {name: reserved, kind: bits, length: 2}
            - {name: adv_interval_delay, kind: bits, length: 4}
      - {name: event_adv_cnt, kind: int, fmt: "<B"}
      - {name: advertising_interval_raw, kind: int, fmt: "<B"}
      - {name: measure_interval, kind: int, fmt: "<B"}
      - {name: rf_tx_power_raw, kind: int, fmt: "<B"}
      - {name: connect_latency_raw, kind: int, fmt: "<B"}
      - {name: lcd_interval_raw, kind: int, fmt: "<B"}
      - {name: hw_version_raw, kind: int, fmt: "<B"}
      - {name: averaging_measurements, kind: int, fmt: "<B"}
  atc_ext_wire:
    kind: struct
    fields:
      - {name: big_raw, kind: int, fmt: "<h"}
      - {name: small_raw, kind: int, fmt: "<h"}
      - {name: valid_seconds, kind: int, fmt: "<H"}
      - {name: symbols, kind: int, fmt: "<B"}
  atc_ext32_wire:
    kind: struct
    fields:
      - {name: big_raw, kind: int, fmt: "<l"}
      - {name: valid_seconds, kind: int, fmt: "<H"}
      - {name: symbols, kind: int, fmt: "<B"}
  atc_scan_wire:
    kind: struct
    fields:
      - {name: interval_seconds, kind: int, fmt: "<L"}
      - {name: peer_le, kind: bytes, length: 6}
  atc_bindkey_wire:
    kind: struct
    fields:
      - {name: key, kind: bytes, length: 16}
```

`firmware_version_raw`, `hw_version_raw` e `flg3.reserved` vanno preservati,
non sono opzioni utente. Il primo e' protetto da `write_offset:1`;
il secondo e' ricalcolato dal sensore. Per il formato intero si applica
ancora il controllo di roundtrip del gateway.

Prova **offline**, nessuna radio o modifica del sensore:

```sh
printf '%s\n' '5987700A062804A9313100B4' |
  ble2uart-gateway --codec atc-wire.yaml --decode atc_cfg_wire
```

Il vettore canonico rappresenta versione 5.9, flags `87/70`, delay 10,
eventi 6, ADV 40, misura 4, potenza A9, latenza 49, LCD 49,
hardware 0, media 180. E' un vettore di struttura, non prova che il
firmware corrente emetta proprio quella lunghezza.

## 15. Riferimenti puntuali e verifiche

| Argomento | Sorgente C fissato |
|---|---|
| Strutture cfg, bitfield, dati display | [app.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.h#L53) |
| Default e normalizzazione | [app.c, default](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.c#L70), [test_config](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.c#L439) |
| ID e handler | [cmd_parser.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.h#L6), [cmd_parser.c](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L288) |
| Trigger/reed, campi condizionali | [trigger.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/trigger.h#L15) |
| Sensori e coefficienti | [sensor.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/sensor.h#L63) |
| RH | [rh.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/rh.h#L41) |
| Radar, HX71X, SDM | [xbr818.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/xbr818.h#L9), [hx71x.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/hx71x.h#L26), [sdm_out.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/sdm_out.h#L10) |
| Scan | [scanning.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/scanning.h#L14) |
| Flag LCD | [lcd.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/lcd.h#L26) |
| Notifiche configurazione/display/trigger | [ble.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/ble.h#L242), [ble.c](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/ble.c#L876) |
| Persistenza EEP | [flash_eep.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/flash_eep.h#L15) |

Nel flasher fissato sono particolarmente utili:
[parser notifiche](https://github.com/pvvx/pvvx.github.io/blob/9b588885f24be8e9d61adbd2e37ef04eaf7bf402/ATC_MiThermometer/TelinkMiFlasher.html#L1115),
[clock/nome/MAC](https://github.com/pvvx/pvvx.github.io/blob/9b588885f24be8e9d61adbd2e37ef04eaf7bf402/ATC_MiThermometer/TelinkMiFlasher.html#L3106),
[display/comfort/trigger](https://github.com/pvvx/pvvx.github.io/blob/9b588885f24be8e9d61adbd2e37ef04eaf7bf402/ATC_MiThermometer/TelinkMiFlasher.html#L3236),
[sensori/SCD41](https://github.com/pvvx/pvvx.github.io/blob/9b588885f24be8e9d61adbd2e37ef04eaf7bf402/ATC_MiThermometer/TelinkMiFlasher.html#L3437),
[UI versionata](https://github.com/pvvx/pvvx.github.io/blob/9b588885f24be8e9d61adbd2e37ef04eaf7bf402/ATC_MiThermometer/TelinkMiFlasher.html#L3700)
e [serializzazione cfg](https://github.com/pvvx/pvvx.github.io/blob/9b588885f24be8e9d61adbd2e37ef04eaf7bf402/ATC_MiThermometer/TelinkMiFlasher.html#L4051).

Gli esempi JSON e gli schemi dell'appendice sono verificabili offline
con il binario nativo. Questo riferimento non implica test su hardware,
aggiornamenti firmware eseguiti, misure di portata o validazione di tutte
le combinazioni di servizi compilabili. Le differenze storiche sono
quelle riscontrate nelle condizioni del C e del flasher fissati, non
una ricostruzione certificata di ogni release mai pubblicata.
