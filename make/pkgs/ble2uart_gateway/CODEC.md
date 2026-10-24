# CODEC

make/pkgs/ble2uart_gateway/tools/atc2spec.py

make/pkgs/ble2uart_gateway/src/spec/codec.yaml

make/pkgs/ble2uart_gateway/src/src/codec.rs

make/pkgs/ble2uart_gateway/src/src/main.rs

CODEC (codec.rs) è un motore dichiarativo di encoding/decoding in Rust, ispirato a Construct. Non ha obiettivo di emulazione completa della libreria Python Construct e si limita alla compatibilità con i formati usati da `atc_mi_interface`.

## 1. Come funziona oggi

Il percorso è questo:

```text
Definizioni Python di atc_mi_interface basate su Construct
                         │
                         ▼
                tools/atc2spec.py
             conversione durante lo sviluppo (build)
                         │
                         ▼
                     codec.yaml
                         │
                         ▼
                interprete scritto in Rust
                         │
                  decoding / encoding
```

`codec.yaml` è incorporato nell’eseguibile (tramite `include_str!`). Non occorre quindi distribuirlo separatamente. Un eventuale `<store>/codec.yaml` esterno può aggiungere o sovrascrivere definizioni del codec incorporato. Per applicarlo al daemon serve un riavvio; modificare direttamente la copia incorporata richiede invece una ricompilazione.

Il `convertitore atc2spec.py` importa gli oggetti Construct e li traduce nel vocabolario dello `schema codec.yaml`.

### Configurazione dei sensori via GATT

Il codec include `cfg`, `trigger`, `comfort_values` e altre strutture di
`atc_mi_construct.py`, ma **non** la tabella degli ID comando e delle slice
di `atc_mi_config.py`. Non va quindi confuso con il protocollo GATT o con un
catalogo completo dei comandi supportati dalle diverse versioni dei sensori.

CLI e CGI usano lo stesso daemon per aprire una sessione host-managed,
scoprire caratteristiche e descrittori, sottoscrivere notifiche, scrivere e
attendere risposte nella stessa connessione. I comandi generici accettano
byte grezzi oppure decodificano le risposte con una struttura del codec attivo;
`patch` legge, modifica i soli campi richiesti, riscrive e verifica la risposta.

Per ATC `0x55`, `codec: "cfg"` e `offset: 1` saltano l'ID comando nella
notifica. `write_offset: 1` omette inoltre la versione firmware dalla
struttura ricodificata: la scrittura contiene `55 + parametri`, non
`55 + versione + parametri`. Questo corrisponde alla slice del client Python.
Non si presume un handle fisso per UUID `1F1F`, ne' un CCCD adiacente.

La decodifica GATT strutturata richiede il consumo completo dei byte.
Prima di applicare una patch il daemon verifica anche che il codec ricostruisca
esattamente il payload originale: code sconosciute, conversioni numeriche con
perdita o campi non rappresentabili producono un errore, non una sovrascrittura.
La decodifica degli advertisement mantiene invece la compatibilita' Construct
preesistente, compresa l'accettazione dei byte finali.

Vedere [sessioni e configurazione ATC](src/README.md#persistent-sessions-and-atc-configuration)
per CLI, limiti, timeout, ripristino SCAN/TXADV e l'esempio Coded PHY. Gli schemi
devono corrispondere al firmware installato; una risposta `0x55` corretta non
dimostra da sola che gli advertisement siano ricevuti su PHY Coded.

### Perche' lo schema e' YAML e il risultato e' JSON?

Sono due oggetti diversi, non due formati concorrenti per lo stesso pacchetto:

- **Lo schema YAML descrive come leggere e scrivere i byte:** strutture,
  lunghezze, tipi, scale, condizioni e formati supportati. E' un file di
  definizioni, leggibile e modificabile durante lo sviluppo; YAML permette
  anche commenti.
- **Il JSON di Discovery/Inspect rappresenta una singola osservazione:**
  MAC, RSSI, PHY, byte ricevuti e, quando il formato e' riconosciuto, valori
  decodificati. E' un formato di scambio comodo per GUI, JavaScript e API.
- **L'advertisement trasmesso via radio e' binario:** non e' ne' YAML ne' JSON.

```text
Construct -> atc2spec.py -> codec.yaml (regole)
                               |
advertisement binario ---------+-> decoder Rust -> valori -> JSON della GUI
```

Per esempio, una regola dello schema puo' dire "leggi un intero unsigned
little-endian a 16 bit e dividilo per 1000"; per i byte `0E 0B` il risultato
JSON del campo sara' `"battery_v": 2.83`.

La stessa specifica potrebbe essere serializzata anche in JSON, conservando
`version`, `structures` e `formats`: cambierebbe la sintassi del file, non
le regole del codec. Resterebbe comunque una specifica, non il JSON di una
misurazione. Construct non impone di usare YAML.

### Percorso inverso: schema JSON/YAML -> Python

Il programma [tools/spec2atc.py](tools/spec2atc.py) legge la specifica dichiarativa
e genera un modulo Python con vere dichiarazioni `Struct`, `Switch`, `Enum`,
`Bitwise`, adattatori e condizioni di Construct:

```sh
python3 make/pkgs/ble2uart_gateway/tools/spec2atc.py \
  --spec make/pkgs/ble2uart_gateway/src/spec/codec.yaml \
  --out /tmp/ble-codec/atc_mi_construct_generated.py
```

Accetta anche `--spec /path/to/codec.json`, con la stessa struttura
`{"version": 1, "structures": {...}, "formats": {...}}`.
`atc2spec.py` oggi scrive questa specifica in YAML.

Il risultato include i supporti di
[tools/spec2atc_runtime.py](tools/spec2atc_runtime.py), quindi si puo' copiare
senza il convertitore o il pacchetto Python originale. Servono Construct 2.10.70,
Arrow per le strutture con timestamp e PyCryptodome per usare la cifratura.
PyYAML serve solo al convertitore quando l'input e' YAML.
Il solo uso del modulo Python non richiede modifiche al gateway. Installare
una specifica con nuove proprieta' sul router richiede invece un binario
che le supporti, come precisato sotto.

Il modulo espone:

- le strutture con i nomi originali, se utilizzabili come identificatori senza
  sovrascrivere helper o built-in Python;
- `STRUCTURES`, dizionario con tutti i nomi originali, anche quelli non utilizzabili
  come identificatori;
- `FORMATS`, con le associazioni formato/struttura, UUID e metadati di rilevamento;
- `SPEC_VERSION`.

Esempio per il pacchetto BTHome v2 mostrato in Inspect:

```python
from atc_mi_construct_generated import STRUCTURES

packet = STRUCTURES["bt_home_v2_format"]
raw = bytes.fromhex("D2FC40008A0C0E0B10001101")
parsed = packet.parse(raw)
assert parsed.data_point[1].data.battery_v == 2.83
assert packet.build(parsed) == raw
```

L'input di `parse` e' il **Service Data**, a partire dall'UUID: non l'intero
advertisement con flag AD, lunghezza/tipo AD e nome. La PHY, anche Coded, non
cambia la dichiarazione del payload BTHome v2.

Per i formati cifrati passare gli stessi parametri a `parse` e `build`:
`mac_address` come 6 byte nell'ordine visualizzato e `bindkey` come 16 byte.
I nonce dei quattro codec seguono [src/src/crypto.rs](src/src/crypto.rs).
La chiave non ha un valore predefinito; un MIC non valido produce un
`construct.ValidationError` invece di misure apparentemente corrette.

**Limiti della ricostruzione:**

- Non e' una decompilazione del sorgente originale: commenti, formattazione,
  nomi degli oggetti condivisi e sorgenti delle callback non sono nello schema.
- Sono ricostruiti i calcoli noti (`absolute_humidity`, `dew_point`,
  `host_local_date`), i percorsi `this[...]`, le slice letterali, e i predicati
  `positive_timestamp`/`equals`. Non viene eseguito codice Python fornito nel JSON.
- Le trasformazioni ricostruibili sono `affine` con encoder esportato,
  `bytes2bits` e `swapbytes`. Non si inventa l'inverso di trasformazioni
  arbitrarie o prive dei parametri necessari.
- Per gli adattatori affini, `atc2spec.py` conserva anche l'espressione
  `decoder`, oltre a fattore e offset. L'ordine delle operazioni conta:
  con input `0xCF`, `(obj + 1) * 0.02` produce `4.16`, mentre la riscrittura
  `obj * 0.02 + 0.02` produce `4.159999999999999`; l'encoder puo' quindi
  produrre rispettivamente `0xCF` o `0xCE`. Le vecchie specifiche senza
  `decoder` sono leggibili, ma vanno rigenerate dall'originale per recuperare
  quell'informazione persa. La nuova proprieta' richiede un binario gateway
  aggiornato: i vecchi binari la rifiutano.
- I nodi stringa senza encoding, anonimi e con padding zero sono ricostruiti
  come `Padding`, come nei bitfield dello schema incorporato. Varianti ambigue
  con nome o padding diverso sono rifiutate.
- L'esportazione rende stringhe le chiavi dei casi di `Switch`: la selezione
  confronta la rappresentazione stringa del valore (`"True"`, `"1"`, simboli
  enum), senza inventare il tipo originale delle chiavi.
- Lo schema deve avere versione 1; nodi non mappati, callback sconosciute,
  proprieta' non riconosciute nei nodi e limiti numerici/profondita' non validi
  causano un errore con posizione nello schema. L'output viene sostituito solo
  dopo la conversione completa.

Il test [tools/test_spec2atc.py](tools/test_spec2atc.py) genera tutte le 21
strutture, confronta 400 vettori di round-trip e 600 casi di parsing/errori,
e verifica i 40 vettori crittografici, incluse manomissioni e chiavi errate.
Le differenze di rappresentazione floating point sono confrontate con tolleranza
`1e-12`; i byte ricostruiti sono confrontati esattamente. Il timestamp locale
dinamico dell'host non viene confrontato con quello salvato nel vettore.

Per evitare un controllo circolare, sono disponibili anche quattro test opzionali
contro il modello Construct originale:

```sh
ATC_CODEC_REFERENCE=/path/to/atc_mi_interface \
ATC_GENERATED_MODULE=/tmp/atc_mi_construct_corrected.py \
python3 -m unittest discover -s make/pkgs/ble2uart_gateway/tools -p test_spec2atc.py -v
```

Il riferimento verificato e' quello di
[freetz-ble-portal, revisione 722cc498](https://github.com/Ircama/freetz-ble-portal/tree/722cc498594895fffef40dd6daae6f44b4ac6119/atc_mi_interface),
non la diversa versione del pacchetto nel progetto upstream ATC_MiThermometer.
I test riesportano tutte le strutture, confrontano direttamente i modelli su
1.000 pacchetti dei vettori piu' 4.200 input indipendenti e verificano tutti
i 256 valori di ciascuno dei sette adattatori affini distinti: 1.792 casi.
In questo confronto diretto i float decodificati devono essere uguali
esattamente, non solo entro una tolleranza. Non e' comunque una prova formale
su tutti gli input e su tutte le callback possibili.

E' verificato anche il caso in cui un oggetto gia' decodificato venga modificato
e poi cifrato: i supporti generati usano lo stream corrente, non il vecchio
`_io` eventualmente conservato dal Container di Construct.

**Discrepanza nota nel riferimento, non nascosta dai test:** l'encoder originale
`BtHomeV2Codec` usa sempre `0x41` come DevInfo nel nonce. Se si attiva anche
`Trigger`, scrive `0x45` nell'header ma continua a cifrare con `0x41`, e il
decoder originale rifiuta il proprio risultato per MIC errato. Il supporto
ricostruito usa invece l'header effettivo e produce un pacchetto autenticato
valido. Il test dedicato registra questa differenza intenzionale, anziche'
dichiarare un'equivalenza assoluta o riprodurre quel difetto dell'originale.

### Note

`"Random / local address"` **non significa che il dispositivo manchi dal JSON
o dal database dei formati**. Il gateway non effettua il lookup OUI quando
`addr_type != 0` o quando l'indirizzo e' localmente amministrato.
Nel caso mostrato, `addr_type: 1` e' sufficiente per quella dicitura.
`"configured": false` indica che il dispositivo non e' nella configurazione.

**Lookup OUI.** OUI significa Organizationally Unique Identifier: un prefisso
assegnato da IEEE a un'organizzazione. Discovery usa i primi tre byte del MAC
pubblico per cercare l'assegnatario nella tabella MA-L
[src/spec/oui.tsv](src/spec/oui.tsv), incorporata nel binario. Non interroga
Internet a ogni pacchetto. L'assegnatario puo' essere il produttore del chip
o del modulo, non necessariamente il marchio del dispositivo o il suo protocollo.
La tabella viene aggiornata con [tools/update_oui.py](tools/update_oui.py).
Il lookup effettivo e' nella funzione `vendor` di [src/src/web.rs](src/src/web.rs).

**`addr_type`.** Indica come interpretare l'indirizzo BLE del trasmettitore:
`0` pubblico, `1` random nel normale caso gestito dai comandi GATT del gateway.
Arriva dal report radio ed e' estratto da [src/src/link.rs](src/src/link.rs):
non e' ricavato dal payload BTHome/PVVX, dal nome o dal vendor. Un indirizzo
random puo' essere statico o privato; random non implica che cambi a ogni
pacchetto. Nella ricezione passiva non lo si sceglie: viene riportato dal dongle.
Nei comandi GATT bisogna usare il tipo del dispositivo destinatario; un valore
sbagliato puo' impedire la connessione. Non e' un campo da aggiungere alle
misure o alle dichiarazioni Construct.

**`vendor` contro `mac_vendor`.** Non sono la stessa elaborazione:

- `vendor` di Discovery viene dal MAC del trasmettitore nel report radio e
  dalla tabella OUI; considera `addr_type`.
- `mac_vendor` del modello Construct e' un campo calcolato: uno `Switch` sui
  primi caratteri del campo `MAC` decodificato dal payload. Le associazioni
  Telink/Lumi/Tianjin e il default `Unknown vendor` sono nello schema
  [src/spec/codec.yaml](src/spec/codec.yaml). Non usa la tabella OUI completa
  e non riceve `addr_type`. Non tutti i formati hanno quel campo `MAC`.

Il MAC nel payload e quello del trasmettitore non devono necessariamente
coincidere; le due etichette possono pertanto differire.

**Indirizzo localmente amministrato.** Nella convenzione IEEE significa che
l'indirizzo e' scelto localmente, anziche' appartenere a un blocco globale
assegnato. Il bit U/L e' `0x02` del primo byte del MAC nell'ordine visualizzato;
il gateway controlla proprio quel bit. Non significa "dispositivo nella LAN".
Per BLE, il tipo random e i suoi sottotipi si interpretano secondo le regole
Bluetooth: il bit U/L IEEE non sostituisce `addr_type` e non determina da solo
se un indirizzo random e' statico o privato. La dicitura della GUI raggruppa
entrambe le condizioni per evitare attribuzioni OUI non affidabili.

**Dispositivo non configurato.** `configured: false` significa precisamente che
il MAC osservato non corrisponde a nessuna voce `devices` nella configurazione
attiva del gateway. Non significa "non abbinato Bluetooth", "non supportato"
o "assente dal codec". Discovery e Inspect possono mostrarlo comunque;
la normale pipeline non lo tratta come un sensore configurato da pubblicare
alle integrazioni. Il pulsante Configure serve a creare la voce con nome,
eventuale bindkey, misure esposte e altre impostazioni. Il flag `configured`
controlla la presenza della voce, non `enabled`: una voce disabilitata risulta
comunque configurata. Se un indirizzo privato ruota, il nuovo MAC non viene
automaticamente associato alla voce con il vecchio MAC.

## 2. In quale programma Rust si trova?

È integrato nell’eseguibile **`ble2uart-gateway`**, non è attualmente una libreria o un programma separato.

Il motore è in `codec.rs`, organizzato in moduli:

| Modulo | Funzione |
|---|---|
| `spec` | Descrive e valida lo schema YAML. |
| `value` | Rappresenta i valori decodificati. |
| `predicates` | Implementa selettori e logiche particolari provenienti dal riferimento Python. |
| `decode` | Interpreta i byte secondo lo schema. |
| `encode` | Produce i byte a partire dai valori. |

Lo schema predefinito è incorporato nell’eseguibile. Un ulteriore `codec.yaml`, accanto alla configurazione del gateway, può aggiungere o sovrascrivere strutture e formati: vedi `load_spec`.

## 3. Fa sia encoding sia decoding?

**Sì, entrambe le direzioni sono implementate**, usando lo stesso schema:

- `Decoder`: byte → valori.
- `Encoder`: valori → byte.

Sono esposte anche dalla CLI:

```text
ble2uart-gateway --decode <struttura>   # legge esadecimale da stdin, produce JSON
ble2uart-gateway --encode <struttura>   # legge JSON da stdin, produce esadecimale
```

Per le strutture cifrate, `--device <MAC>` permette di utilizzare la chiave del dispositivo configurato.

## 4. Quanto è compatibile con Construct?

### Con i formati portati da atc_mi_interface

L’obiettivo è riprodurne il comportamento e sono presenti `test di confronto con il riferimento Python`. Il test di encoding/decoding verifica **400 vettori**, e controlla la presenza di **224 casi di ramo** nei dati di prova.

Viene inoltre registrato un ramo non costruibile dal riferimento, `mi_like_data.XIAOMI_DATA_ID_Lock`.

Questo è un controllo concreto, ma **non dimostra equivalenza su tutti gli input possibili**, soprattutto quelli malformati o ai limiti. Non dichiarerei quindi “100% compatibile” senza qualificazioni.

### Con tutta la libreria Construct

**No.** L’interprete supporta un sottoinsieme: strutture, bitfield, interi, stringhe, enum, array, switch, condizioni, trasformazioni e altro.

Le limitazioni principali sono:

- non esegue lambda o callback Python arbitrarie;
- alcune logiche vengono riprodotte manualmente in `predicates`;
- il linguaggio delle espressioni è limitato;
- non implementa tutto il catalogo di Construct, per esempio un sistema generale di puntatori/seek o parsing lazy;
- esistono limiti espliciti su profondità, dimensioni e larghezza degli interi.

**Nuove composizioni di operazioni già supportate possono essere aggiunte nel solo YAML; nuove operazioni richiedono codice Rust.**

## 5. Usa librerie Rust che mappano Construct?

**No: il mapping e l’interprete sono nostri.**

Nel `Cargo.toml`:

- `serde` e `serde_yaml` caricano lo schema, ma non interpretano i formati binari;
- `serde_json` gestisce la rappresentazione JSON;
- `aes`, `ccm` e `aead` forniscono la crittografia.

Non c’è una dipendenza Rust che fornisca una traduzione generale di Construct.

## 6. Potrebbe diventare una sorta di Construct in Rust?

**Sì: il nucleo esiste già.** Lo definirei oggi un **interprete di schemi binari bidirezionale, specializzato nei protocolli ATC/Xiaomi/BTHome**.

Per renderlo una libreria riutilizzabile separerei:

1. **Motore generale**: schema, valori, espressioni, encoder e decoder.
2. **Estensioni di dominio**: MAC, crittografia BLE, calcoli e predicati specifici.
3. **Convertitore Construct → schema**: strumento opzionale di sviluppo.
4. **Suite di compatibilità**: casi validi, errori, input troncati, limiti numerici e round-trip.

La direzione più realistica sarebbe **“un’alternativa dichiarativa a Construct in Rust, con importazione di un sottoinsieme di Construct”**, non una promessa di compatibilità totale con qualsiasi programma Construct/Python.
