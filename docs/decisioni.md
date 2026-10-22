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

## 22 ottobre 2026: fornitori nuovi e metodologia index/2

| Scelta | Motivo |
|---|---|
| **Exoscale e Nebius contano nel paniere sovrano** (metodologia index/2, in vigore dal 22 ottobre). La regola sovereignty/1 non cambia: restano "controllo in revisione" e sono etichettati così ovunque. | Decisione di Massimo ("metti quelli in dubbio"). Registrata con data e motivo in `registry/methodology/index-v2.yaml`. Effetto: Nebius entra negli indici H100, H200, B200, L40S. Rischio da conoscere: un investitore o un regolatore può obiettare che Nebius è quotata al Nasdaq e ha controllate USA. |
| I fixing usano la metodologia in vigore quel giorno (index/1 fino al 21 ottobre, index/2 dal 22). | Regola dei benchmark: un cambio di metodo vale dal giorno in cui entra in vigore e non tocca la storia. |
| Nuovi collector: **Nebius** (pagina prezzi), **Lyceum** (Berlino/Zurigo, pagina prezzi), **Seeweb** (Italia, listino nello script della pagina, prezzo per GPU). | Hanno prezzi pubblici leggibili. Seeweb ha l'H100 a €1,89 per GPU-ora: verificato nel codice della pagina che il prezzo è per GPU (prezzo × numero di GPU). |
| Nuovi fornitori nel registro, senza collector per ora: STACKIT, Open Telekom Cloud, Swisscom, Phoenix Technologies (kvant), Gcore (in revisione: azionisti non pubblici), Sesterce. | STACKIT e Open Telekom Cloud pubblicano prezzi ma i loro siti non rispondono da questo PC: collector nel prossimo sprint (da GitHub probabilmente funzionano). Swisscom, kvant e Sesterce non hanno listino pubblico. |
| Fatti non verificati su un registro delle imprese marcati "provisional" (Seeweb, Lyceum, Phoenix, Sesterce, Gcore). | Onestà: il sito mostra il badge. |
| Effetto sui numeri (prova del 21 ottobre sera): CSX-H100 da €2,87 (3 fornitori) a €3,40 (6); CSX-H200 e CSX-B200 diventano pubblicabili; copertura frontier 6 su 18. | Paniere più rappresentativo. |

## 22 ottobre 2026 (sera): design 2 e sito che esegue il design

| Scelta | Motivo |
|---|---|
| Nuovo stile "neoclassico alpino": fondo chiaro color marmo, blu lapislazzuli per i sovrani, rosso porfido per gli iperscaler, oro per i dettagli. Titoli in Bodoni Moda (il carattere di Bodoni, Parma 1790), iscrizioni in Cinzel, testo in Geist. | Richiesta di Massimo: chiaro, meno testo, neoclassicismo unito ai data center, Alpi svizzere, orgoglio europeo, capibile da un investitore. Il design 1 (scuro) è in `design/archive/` (tag `design-v1`). |
| Immagini di pubblico dominio da Wikimedia Commons: Boullée (Biblioteca del Re, 1785, BnF; Cenotafio di Newton, 1784), Piranesi (Paestum, 1778), Caspar Wolf (1776), Hodler (1908, 1911), Turner (Rigi blu, 1842, Tate). Le incisioni sono ritinte in blu. | Arte europea libera da diritti, con autore e anno in didascalia e nel piè di pagina. |
| Nella home la biblioteca di Boullée "si accende": luci di rack disegnate nella prospettiva dell'incisione, con l'interruttore 1785 / 2026. | Il messaggio del progetto in un'immagine: la sala del sapere del Settecento è il data center di oggi. |
| Cinque tavole nel canvas: home, telefono, "Perché la sovranità", indice, metodo. Ogni sezione: un titolo, una frase, una visualizzazione; i numeri vengono dal ledger. | "Troppe scritte", "non si capisce niente": una idea per sezione, nell'ordine di una presentazione a investitori (problema, soluzione, prova, fiducia, piano). |
| Fatti della pagina "Perché" solo con fonte: Synergy (luglio 2025: 70% ai tre USA, 15% agli europei, 29% nel 2017), Stanford AI Index 2025 (modelli 2024: USA 40, Cina 15, Europa 3), CLOUD Act (18 U.S.C. § 2713), AWS European Sovereign Cloud (gennaio 2026, oltre €7,8 miliardi in Germania, capogruppo Amazon), NIS2, DORA, Cloud and AI Development Act (COM(2026) 502, 3 giugno 2026), EuroHPC (19 AI Factories, ottobre 2025), 76 proposte di AI Gigafactory (giugno 2025). | Un investitore deve poter controllare ogni numero. |
| **Il sito esegue gli stessi file del canvas.** Le tavole sono copiate in `site/design/`; `src/compeu/dc.py` le legge; `site/static/js/dcrun.js` (nostro) le disegna con Preact (libreria MIT da 11 KB); a ogni build i dati del canvas sono sostituiti con quelli del ledger e le immagini caricate nel canvas con i file in `site/static/img`. | Una sola fonte del design: il sito non può divergere dal canvas, e cambiare il design vuol dire copiare quattro file. Scartato: riscrivere le pagine a mano (doppio lavoro, differenze); usare il motore di Claude Design (non è nostro da distribuire). |
| Indirizzi: `/`, `/why/`, `/fixings/` (al posto di `/data/`, che ora rimanda lì; i file di dati restano in `/data/`), `/methodology/`. Aggiunti sitemap, robots, immagine di anteprima per i social, favicon. | Indirizzi chiari; i link vecchi continuano a funzionare. |
| Font e librerie ospitati sul sito, nessuna richiesta a Google. Il canvas usa Google Fonts (è l'unico modo in Claude Design). | Coerenza con la scelta del 20 ottobre sulla privacy dei visitatori. |
| Telefono: lista dei fixing a schede, grafico più stretto e alto, 9 fornitori con "mostra tutti". | Su 390 px le tabelle larghe costringevano a scorrere di lato. |
| Nuovo workflow "Site": pubblica il sito a ogni modifica del design o del codice del sito, senza raccogliere prezzi. | Prima il sito cambiava solo con la raccolta delle 05:20. |
| Rimossi il sito vecchio (CSS, JS, three.js, font) e l'opzione `compeu build --single`. | Sostituiti dal canvas, che fa da anteprima. |
| Il pulsante di contatto resta il segnaposto [CONTACT EMAIL]. | Nessun indirizzo reale ancora: va scelto da Massimo. |

## 22 ottobre 2026 (sera): nuova ricerca dei fornitori

| Scelta | Motivo |
|---|---|
| L'indice considera solo il calcolo per l'AI: GPU affittate a ore (H100, H200, B200, A100, L40S…). Dai cloud generalisti si prendono solo le offerte GPU. | Precisazione di Massimo: il sito è sul compute per l'AI, non sul cloud in generale. |
| Nuovi collector: **UpCloud** (Finlandia, Helsinki: H100 €2,17/ora, B200 €5,26/ora, spot a parte), **Leafcloud** (Olanda, Amsterdam: H100 €3,15, A100 €1,61), **IONOS** (Germania: H200 €3,00/ora per GPU, ora pubblico), **Koyeb** (Francia, di Mistral AI da febbraio 2026). | Prezzi pubblici leggibili, sede e controllo europei (fatti di UpCloud, Leafcloud e Koyeb "provvisori" finché non confermati su un registro). |
| Koyeb è sovrano ma le sue GPU grandi (H100, H200, A100) sono in Nord America: restano fuori dall'indice, che conta solo macchine in UE, SEE o Svizzera. Entra solo ciò che gira a Francoforte o Parigi. | Le due condizioni (proprietario europeo e macchina in Europa) valgono insieme. |
| "RTX 6000 (96 GB)" riconosciuta come RTX PRO 6000 Blackwell. | Nessun'altra RTX 6000 ha 96 GB: è un fatto, non una stima. |
| Senza collector, con il motivo scritto: STACKIT (il listino non dice quale GPU ha ogni server), T Cloud Public, ex Open Telekom (l'API dei prezzi non elenca le GPU H100), Gcore (la pagina non dice se i prezzi sono a consumo o con impegno), CloudFerro (il listino non dice quante GPU ha il server gpu.a100). | Regola: mai indovinare un modello di GPU o un numero di GPU. |
| Esclusi: fornitori britannici (Nscale, Fluidstack, Hyperstack, CUDO, Civo), fuori da UE e Svizzera; Northern Data/Taiga (controllata da Tether); Genesis Cloud (sito irraggiungibile, notizie di liquidazione da verificare). | Regola di sovranità; dati non verificabili. |
| Effetto previsto dal prossimo fixing (prova del 22 ottobre sera): CSX-H100 da €3,42 a €3,01 (8 fornitori); CSX-H200 €5,00 (6); CSX-B200 €7,46 (4); CSX-A100 €1,61; CSX-L40S €1,40; copertura frontier 9 su 22. | Paniere più ampio e più rappresentativo. |

## 23 ottobre 2026: design 3, Europa classica di notte

| Scelta | Motivo |
|---|---|
| Fondo scuro (#07080B), testo color marmo, oro per filetti e iscrizioni; blu #3987E5 per i sovrani e arancio #D95926 per gli iperscaler USA, coppia controllata per daltonismo e contrasto. "In revisione" è un anello vuoto blu (forma, non un terzo colore). | Richiesta di Massimo: unire Europa classica e rivoluzione dell'AI, sito "incredibilmente bello", colori a mia scelta. Il design 2 (chiaro, Alpi) è archiviato: canvas https://claude.ai/artifact/D1B6agCzC5HU8Zpp5WekYc e tag `design-v2`. |
| Niente più Svizzera nel marchio: tolte le Alpi (Hodler, Wolf, Turner), "Lugano" dalla mappa e dal piè di pagina, "Built in Switzerland". La Svizzera resta solo dove la regola la nomina (sede o controllo in UE o Svizzera); sulla mappa ha lo stesso colore dell'UE. | "Limitante e confusionario" (Massimo). La regola non cambia. |
| La home comincia dai dati: numero dell'indice per la GPU scelta (H100, H200, B200, A100, L40S), confronto con gli iperscaler USA, mappa 3D a tutta larghezza. Le spiegazioni sono in fondo (come funziona, registro, roadmap, contatto). | Richiesta esplicita: "all'inizio meglio mettere i dati dell'indice", "la mappa della versione scura era bellissima". |
| Mappa ripresa dalla versione 1 e resa "classica": colonne di luce con capitello e base, reticolo di meridiani e paralleli, nomi latini (EVROPA, MARE ATLANTICVM…) distesi sul terreno. Prezzo o controllo, trascinamento, scheda al passaggio, profilo al clic. Il terreno è disegnato in una cache e ridisegnato solo quando la vista cambia. | Interattività della v1; prestazioni su telefoni e PC lenti. |
| Grafici dell'indice ridisegnati: tabellone per GPU con ogni quotazione visibile (punto per fornitore, fascia dei prezzi sovrani, fixing sovrano e USA collegati, rapporto "2,05×"), su una scala comune per livello (frontier, data centre); storico con mirino e tabella; barre di tutti i fornitori con le due linee dei fixing. Una sola scelta di GPU guida tutta la pagina. | "La parte grafica dell'indice è importantissima": si vede da cosa nasce ogni numero, non solo il numero. |
| Statue come nuvole di 52.000 punti di luce (WebGL, senza librerie): Venere di Milo (calco dell'SMK di Copenaghen, scansione 3D di pubblico dominio) nella home, Augusto (Musée Saint-Raymond, Tolosa, scansione CC0) nella pagina "Perché". File in `site/static/3d/`. Con "riduci movimento" restano ferme. | L'unione tra scultura classica e dati, in tre dimensioni e interattiva ("il sito era troppo 2D"). |
| Incisioni ritinte oro su nero: Biblioteca del Re di Boullée (registro), Paestum di Piranesi (metodo); Cenotafio di Newton di Boullée in cornice dorata ("Perché"). Pagina "Perché" con Bodin (1576) e la pace di Vestfalia (1648) nella cronologia. | Identità europea classica senza riferimenti nazionali. |
| `_sites` del sito ora ha anche A100 e L40S per sito; il preload dell'immagine di testa vale per la pagina che la usa (metodo), non sempre per la home. Nuove anteprima social e favicon scure. | Il selettore GPU muove anche la mappa; niente download inutili. |

