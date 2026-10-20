# Decisioni

Scelte fatte, con data e motivo. Le più recenti in fondo.

## 20 ottobre 2026: impostazione della fase 1

| Scelta | Motivo |
|---|---|
| Indice = **mediana** di un prezzo per fornitore (il suo on-demand più economico per GPU-ora in Europa), non media di tutti gli SKU. | Un fornitore con 40 SKU non deve pesare 40 volte; la mediana non si sposta per un valore anomalo. Esempio: €2,60, €2,83, €2,87 e un €9 anomalo: media €4,33, mediana €2,85. |
| Numero minimo di fornitori (3 sovrani, 2 iperscaler) e dati vecchi esclusi dopo 3 giorni. | Con meno fornitori l'indice non viene pubblicato: si mostra un vuoto, mai una stima. |
| Fixing definitivi: una riga per indice al giorno, mai ricalcolata. | Regola dei benchmark (IOSCO): lo storico deve restare valido anche se il metodo cambia. Serve per la fase 3. |
| Ledger in file di testo nel repository, solo in coda, con catena di hash. | Nessun database da mantenere; chiunque può verificare la storia con `git clone` e `ceresio verify`. |
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
| Nome **Ceresio** mantenuto, firma "Published from Lugano". | Il lago di Lugano dà un marchio svizzero e neutrale; il contenuto resta europeo. Nessuna croce svizzera nel logo: il suo uso commerciale è regolato dalla legge svizzera sugli stemmi. |
| GitHub Actions + GitHub Pages per partire, specchio europeo su Scaleway già nel workflow. | Costo zero subito; un indice di sovranità servito da un'azienda USA è un punto debole, da chiudere appena c'è un dominio. |
