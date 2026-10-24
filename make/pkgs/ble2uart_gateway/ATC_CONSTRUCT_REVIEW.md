# Revisione dei tracciati di atc_mi_construct.py rispetto al firmware C

## 1. Esito e perimetro

**Si', occorrono revisioni**, non soltanto aggiunte di nuovi comandi.
Il layout `cfg` storico conserva la lunghezza logica di 12 byte, ma alcuni
byte hanno cambiato significato. Esistono inoltre bit persi in ricodifica,
tipi con segno errato e formati emessi dal C non coperti dal modulo Python.

La sezione **LYWSD03MMC native structures**, invece, descrive il protocollo
del firmware originale Xiaomi: **non va sostituita con i tracciati ATC**.
Il C di ATC non costituisce una specifica del firmware originale.

Analisi del 21 ottobre 2026, revisioni fissate:

* [Firmware pvvx/ATC_MiThermometer, b6b4c7bde322adc7538f1ec10fb32160a00df811](https://github.com/pvvx/ATC_MiThermometer/tree/b6b4c7bde322adc7538f1ec10fb32160a00df811),
  `VERSION=0x59`, cioe' 5.9.
* [Modulo Python richiesto, cb06199ac462bb233849a18b5fc793edebe45220](https://github.com/Ircama/ATC_MiThermometer/blob/cb06199ac462bb233849a18b5fc793edebe45220/python-interface/atc_mi_interface/atc_mi_construct.py).
* [Adapter Python della stessa revisione](https://github.com/Ircama/ATC_MiThermometer/blob/cb06199ac462bb233849a18b5fc793edebe45220/python-interface/atc_mi_interface/atc_mi_construct_adapters.py).
* [Client e catalogo comandi della stessa revisione](https://github.com/Ircama/ATC_MiThermometer/blob/cb06199ac462bb233849a18b5fc793edebe45220/python-interface/atc_mi_interface/atc_mi_config.py).

Sono stati controllati sia gli header C sia i punti che effettivamente
copiano/trasmettono i dati. Un `typedef`, da solo, non identifica la
lunghezza di una risposta; i comandi possono trasmettere solo un prefisso
della struttura, aggiungere dati o avere una coda differente dalla scrittura.

Questo documento **specifica le revisioni da apportare**: non modifica il
repository Python remoto, il firmware o lo schema generato del gateway.
Per parametri, azioni ed esempi operativi vedere il riferimento separato
[ATC_PARAMETERS.md](ATC_PARAMETERS.md).

Una successiva implementazione locale e' disponibile in
[atc_mi_interface](../../../atc_mi_interface/README.md), con schemi dichiarativi,
catalogo dei 49 handler C e tre backend Bleak. Le correzioni locali non
modificano il fork remoto: copertura, verifiche e limiti residui sono descritti
nel README del pacchetto.

### Priorita'

| Priorita' | Revisione | Motivo |
|---|---|---|
| P1 | Separare `cfg` legacy/moderno e scegliere il profilo per firmware/hardware | Una patch valida sintatticamente puo' modificare un parametro diverso |
| P1 | Correggere `atc1441_enc_format.temperature` da signed a unsigned | Temperature alte vengono decodificate come temperature negative |
| P1 | Correggere segno e bitfield di `trigger`/`atc_flag` | Isteresi H negativa errata; bit reed/tasto persi in rebuild |
| P1 | Coprire BTHome `0x5C`/`0x5D` e rifiutare ID senza lunghezza nota | Il C li emette; il parser attuale puo' disallineare gli oggetti successivi |
| P1 | Distinguere payload di lettura, scrittura e notifica | Non riscrivere versione, ID, stati, ADC o code informative |
| P2 | Aggiungere i comandi/risposte assenti e le varianti compilabili | Lo schema dei vecchi termometri non copre tutto il firmware corrente |
| P2 | Gestire PVVX senza byte flags e gli eventi reed separati | Il C puo' emettere queste varianti |
| P2 | Correggere conversioni float non reversibili | Anche un parse/build senza modifiche puo' cambiare un byte |
| P2 | Aggiornare enum Mi e contatore evento `0x20E1` | Identificativi ed eventi C non completamente descritti |
| P3 | Precisare commenti native, handle, timestamp e metadati | Evitare di confondere versioni virtuali, protocolli e valori di sessione |

P1/P2/P3 sono priorita' di manutenzione e correttezza, non classificazioni
di vulnerabilita'.

## 2. Prima distinzione: tre protocolli diversi

| Superficie | Payload | Schema appropriato |
|---|---|---|
| Servizio Xiaomi originale `ebe0ccb0-7a0a-4b0c-8a1a-6ff2997da3a6` | Valori nativi proprietari | `native_temp_hum_v_values`, `native_comfort_values` |
| Servizio ATC `181A`, caratteristiche `2A1F`, `2A6E`, `2A6F` | Valori singoli di due byte | Temperatura/umidita' con scala della singola caratteristica |
| Servizio ATC `1F10`, caratteristica `1F1F` | ID comando + dati/notifiche | Famiglie `00`, `20`, `23`, `33`, `44`, `55`, ecc. |

Il modello commerciale LYWSD03MMC non identifica da solo il protocollo:
lo stesso hardware, dopo il flash ATC, espone un'altra tabella GATT.

Riferimenti:
[tabella di riconoscimento Python](https://github.com/Ircama/ATC_MiThermometer/blob/cb06199ac462bb233849a18b5fc793edebe45220/python-interface/atc_mi_interface/atc_mi_config.py#L44),
[UUID C](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app_att.c#L396),
[trasmissione delle misure singole](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/ble.h#L214).

## 3. Sezione «LYWSD03MMC native structures»

### 3.1 `native_temp_hum_v_values`: conservare i cinque byte

Il modulo Python descrive:

| Offset | Campo | Tipo/scala |
|---|---|---|
| 0..1 | Temperatura | int16 LE / 100, °C |
| 2 | Umidita' | uint8, %RH intera |
| 3..4 | Tensione batteria | uint16 LE / 1000, V |

`version`, unita', umidita' assoluta e dew point sono `Computed`:
**non occupano byte**. `sizeof()` restituisce 5.
Non aggiungere `33`, contatore, flag o un secondo byte H per uniformarlo
al firmware ATC: si romperebbe la compatibilita' con il protocollo originale.

Vettore verificato con il modulo Python non modificato:
`DA FD 2D B8 0B` -> **-5.50 °C, 45 %RH, 3.000 V**.

### 3.2 `native_comfort_values`: conservare sei byte e ordine high/low

| Offset | Campo | Tipo/scala |
|---|---|---|
| 0..1 | `temperature_high` | int16 LE / 100 |
| 2..3 | `temperature_low` | int16 LE / 100 |
| 4 | `humidity_high` | uint8 |
| 5 | `humidity_low` | uint8 |

Qui `version=2` e' ancora un valore virtuale, non una versione presente
nel pacchetto. Vettore verificato:
`28 0A D0 07 3C 1E` -> **T high=26, T low=20, H high=60, H low=30**.

Il comando ATC `20` e' diverso: Tmin, Tmax, Hmin, Hmax, quattro word,
otto byte. **Niente sostituzione di `native_comfort_values` con
`comfort_values`, o viceversa.**

### 3.3 Revisioni necessarie ai commenti e al routing

1. Dichiarare esplicitamente «firmware originale Xiaomi».
2. Chiarire che 53 e 66 nei commenti sono handle decimali osservati,
   non UUID e non identificativi universali.
3. Usare discovery di servizio/caratteristica e proprieta' GATT, non
   una scelta basata esclusivamente sul numero dell'handle.
4. Mantenere i due formati nativi separati dalle nuove strutture ATC.
5. Per riscritture usare solo i campi wire e verificare le proprieta'
   della caratteristica: un `Computed` non e' un parametro modificabile.

**Limite dell'evidenza:** il C esaminato non implementa quel servizio
proprietario Xiaomi. Le prove confermano struttura e comportamento
del modulo Python, non certificano tutte le revisioni del firmware
originale Xiaomi. Per cambiarne il layout servirebbero catture native
o una specifica del firmware originale.

## 4. Sezione «App Cmd internal structures»: `cfg`

### 4.1 Il commento «Firmware Version >=4.3» non basta

Il commento suggerisce una compatibilita' aperta, mentre il layout
e' quello storico. `screen_off` da 4.3 non implica che tutti gli altri
campi abbiano mantenuto significato nelle versioni successive.

Convenzioni non ambigue da documentare:

* `cfg_t` C: **11 byte**.
* Corpo logico di risposta dopo ID `55`: versione wire + `cfg_t`,
  quindi **12 byte**.
* Risposta logica intera: `55 || VERSION || CFG`, **13 byte**.
* Richiesta di scrittura: `55 || CFG`, **12 byte**.
* Il campo Python `version=Computed(1)` non e' `VERSION` del firmware.

La frase «version byte + 11 bytes» e' corretta per la dimensione logica,
ma **non** garantisce che il parser storico sia semanticamente corretto.

### 4.2 Mappa completa delle revisioni del layout

Offset della tabella: all'interno degli 11 byte C, esclusi ID e versione.

| Offset | Python storico | C corrente | Revisione |
|---|---|---|---|
| 0 | `flg` | Bitfield con alias per modello | Selezionare significato di bit 3/5 tramite profilo hardware |
| 1 | `flg2` | Smiley oppure `screen_type`, poi bit radio | Alias LCD dipendente dal modello |
| 2 | `temp_offset`, int8 /10 | `flg3` per `VERSION >=0x47` | Introdurre un layout moderno, non un alias di offset |
| 3 | `humi_offset`, int8 /10 | `event_adv_cnt` per `VERSION >=0x47` | uint8 conteggio, non percentuale |
| 4 | `advertising_interval` | uint8, passo 62.5 ms | Preservare il raw e normalizzare con vincoli C |
| 5 | `measure_interval` | uint8 moltiplicatore | Non interpretarlo come secondi |
| 6 | `rf_tx_power` | Codice radio uint8 | Mantenere enum e raw; evitare dBm arbitrari |
| 7 | `connect_latency` | Latenza periferica uint8 | Raw autorevole; secondi solo valore derivato |
| 8 | `min_step_time_update_lcd` | Intervallo LCD per i modelli che lo usano | Non applicare l'interpretazione LCD a ID estesi storici |
| 9 | `hw_cfg`: sensore + riservati + ID 4 bit | `hw_ver` uint8 ricalcolato dal firmware | Profilo storico e profilo hardware corrente distinti |
| 10 | `averaging_measurements` | uint8 | Nessun cambio binario rilevato |

Fonti:
[cfg_t](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.h#L53),
[set_hw_version](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.c#L353),
[normalizzazione](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.c#L439).
La soglia `0x47` deriva dal ramo condizionale presente nel C; non e'
una verifica di ogni binario storico mai distribuito.

### 4.3 Nuovo `flg3`, bit LSB -> MSB

| Bit | Campo | Tipo/semantica |
|---|---|---|
| 0..3 | `adv_interval_delay` | 0..15, unita' 0.625 ms |
| 4..5 | Riservati | Preservare, non usare `Padding` che li azzeri nel rebuild |
| 6 | `date_ddmm` | Opzione ordine data per il display previsto dal modello |
| 7 | `show_day_of_week` su LYWSD02MMC | 1 mostra il giorno |
| 7 | `not_day_of_week` sugli altri rami | 1 nasconde il giorno, dove supportato |

Con Construct `BitStruct` i campi si dichiarano MSB-first:
weekday, date, riservati 2 bit, delay 4 bit.
Conservare un nome raw neutro per il bit 7 e attribuirgli semantica
nel profilo, oppure usare due sottostrutture esplicitamente diverse.

`event_adv_cnt`: uint8; il commento C indica minimo 5 ma `test_config()`
porta i valori <6 a **6**. Il parser non deve scambiare il default 6
con un offset umidita' di +0.6 %.

### 4.4 Alias dei flag e identificazione hardware

| Campo wire | LYWSD03MMC e ramo classico | MJWSD05MMC/EN | LYWSD02MMC |
|---|---|---|---|
| `flg` bit 3 | `show_time_smile` | `x100` | `show_battery` |
| `flg` bit 5 | `show_batt_enabled` | `time_am_pm` | `time_am_pm` |
| `flg2` bit 0..2 | `smiley` | `screen_type` | `smiley` nel C corrente |

Non basta espandere l'enum `hw_cfg.hwver`: trattare il byte hardware
corrente come bitfield storico continuerebbe a inventare un sensore
dal bit 7 e bit riservati inesistenti.
Separare identificativo della scheda, modello del dispositivo e tipo
sensore rilevato; quest'ultimo e' ottenibile dall'identificazione `00`
e dalla risposta sensore `25`.

L'enum storico Python termina a 9. Nell'enum hardware C sono presenti
anche 10=B1.5, 11=MHO-C122, 12=MJWSD05MMC_EN, 13=MJWSD06MMC e
14=LYWSD03MMC_NB16; 15 indica `HW_VER_EXTENDED`.
Non confondere B1.6 storico (4) e NB16 (14), ne' questi valori con
il `DEVICE_TYPE` di compilazione.

### 4.5 Prova di errore semantico senza errore binario

Vettore di corpo logico moderno:
`59 87 70 0A 06 28 04 A9 31 31 00 B4`.

Il `cfg` Python attuale:

* restituisce versione 5.9;
* interpreta `0A` come `temp_offset=1.0`;
* interpreta `06` come `humi_offset=0.6`;
* riesce a ricostruire **gli stessi byte**.

Il C corrente interpreta invece delay=10 ed eventi=6.
**Un roundtrip esatto non prova la correttezza del significato dei campi.**
Le patch dei vecchi offset devono essere disabilitate nel profilo moderno.

### 4.6 Strategia di revisione proposta

Non rimuovere la compatibilita' storica:

1. Conservare il vecchio layout con nome esplicito, ad esempio
   `cfg_legacy_43`, e una compatibilita' dichiarata, non `>=4.3`.
2. Aggiungere `cfg_modern`, con `flg3`, `event_adv_cnt` e hardware raw.
3. Fare dispatch sul byte versione e sul profilo del dispositivo.
4. Usare raw uint8 autorevoli per intervalli e latenza; esporre le
   unita' umane come rappresentazioni derivate o adapter esatti.
5. Separare `cfg_response` da `cfg_write`: nella scrittura non deve
   comparire la versione firmware.
6. Conservare i bit ignoti senza presentarli come opzioni.
7. Verificare lunghezza esatta e firmware supportato prima delle patch.

Per una versione sconosciuta, una visualizzazione raw esplicitamente
non modificabile e' preferibile a una decodifica legacy apparentemente valida.

### 4.7 Il byte extra della notifica e' un problema del C, non dello schema

Nel commit fissato:

* [app_att.c](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app_att.c#L431)
  dichiara `my_RxTx_Data` lungo `sizeof(cfg)+2`;
* [ble_send_cfg](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/ble.h#L242)
  invia `sizeof(cfg)+3`.

La notifica richiesta dal C e' quindi di 14 byte, contro 13 logici.
Non aggiungere un dodicesimo campo a `cfg_t` per assorbire quel byte:
non e' una nuova opzione del protocollo e non deve essere riscritto.
Il parser diagnostico puo' esporre separatamente la coda anomala con
un errore/avviso di lunghezza; il percorso di modifica deve rifiutarla.
Verificare anche il binario reale: l'analisi riguarda quel sorgente,
non tutti i firmware installati.

## 5. Altre strutture applicative gia' presenti

### 5.1 `comfort_values`: mantenere il formato ATC da otto byte

Il C `scomfort_t` e il Python concordano su Tmin/Tmax int16 LE e
Hmin/Hmax uint16 LE, scale 1/100.
Nessuna revisione binaria necessaria per questa famiglia.
Aggiungere validazione applicativa min<=max e limiti fisici, senza
confonderla con il formato nativo da sei byte.

### 5.2 `trigger`: quattro correzioni e quattro layout

Nel C `humi_threshold` e `humi_hysteresis` sono **int16**, non uint16.
Il Python deve usare signed per entrambi; il problema pratico maggiore
e' l'isteresi negativa, che seleziona la direzione di attivazione.

`rds` completo:

* bit 0..1: `type1`;
* bit 2..3: `type2`, non `reserved_for_types`;
* bit 4: `rs1_invert`;
* bit 5: `rs2_invert`, oggi assorbito dal `Padding(3)` Python;
* bit 6..7: non descritti come opzioni, preservare raw.

Stato `flg` completo:

* bit 0 `rds1_input`, 1 `trg_output`, 2 `trigger_on`;
* bit 3 `temp_out_on`, 4 `humi_out_on`;
* bit 5 `key_pressed`, 6 `rds2_input`;
* bit 7 da preservare come non modellato.

Il C condiziona i blocchi a `SERVICE_TH_TRG` e `SERVICE_RDS`:

| TH_TRG | RDS | Corpo risposta `44`, senza ID | Blocco persistito |
|---|---|---|---|
| si' | si' | Soglie/isteresi 8 + reed 3 + stato 1 = 12 byte | Primi 11 |
| si' | no | Soglie/isteresi 8 + stato 1 = 9 byte | Primi 8 |
| no | si' | Reed 3 + stato 1 = 4 byte | Primi 3 |
| no | no | Comando non compilato | Nessuno |

Non dedurre il layout dalla sola versione: servono i servizi della build.
Il sorgente copia fino a `sizeof(trg)` e puo' accettare anche lo stato
in una scrittura, ma esclude quest'ultimo dal record persistente e
ricalcola lo stato. Il serializer di configurazione dovrebbe inviare
solo i parametri; `45` gestisce separatamente l'uscita runtime.

Prova con Python originale, corpo:
`34 08 88 13 C9 FF 9C FF 10 0E 35 60`.

* T=21, H=50, isteresi T=-0.55, isteresi H attesa=-1.
* Python produce **H hysteresis=654.36**.
* Il rebuild cambia `rds=35` in `15`: perde inversione RS2.
* Lo stato `60` diventa `00`: perde tasto e secondo ingresso.

Questo e' un difetto di informazione persa, non soltanto di etichette.
Fonte:
[trigger.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/trigger.h#L15),
[handler](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L396).

### 5.3 `device_name`, `device_type`, `i2c_devices`

* `device_name` include NUL e stringa greedy per il nome **Mi**.
  Non usarlo per il nome BLE `01`, che non ha quel prefisso obbligatorio.
* Il nome Mi ha un blocco di protocollo di 20 byte; nome BLE e nome Mi
  richiedono due serializer distinti e rispettivi limiti in byte.
* `device_type` e' in realta' un enum di alcuni **indirizzi I2C**, non
  l'ID `DEVICE_TYPE` o `ID_SENSOR_TYPES` del C.
* Aggiungere i nuovi indirizzi noti quando verificati, ma mantenere
  il valore numerico per quelli sconosciuti.
* `02` non e' una lista indistinta di dispositivi: ha slot sensore,
  display ed eventualmente RTC; 0 puo' indicare assenza, 1 display SPI.
* `03` e' invece il risultato di una scansione I2C.

Separare quindi `internal_device_addresses_response` e
`i2c_scan_response`. Conservare la convenzione indirizzi del firmware,
senza trasformare automaticamente un indirizzo a 8 bit in uno a 7 bit.
Fonte:
[handler 01/11](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L553),
[handler 02/03](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L642).

### 5.4 `mac_address`, `token_bind_mi_keys`

Il corpo MAC classico lungo 9 byte e' compatibile: lunghezza 8,
MAC[6] in ordine inverso, due byte random.
La scrittura puo' invece scegliere SIZE 6 oppure 8, oltre al reset:
modellare queste richieste separatamente dalla risposta.

`token_bind_mi_keys` resta corretto per il **contenuto assemblato**
di 28 byte: token 12 + bindkey 16. Non comprende ID/lunghezza/
frammentazione della notifica Mi. Aggiungere una struttura di frame
e reassembly nel livello protocollo, non trattare ogni frammento come
un token completo.
Il binding del nome struttura a ID e slicing e' nel client, non nel
solo modulo Construct.

### 5.5 `current_last_date`, `time_tick_step`

`23` risponde con:

* solo tempo uint32, se manca `SERVICE_TIME_ADJUST`;
* tempo corrente + ultima impostazione, due uint32, se presente.

Il Python obbliga sempre otto byte e non copre la prima variante.
La scrittura contiene invece un solo uint32.
Il C puo' aggiornare un RTC hardware: non considerare universalmente
volatile o persistente l'orologio senza profilo.

`24`: risposta uint32 assoluto tick/s, scrittura delta **int16**
rispetto a 16000000. `time_tick_step` descrive la lettura, non la
scrittura. Aggiungere `time_adjust_write` signed separato.

`Host Local Date` usa nel modulo un'espressione valutata all'import,
non una lambda valutata a ogni parse. E' un problema di metadato,
non wire: renderla dinamica o spostarla fuori dallo schema.
Fonte:
[handler 23/24](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L574).

## 6. Nuovi tracciati da aggiungere per i comandi

I nomi suggeriti sono proposte di organizzazione, non simboli gia'
presenti in `atc_mi_construct.py`. Tipi little-endian salvo indicazione.
La tabella separa la configurazione dal corpo di risposta.

| Famiglia | Nuova struttura/campi | Differenze da rispettare |
|---|---|---|
| `00` | Identificazione: revision u8, hw u16, sw u16, specific data u16, services u32 | Corpo 11 byte, ID escluso; software in formato BCD; servizi autorevoli da `app_config.h` |
| `06` | JEDEC flash ID, tre byte | Sola lettura |
| `18` | Bindkey 16 byte oppure esito assenza `FF` | Union di risposta; scrittura sempre 16 byte |
| `21` | Intervallo u32, MAC[6], bindkey[16] opzionale | Opzione dipende da `SCAN_USE_BINDKEY`, non dalla sola versione |
| `22` classico | Grande s16, piccolo s16, validita' u16, flags u8 | Scale e simboli dipendono dal display |
| `22` esteso | Numero s32, validita' u16, flags u8 | MJWSD05MMC/EN e LYWSD02MMC: non due s16 |
| `25`/`26` | K1 u32, K2 u32, Z1 s16, Z2 s16 | Risposta include ID u32, indirizzo u8, tipo u8; write coefficienti, non metadati |
| `2B`/`2C` | Coefficienti di un canale INA3221 + metadati | Non serializzare l'intero array interno di tre canali |
| `27`/`28` | MY18B20 singolo o doppio: K/Z e metadati | Attenzione a padding C e byte aggiunto dal comando 27, dettagli sotto |
| `29` | RH: K u32, Z u16, D u16 | Risposta aggiunge due ADC u16; scrittura solo coefficienti |
| `2A` | Calibrazione: subcomando; risposta esito + quattro byte dati | Non confondere due ADC u16 con un valore fisico unico u32 |
| `2D` | Radar: soglia u16, hold u16 | Configurazione condizionale XBR818 |
| `33` | Misure/ack, varianti per servizi | Non riusare il formato nativo Xiaomi; dettagli sezione 7 |
| `35` | Record logger oppure fine stream | ID, indice u16, record; fine: ID + indice zero |
| `45` | Stato trigger u8 | Non una configurazione di soglie |
| `60` | Buffer segmenti, lunghezza dipendente da LCD | Non stringa UTF-8, nessuna dimensione universale |
| `61` | Stato/controllo LCD u8 | Bit 0 ext buffer, 1 notify_on, 7 send_notify; preservare riservati |
| `68` | DAC: min/max input s16, min/max output u16 | Risposta aggiunge coefficiente derivato s32 |
| `70` | Write PIN u32; risposta esito u8 | Nessuna lettura del PIN via query generica |
| `71` | Write MTU u8; risposta esito u8 | Esito richiesta non equivale a MTU effettivamente negoziata |
| `72` | Reboot-on-disconnect; risposta esito | Azione, non configurazione persistente |
| `73` | Stato u8, indirizzo u32, dimensione KiB u32 | Write indirizzo+dimensione; distinguere eventi OTA |
| `49` | HX71X: zero u32, coeff u32, volume u32 | Risposta include **solo ADC u32** oltre alla configurazione, non `value` |

Per sensori, codice base:
[sensor.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/sensor.h#L65),
[handler coefficienti](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L692),
[handler famiglie aggiuntive](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L770).

### 6.1 Non trascrivere ciecamente i `sizeof` C in campi contigui

Alcune strutture non sono `packed`:

* `my18b20_coef_t` singolo contiene u32 + s16, sei byte di campi,
  ma puo' occupare **otto byte** con allineamento naturale;
* `memo_blk_t` contiene u32 + s16 + u16 + u16, dieci byte di campi,
  ma puo' occupare **dodici byte**.

`27` e il logger usano `sizeof` nel percorso di trasmissione.
Misurare quindi dimensioni/offset con la toolchain target, non con la
somma dei campi o con `struct.pack` senza padding.
Un controllo `ctypes` sull'host ha confermato il rischio (8 e 12),
ma **non e' una prova dell'ABI Telink**.
Per strutture che trasmettono invece una dimensione esplicita,
ad esempio `sensor_cfg_send_size=18`, prevale quel valore e il relativo
percorso di copia, non la dimensione della struttura completa in RAM.

Nel ramo `27`, `my18b20_send_size=sizeof(coef)+6`; il parser aggiunge
anche un byte finale assegnato al valore della lunghezza della risposta.
`28` usa invece `my18b20_send_size+1` come lunghezza totale.
Documentare la differenza e verificarla su cattura/build target:
non dichiarare entrambe le risposte come soli sei byte.
Fonti:
[my18b20.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/my18b20.h#L11),
[handler 27/28](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L770),
[logger.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/logger.h#L26),
[trasmissione logger](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/ble.c#L913).

### 6.2 Frame, azioni e ID senza handler

Aggiungere un livello di dispatch delle risposte, non soltanto un elenco
di `Struct` scollegate. Per esempio `56` e `DD` rispondono con `55`;
gli stream Mi e logger producono piu' frame; `33` puo' produrre prima
un ack corto.

`04` I2C, `DC` EEP e debug richiedono schemi propri solo se si vuole
esporre intenzionalmente tali API; non aggiungerli come campi `cfg`.
Gli ID `40`, `D1`, `D3`, `D4`, `D5`, `D7` dichiarati nell'enum non hanno
handler nel parser esaminato. Non dedurne un formato funzionante.
Analogamente i comandi SCD41 `2E`, `2F`, `77` del flasher separato
non sono definiti nel parser C fissato: non considerarli aggiunte
verificate dal presente confronto C/Python.

## 7. Misure ATC `33`: aggiunta necessaria, non revisione del native

La parte base TH e' copiata da `measured_data`:

| Offset nel frame intero | Campo | Tipo/scala |
|---|---|---|
| 0 | ID `33` | u8 |
| 1..2 | Batteria | u16 mV, eventualmente media |
| 3..4 | Temperatura | s16 /100 °C |
| 5..6 | Umidita' | **s16** /100 %RH |
| 7..8 | Contatore misure | u16 |
| Successivi | Estensioni | Dipendono dai servizi, nell'ordine del serializer |

Estensioni nel sorgente: stato TH trigger, CO2 SCD41, contatore reed,
illuminamento, pressione, una/due temperature MY18B20.
Per INA3221 la base ha batteria, tre correnti s16, tre tensioni u16
e contatore: 16 byte, prima delle estensioni. Per altre build elettriche
la parte base e' diversa dal termometro.

Nel ramo PLM con `USE_SENSOR_PWMRH==2` esiste inoltre `mois` prima
di `count`, mentre `MEASURED_MSG_SIZE` resta 8: non etichettare
automaticamente l'ultima word trasmessa come contatore per questa build.
Per build senza TH/IUS/PLM, la base e' solo batteria+contatore, quattro
byte; le temperature MY18B20, se previste, seguono nelle estensioni.

Non tutti gli extension block vengono trasmessi solo perche' il campo
esiste in `measured_data_t`: il serializer ha una guardia esterna su
TH_TRG/RDS/PRESSURE/18B20. La pressione trasmessa come estensione usa
due byte anche dove il campo RAM e' u32; l'illuminamento usa due byte
anche dove il valore RAM e' u32. Il modulo deve modellare il **wire
effettivo**, esponendo eventuale perdita di precisione come limite
del firmware, non inventare i byte mancanti.

`33` ha anche un ack di due byte: `33 COUNT`, dove COUNT indica lo
stato richiesto del trasferimento; non e' una misura troncata.
Richiesta e stream devono essere distinti anche dal router notifiche.
Fonti:
[measured_data_t](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/app.h#L210),
[serializer](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/ble.c#L828),
[ack](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/cmd_parser.c#L323).

Esempio sintetico TH con stato trigger:
`33 B8 0B DA FD 94 11 01 00 04`
-> batteria 3000 mV, T=-5.50 °C, H=45 %, contatore 1, flag 04.
Non applicare il parser nativo da cinque byte a questo frame.

## 8. Formati advertising: revisioni ulteriori verificate

### 8.1 ATC1441 cifrato: temperatura unsigned

Il C usa un byte **u8** per la temperatura traslata:
approssimativamente `temperatura_raw / 50 + 80`, con quantizzazione
e arrotondamento del serializer. La scala di decodifica e'
`byte/2 - 40`.

Il Python usa `ExprAdapter(Int8sl, ...)`: oltre raw 127 interpreta
il byte come negativo. Esempio di plaintext decifrato:
`A0 64 32`.

* C/semantica wire: temperatura **40 °C**, umidita' 50 %, batteria 50 %.
* Python corrente: temperatura **-88 °C**, umidita' 50 %.

La revisione richiesta e' `Int8ul` per il byte temperatura; mantenere
la trasformazione e verificare i limiti fisici/di quantizzazione.
Testare almeno raw 0, 80, 127, 128, 160, 254.
Non e' necessario cambiare nonce o algoritmo AES per correggere
questo errore del plaintext.
Fonti:
[adv_atc_data_t](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/custom_beacon.h#L82),
[serializer cifrato](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/custom_beacon.c#L32).

### 8.2 PVVX: flags opzionale e bit non piu' riservati

Il formato PVVX classico resta LE con MAC invertito, T signed
centesimi, H unsigned centesimi e batteria. Tuttavia:

* senza `SERVICE_TH_TRG`, il C riduce la lunghezza del frame di un byte
  e non invia `flags`;
* `custom_format` Python lo richiede sempre;
* quando presente, `flags` copia lo stato trigger completo:
  aggiornare `atc_flag` con key/RS2 e preservare i bit sconosciuti,
  come per `trigger.flg`;
* il PVVX cifrato include invece il byte trigger, posto a zero nel
  ramo senza TH_TRG: non rendere indiscriminatamente opzionale anche
  quel byte del plaintext cifrato.

Le lunghezze devono essere riferite allo stesso livello: l'AD completo
include lunghezza e tipo; il modulo Python comincia dall'UUID.
Dal punto di vista Python il PVVX non cifrato e' 17 byte con flags
oppure 16 senza, **UUID incluso**.
Fonte:
[pvvx_data_beacon](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/custom_beacon.c#L114).

Aggiungere inoltre gli eventi service-data `2A56` (stato digitale)
e `2AEB` (contatore a 24 bit) del ramo `default_event_beacon`.
Il serializer copia i byte contatore in ordine alto->basso:
non assumere LE solo perche' i valori PVVX TH sono LE.
Fonte:
[eventi](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/custom_beacon.c#L194).

### 8.3 BTHome v2: nuovi oggetti assenti

L'enum Python termina a `0x54`; il C definisce anche:

| ID | Nome C | Wire/fattore indicato dal C | Uso nel serializer corrente |
|---|---|---|---|
| `55` | `volume_storage` | u32, 0.001 L | Non trovato come emissione in `bthome_beacon.c` |
| `56` | `conductivity` | u16, µS/cm | Non trovato |
| `57` | `temperature8` | s8, °C | Non trovato |
| `58` | `temperature035` | s8, 0.35 °C | Non trovato; commento ID C contiene un refuso |
| `59` | `count_i8` | s8 | Non trovato |
| `5A` | `count_i16` | s16 | Non trovato |
| `5B` | `count_i32` | s32 | Non trovato |
| `5C` | `power_i32` | s32, 0.01 W | **Emesso da build elettriche** |
| `5D` | `current_i16` | s16, 0.001 A | **Emesso da build elettriche** |
| `5E` | `direction` | u16, 0.01 gradi | Non trovato |
| `5F` | `precipitation` | u16, mm | Non trovato |
| `60` | `channel` | s8 nel commento C | Non trovato |

Per i campi solo enumerati verificare anche la specifica BTHome prima
di promuoverli a supporto certificato; non tutti gli oggetti elencati
nel C vengono trasmessi da una build di termometro.
Aggiungere sia enum **sia branch `Switch`**, non solo il nome dell'ID.

Il C puo' ripetere ID temperatura, tensione, corrente, stato switch
o apertura per piu' canali: conservare lista e ordine, non ridurre
tutto a un dizionario con una sola chiave per ID.
Fonti:
[enum BTHome](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/bthome_beacon.h#L20),
[emissione](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/bthome_beacon.c#L30).

### 8.4 ID sconosciuto: non si puo' indovinare il confine BTHome

`Switch` senza default esplicito restituisce `None` per un ID
sconosciuto e non consuma il suo valore; `GreedyRange` prova quindi
a interpretare i byte del valore come nuovi ID. Un parse riuscito
puo' avere dati falsi e una coda non consumata.

Riproduzione sul Python originale:
`D2 FC 40 5D E8 03`.
Il valore corretto e' corrente signed raw 1000 -> 1 A.
Il Python produce oggetti ignoti `5D` e `E8`, senza leggere un valore
di corrente, e si ferma prima dell'ultimo byte.

Revisione proposta:

1. Default sconosciuto esplicitamente in errore.
2. Verifica di consumo completo anche **all'esterno** di `GreedyRange`,
   perche' questo intercetta gli errori del proprio elemento.
3. Nel livello diagnostico mostrare il suffisso raw non decodificabile.
4. Nel percorso dati strutturati/modifica non dichiarare successo pieno.

MiBeacon ha una lunghezza per oggetto: li' e' possibile conservare
un oggetto sconosciuto come raw con framing noto. Non importare
questa strategia in BTHome, dove l'ID sconosciuto non fornisce da
solo la lunghezza.

### 8.5 MiBeacon: aggiunte mirate, non sostituzione del parser

Il C emette un contatore reed vendor `0x20E1`, uint32 con lunghezza
oggetto 4, non presente nel dispatch Python: aggiungere enum e branch.
Aggiornare anche i nomi modello per `MJWSD05MMC=0x2832` e
`MJWSD06MMC=0x55B5`. Un device ID ignoto puo' comunque essere
conservato numericamente: e' un problema diverso da un oggetto
senza schema.

Temperature/umidita'/batteria Mi classiche non richiedono una modifica
di endian per adeguarsi al C controllato.
Non rimuovere i branch per altri dispositivi Xiaomi del fork: il
firmware ATC non e' l'intero universo dei dispositivi che il modulo
vuole supportare.
Fonti:
[mi_beacon.h](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/mi_beacon.h#L14),
[contatore evento](https://github.com/pvvx/ATC_MiThermometer/blob/b6b4c7bde322adc7538f1ec10fb32160a00df811/src/mi_beacon.c#L190).

### 8.6 Formati non da eliminare solo perche' storici

ATC1441 non cifrato resta misto endian, non tutto LE.
I formati HA/BTHome v1 possono restare per vecchi sensori anche se
il ramo C corrente usa BTHome v2.
`general_format` e' un aggregatore di alternative, non un sostituto
del framing AD: lunghezza, UUID e consumo completo devono guidare
la scelta, soprattutto se il PVVX ha flags opzionale.

## 9. Precisione, segno e separazione Python/gateway

### 9.1 Float: difetto riprodotto anche nel Python originale

L'adapter di latenza usa `int(float(x)/0.02)-1`.
Per raw 28: decode **0.58**, build restituisce raw **27**.
Quindi una patch di un campo diverso puo' cambiare la latenza se il
client ricostruisce tutta la configurazione.

Mantenere raw interi come rappresentazione autorevole, oppure usare
aritmetica decimale/razionale e validare la rappresentabilita' prima
del commit. Non sostituire indiscriminatamente ogni `int` con `round`
senza testare risoluzione, segno e fuori-range.
Gli stessi rischi riguardano altri adapter con fattori decimali.

### 9.2 Un errore del decoder Rust non dimostra un errore di Construct

Il Python originale decodifica correttamente gli int8 signed degli
offset storici. Un problema osservato nel decoder Rust generato per
un offset negativo va corretto/testato anche li', ma **non** e' una
ragione per trasformare gli offset Python signed in unsigned.

Sono due problemi distinti:

* tipo signed errato **nel Python** per ATC1441 cifrato e isteresi H;
* rispetto dei tipi signed **nell'interprete generato**, da verificare
  separatamente dalla validita' della specifica Construct.

## 10. Piano di migrazione e criteri di accettazione

1. Aggiungere profili e test prima di cambiare il nome pubblico `cfg`.
2. Preservare il vecchio layout e i parser Xiaomi nativi.
3. Implementare codec RX/TX separati per ogni comando con framing
   ID/versione/lunghezza/esito esplicito.
4. Estendere il catalogo del client: ID, slicing, write length,
   read-only, reassembly, servizi e side effect.
5. Rigenerare il YAML solo dopo aver aggiornato converter e interprete
   per ogni nuova costruzione; non modificare a mano solo il file generato.
6. Aggiornare CGI/modelli ATC: la selezione di schema deve seguire il
   profilo del peer, non restare implicitamente `cfg` storico.
7. Richiedere test di roundtrip e test di **significato**, che controllino
   campi, unita', tipo/segno e bytes scritti.
8. Validare su hardware le varianti per cui il C non basta a determinare
   ABI, lunghezza effettiva o framing storico.

### Matrice minima dei test

| Caso | Atteso dopo la revisione |
|---|---|
| Native `DAFD2DB80B` | -5.5 °C, 45 %, 3 V; cinque byte |
| Native comfort `280AD0073C1E` | high/low rispettati; sei byte |
| Legacy cfg `43851000002804A9313104B4` | Layout storico conservato, 12 byte |
| Modern cfg `5987700A062804A9313100B4` | Delay 10, eventi 6, nessun offset T/H |
| Modern cfg con coda anomala | Errore esplicito prima di una patch |
| Latenza raw 28 | Decode/build preservano 28 |
| Trigger `34088813C9FF9CFF100E3560` | H hysteresis -1; preserva inversione RS2 e stato |
| TH_TRG senza RDS, e viceversa | Layout 9/4 byte selezionati correttamente |
| Plaintext ATC1441 `A06432` | 40 °C, non -88 °C |
| PVVX senza flags | Variante riconosciuta senza inventare uno stato |
| BTHome `D2FC405DE803` | Corrente 1 A, consumo completo |
| BTHome `D2FC405C64000000` | Potenza 1 W, consumo completo |
| BTHome ignoto | Errore/coda raw esplicita, non oggetti inventati |
| ID ripetuti per piu' sensori | Conserva tutti i valori e l'ordine |
| Mi evento `E1200401000000` | Contatore vendor=1 |
| `23` con/senza TIME_ADJUST | Corpi 8/4 byte |
| `24` query/write | uint32 RX, int16 delta TX |
| `25` e altre risposte con metadati | Il write omette la coda di sola lettura |
| `27`, logger, ABI target | Lunghezze e padding verificati nella build |
| Nome BLE e nome Mi | Prefissi e limiti distinti |

Le prove gia' eseguite per questo rapporto importano il modulo Python
originale con Construct **2.10.70**, senza modificarlo, e usano soltanto
vettori sintetici offline. I fallimenti descritti sono stati riprodotti,
non ipotizzati in base ai commenti. Non sono stati eseguiti comandi BLE,
flash o scritture su dispositivi.

### Collegamenti nel gateway da aggiornare in una futura implementazione

* [Converter Construct -> YAML](tools/atc2spec.py).
* [Specifica generata](src/spec/codec.yaml).
* [Interprete codec](src/src/codec.rs).
* [Motore GATT e verifica patch](src/src/gatt.rs).
* [CGI e modelli di richiesta](files/root/usr/lib/cgi-bin/ble2uart_gateway.cgi).

La presente richiesta e' documentale: nessuno di questi componenti
e' stato modificato per implementare le revisioni proposte.

Nota sul percorso patch del gateway: `offset` e `write_offset` non
costituiscono una selezione indipendente del prefisso scrivibile.
Quando una risposta contiene metadati in coda, rimuovere solo un
prefisso non basta: occorre un serializer TX dedicato o una mappatura
RX/TX esplicita. Non pubblicare esempi di patch che riscrivano
involontariamente ID, ADC o stati come se fossero coefficienti.
