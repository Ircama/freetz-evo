# CODEC

make/pkgs/ble2uart_gateway/tools/atc2spec.py

make/pkgs/ble2uart_gateway/src/spec/codec.yaml

make/pkgs/ble2uart_gateway/src/src/codec.rs

make/pkgs/ble2uart_gateway/src/src/main.rs

**CODEC è un piccolo motore dichiarativo di encoding/decoding in Rust, ispirato a Construct. Non è però un’emulazione al 100% della libreria Python Construct.** Bisogna distinguere la compatibilità con i formati di `atc_mi_interface` dalla compatibilità generale con Construct.

## 1. Come funziona oggi

Il percorso è questo:

```text
Definizioni Python di atc_mi_interface basate su Construct
                         │
                         ▼
                tools/atc2spec.py
             conversione durante lo sviluppo
                         │
                         ▼
                     codec.yaml
                         │
                         ▼
                interprete scritto in Rust
                         │
                  decoding / encoding
```

Il `convertitore atc2spec.py` importa gli oggetti Construct e li traduce nel vocabolario dello `schema codec.yaml`.

Sul dispositivo **non vengono eseguiti Python o Construct**.

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
