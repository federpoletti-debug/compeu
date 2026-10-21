# Decisioni

Scelte fatte, con data e motivo. Le più recenti in fondo.

## 20 ottobre 2026: impostazione della fase 1

| Scelta | Motivo |
|---|---|
| Indice = **mediana** di un prezzo per fornitore (il suo on-demand più economico per GPU-ora in Europa), non media di tutti gli SKU. | Un fornitore con 40 SKU non deve pesare 40 volte; la mediana non si sposta per un valore anomalo. Esempio: €2,60, €2,83, €2,87 e un €9 anomalo: media €4,33, mediana €2,85. |
| Numero minimo di fornitori (3 sovrani, 2 iperscaler) e dati vecchi esclusi dopo 3 giorni. | Con meno fornitori l'indice non viene pubblicato: si mostra un vuoto, mai una stima. |
| Fixing definitivi: una riga per indice al giorno, mai ricalcolata. | Regola dei benchmark (IOSCO): lo storico deve restare valido anche se il metodo cambia. Serve per la fase 3. |
| Ledger in file di testo nel repository, solo in coda, con catena di hash. | Nessun database da mantenere; chiunque può verificare la storia con `git clone` e `compeu verify`. |
| Cambi BCE (tassi di riferimento giornalieri) invece del cambio fisso 1,15. | Fonte primaria e europea; il cambio usato è quello del giorno della rilevazione. |
| Stato "**under review**" oltre a sovrano/non sovrano. | Quando il controllo è conteso la regola non può decidere. Il fornitore resta visibile ma fuori da entrambi i panieri. |
| **Exoscale under review.** | Exoscale è di A1 (Vienna), ma A1 è controllata da América Móvil (Messico) con un patto con lo Stato austriaco (ÖBAG). Con la regola "proprietà in Europa" non passa in modo pulito. Va deciso da Massimo, con un parere legale. |
| **Nebius under review.** | Holding olandese, ma quotata al Nasdaq e con controllate e data center negli USA: la portata del CLOUD Act è da verificare. |
| RunPod solo come riferimento globale, mai nei panieri. | Prezzi non legati a una sede europea. Prezzi a 0,50 esatti con l'altro prezzo almeno doppio: marcati "sospetti" ed esclusi dai confronti. Le fette di GPU (MIG) sono escluse. |
| Hetzner letto dalla pagina prodotto, non dall'API Cloud. | Le GPU di Hetzner sono server dedicati (GEX), non esistono nell'API Cloud indicata nel brief. |
| Verda letto dalla sua API pubblica. | Il brief la dava come incerta: l'API `instance-types` pubblica i prezzi senza autenticazione. |
| AWS: API bulk ufficiale, file per regione scaricato solo quando AWS pubblica una nuova versione. | I file sono da circa 180 MB; la versione resta tracciata nel run. |
| Sito statico generato in Python (Jinja), JS senza framework, three.js per la mappa 3D. | Un solo linguaggio per tutto, nessun server, costo quasi zero, leggibile da chi viene dopo. |
| Font ospitati in casa, nessuna risorsa da Google. | Caricare font da Google invia dati dei visitatori a un'azienda USA (sentenza LG München, 2022): incoerente per un sito sulla sovranità. |
| Sito in inglese. | Il pubblico (provider, compratori, investitori) è europeo e internazionale. Struttura pronta per altre lingue. |
| Nome **Ceresio** mantenuto, firma "Published from Lugano". | Il lago di Lugano dà un marchio svizzero e neutrale; il contenuto resta europeo. Nessuna croce svizzera nel logo: il suo uso commerciale è regolato dalla legge svizzera sugli stemmi. (Superata il 21 ottobre: vedi sotto.) |
| GitHub Actions + GitHub Pages per partire, specchio europeo su Scaleway già nel workflow. | Costo zero subito; un indice di sovranità servito da un'azienda USA è un punto debole, da chiudere appena c'è un dominio. |

## 21 ottobre 2026: CompEU e design in Claude Design

| Scelta | Motivo |
|---|---|
| La startup si chiama **CompEU**: nome cambiato ovunque (sito, pacchetto Python `compeu`, comando `uv run compeu`, documenti). | Decisione di Massimo. |
| I codici degli indici restano CSX (sovrano) e CHX (iperscaler); cambiano solo i nomi visibili ("CompEU Sovereign H100"). | I fixing già pubblicati nel ledger usano quei codici e non si possono riscrivere. Il calcolo non cambia, quindi resta la metodologia index/1. |
| Sito progettato in Claude Design, poi portato nel codice. | Richiesta di Massimo. Il canvas ha la home interattiva (mappa 3D, laboratorio dell'indice, esploratore prezzi, copertura, test di sovranità, simulazione del ledger), la versione telefono e la metodologia. Il codice resta la fonte dell'aggiornamento giornaliero. |
| Nuova identità: logo a chip con 12 contatti in cerchio, titoli in Bricolage Grotesque, testo in Schibsted Grotesk, dati in JetBrains Mono, fondo blu notte. | Un marchio nuovo per un nome nuovo; il chip richiama il compute, il cerchio di 12 l'Europa senza copiare l'emblema UE. |
| Bug corretto: nei file YAML `NO` (Norvegia) veniva letto come `false`. Ora è tra virgolette, e un test controlla che ogni codice paese sia una stringa. | Le osservazioni del 20 ottobre per le regioni norvegesi hanno `country: false` nel ledger. Non si correggono (il ledger non si riscrive). Effetto: le regioni norvegesi erano escluse dal perimetro, che invece le prevede; nessun fixing del 20 ottobre cambia (nessuna offerta norvegese sarebbe stata la più economica). Dal run successivo il paese è giusto e la Norvegia conta, come scritto nel metodo. |
| Hetzner, collector versione 2: nomi e GPU dalla pagina (pulsante d'ordine, codici prodotto, riga delle specifiche), prezzi in euro dal file `live_data_prices.json` per data centre. | Il 21 ottobre Hetzner ha rifatto la pagina e il primo run da GitHub ha segnalato "nessun prezzo letto" (corretto: nessun dato inventato). La pagina mostra anche prezzi in dollari ai visitatori USA. Ora il risultato non dipende né dalla grafica né dal paese, e ogni data centre (Falkenstein, Norimberga, Helsinki) ha il suo prezzo. Il nuovo GEX430 ha 4 GPU: il prezzo si divide per 4 (€1,44 per GPU-ora). |
| Quando una fonte fallisce, il run conserva anche le note del parser. | Così si capisce subito che cosa è cambiato alla fonte. |
