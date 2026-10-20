Non realizzerei il workflow completo in Rust, che può essere invece implementato attraverso uno script Python o bash, ma renderei possibili le funzionalità base a livello Rust (a meno che non siano tutte già disponibili); ottenute le funzionalità, implementa uno script separato (bash o python) che attui la configurazione.

Servono **notifiche GATT, non advertisements**. Nel caso ATC vengono usate per realizzare una conversazione richiesta/risposta applicativa.

### Come funziona la lettura della configurazione ATC

All’interno della **stessa connessione BLE**:

```text
Gateway → termometro: abilita le notifiche della caratteristica 0x1F1F
Gateway → termometro: scrive il comando 0x55 su quella caratteristica
Termometro → gateway: invia una notifica contenente 0x55 + configurazione
```

Per modificare la configurazione si scrive invece `0x55` seguito dai nuovi parametri e si gestisce la risposta del termometro.

Ci sono quindi tre elementi distinti:

| Elemento | Funzione |
|---|---|
| **Advertisements** | Pacchetti trasmessi senza connessione: temperatura, umidità ecc. È qui che vogliamo osservare il passaggio a Coded PHY. |
| **Risposta ATT alla scrittura GATT** | Conferma, per una scrittura *with response*, che la scrittura è stata accettata a livello GATT. Non contiene necessariamente la configurazione richiesta. |
| **Notifica GATT ATC** | Messaggio inviato dal termometro sulla connessione, contenente la risposta applicativa: per esempio la configurazione richiesta con `0x55`. |

Una notifica è dunque un meccanismo GATT normalmente asincrono; **ATC lo usa anche come canale di risposta ai comandi**. Non bisogna cercare la risposta negli advertisements.

### Quali primitive servono nel gateway

Rust deve soltanto rendere possibile allo script:

1. aprire e mantenere una connessione;
2. scoprire caratteristiche e descrittori;
3. sottoscrivere le notifiche della caratteristica scelta;
4. scrivere comandi e leggere gli eventi ricevuti, con timeout;
5. chiudere la connessione, ripristinando lo scan anche in caso di errore.

La conoscenza di `0x55`, dei campi `bt5phy`/`longrange` e della sequenza di configurazione può restare **interamente nello script Python**, come proponi.

### Perché ho menzionato il firmware ESP32

Il firmware ESP32 già inoltra notifiche ricevute come messaggi seriali `RXDATA`, ma il percorso di **registrazione automatica** che ho esaminato usa gli UUID fissi `0x00FF`/`0xFF01`, anziché quelli ATC.

La funzionalità da rendere generica è quindi **la sottoscrizione alle notifiche di una caratteristica arbitraria**, compresa l’abilitazione del suo descrittore CCCD (`0x2902`). Non serve modificare il protocollo del termometro né aggiungere nuovi tipi di advertising.

**Il risultato desiderato rimane:** lo script configura il termometro attraverso una sessione GATT; terminata la sessione, il gateway riprende lo scan e verifica negli advertisements il PHY effettivamente ricevuto.

