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

## 23 ottobre 2026 (sera): design 3.1, Canova e Palladio

| Scelta | Motivo |
|---|---|
| Home: in apertura titolo, una tabellina compatta dei prezzi (una riga per GPU: indice sovrano, variazione del giorno, prezzo USA) e la Venere Italica di Canova in una nicchia d'oro. Un clic sulla statua (o "Prices") la trasforma nelle colonne dei prezzi della GPU scelta: una colonna per fornitore, blu i sovrani e arancio gli iperscaler USA, con le linee dei due fixing; al passaggio del mouse nome e prezzo. Cambiando GPU i punti scorrono verso le nuove colonne. | "I prezzi devono esserci perché sono il prodotto", ma più piccoli ed eleganti, con un elemento classico interattivo; unione di neoclassico (Canova) e dati. |
| La mappa passa alla sezione I, a tutta larghezza. Altezza delle colonne = prezzo: stessi pixel per euro per ogni colonna, vicina o lontana (prima c'erano un rialzo fisso e la prospettiva), con un righello in euro e il livello della colonna indicata. | Richiesta di Massimo: "le colonne della mappa non sono alte quanto i prezzi". |
| Architetture di luce disegnate nel codice (`architecture.js`): Villa La Rotonda di Palladio per "Come funziona" (quattro portici = quattro passi, la villa gira verso il passo scelto), una serliana per "La strada" (tre aperture = tre fasi, si accendono al passaggio), un tempio dorico in apertura del metodo, una trifora per i tre test di sovranità (scelto un fornitore, le luci dei test superati si accendono d'oro, quelle falliti restano buie con la cornice arancio). | "Architetture interattive che si muovono come le statue", diversificate (trifora, serliana, templi). |
| Pagina "Perché": Augusto diventa il mercato cloud europeo in 20 colonne da 5% (14 arancio USA, 3 blu europei, 3 grigie altri; Synergy Research, luglio 2025). Pagina indice: la Venere con la mela di Thorvaldsen (1809) diventa i fixing di oggi. La Venere di Milo esce dal sito. | Stessa idea su ogni pagina: la scultura classica che diventa dato. |
| Carattere dei titoli: Cormorant Garamond al posto di Bodoni Moda (Cinzel per le iscrizioni, Geist per il testo). Nuovo logo: un frontone su tre colonne che salgono come un grafico, la prima blu (sovrana); "Comp" e "EU" in corsivo. Nuove favicon e anteprima social. | "Un font esteticamente migliore"; il logo vecchio era "inguardabile": il nuovo unisce tempio classico e grafico moderno, semplice e riconoscibile. |
| Testi accorciati in tutta la home (meno spiegazioni, numeri romani per le sezioni). | "Troppe scritte". |

## 24 ottobre 2026: ricerca dei fornitori europei, CloudFerro ed evroc

| Scelta | Motivo |
|---|---|
| Nuovo collector CloudFerro: legge le tabelle prezzi ufficiali di quattro cloud (WAW3-1, WAW3-2, WAW4-1 a Varsavia, LCJ1-1 a Łódź), euro senza IVA, prezzo pay-per-use all'ora. Conta solo GPU intere: flavour passthrough il cui nome dà il numero di GPU (h100.2, gpu.h200x4) e flavour condivisi segnati "full" (una L40S o una RTX PRO 6000 intera). Le frazioni (1/2, 1/4, 1/8 di scheda) restano fuori. | Prezzi pubblici di H100 (€6,29), H200 (€7,23), L40S e RTX PRO 6000 da un fornitore sovrano. Mai indovinare quante GPU ha una macchina. |
| La tabella di Francoforte (FRA1-3) di CloudFerro non si legge: elenca gpu.a100 con 40 GB ma non dice se la VM ha una scheda intera. | Si aspetta una conferma di CloudFerro invece di supporre. |
| Nuovo collector evroc (Svezia): "On-demand GPU VM From €8 / hour / GPU" per le NVIDIA B200. "Da €8" è il prezzo on-demand più basso, cioè l'unica quotazione che l'indice prende per fornitore. Il modello si legge dal titolo della pagina (il testo cita la H100 solo per confronto). Prezzo di catalogo valido in Europa perché evroc dichiara che nessun dato esce dall'UE. | Primo prezzo pubblico di B200 da un cloud sovrano oltre ai tre già nel paniere. |
| Nuovi nel registro, senza raccolta per ora: 3DS Outscale (Francia, Dassault Systèmes; sito in manutenzione il 23 ottobre), cloudscale.ch (Svizzera; i prezzi delle RTX PRO 6000 sono calcolati dallo script della pagina, non scritti), Elastx (Svezia; solo prezzi mensili in corone), centron (Germania; prezzo della sola GPU, CPU e memoria a parte senza una VM minima). | Il registro deve elencare tutti i cloud GPU europei con prezzi pubblici, anche quando i prezzi non sono ancora confrontabili. Ognuno ha scritto perché aspetta. Il denominatore della copertura cresce: è voluto (conta tutti i sovrani). |
| Non entrano nel registro: SwissGPU (elettricità fatturata a parte), Hivenet e altri con sole GPU consumer, Cherry Servers (A100 in lista d'attesa), Cleura, flow.swiss (niente GPU a prezzo pubblico), Leaseweb (prezzi orari non trovati), Genesis Cloud (in liquidazione secondo il registro tedesco), i fornitori britannici (fuori dalla regola) e Northern Data. | Solo GPU per l'AI con un prezzo orario on-demand pubblico e comparabile. |
| UpCloud: la pagina prezzi risponde dal PC di Massimo ma dai server di GitHub riceve 403 (Cloudflare). Nessun aggiramento: il buco resta dichiarato e l'allarme parte dopo due giorni. | Da chiedere a UpCloud (lista di accesso o accordo sui dati). |

## 24 ottobre 2026: design 3.2, una home più ordinata

| Scelta | Motivo |
|---|---|
| La home racconta una storia breve: apertura con i prezzi e la Venere di Canova, poi I · dove noleggiare (la mappa, invariata), un riquadro verso l'indice completo, II · come funziona (Rotonda), III · il registro, IV · la strada (serliana), V · contatti. Tabellone, storico e barre dei fornitori restano solo nella pagina Indice, che ora apre con "I · Today". | Massimo: l'apertura è abbastanza intuitiva, "il resto è incasinato"; la mappa andava bene, il problema era l'organizzazione. |
| Il registro è la Biblioteca del Re di Boullée disegnata nel codice come ologramma di punti (navata, volta a cassettoni con lucernario, terrazze di libri, colonnato, grande arco in fondo). Sei libri sono gli ultimi sei fixing: diventano blu quando i sigilli tornano, arancioni quando un numero viene cambiato e la catena si rompe. | Massimo ama gli ologrammi di punti e la biblioteca: la verifica dei sigilli diventa visibile. |
| Una riga in apertura dice cos'è il prodotto: "A daily index for AI compute". | Si deve capire subito che cosa offre il sito. |

## 24 ottobre 2026 (sera): pagina del mercato e sfera armillare

| Scelta | Motivo |
|---|---|
| La pagina Indice diventa "The market", in stile trading: a sinistra la lista degli indici (valore, variazione, mini-grafico), a destra il grafico a candele del giorno con mirino, intervalli 5D/1M/3M/All, confronto sovrano/USA e le quotazioni come "volumi". Una candela: corpo dal fixing del giorno prima a quello del giorno, stoppino dalla quotazione più bassa alla più alta del paniere (`site.daily_bars`, dai fixing sigillati). | Massimo: una parte del sito dedicata ai grafici del prezzo nel tempo, tipo trading, unita alla pagina dell'indice. |
| Tolti dal sito la tabella "Sources", le note "come leggiamo i prezzi", il link alla fonte nei profili, la matrice dei prezzi per fornitore e la sezione dei download. Il registro e i dati restano nel repository. | Massimo: i dati sui fornitori e sul modo di raccoglierli sono proprietari, il sito non deve renderli espliciti. |
| La copertura dei fornitori sovrani è una sfera armillare olografica: ogni fornitore è una stella posta nel cielo secondo la sua sede; accesa se pubblica un prezzo di GPU frontier, pallida se pubblica prezzi senza GPU frontier, anello vuoto se non pubblica prezzi. Passando sopra una stella se ne legge il nome, cliccando si apre il profilo. | Mostrare dati simili in modo meno esplicito, più interattivo e classico-moderno. |
| Il meandro greco del piè di pagina diventa un circuito su cui corre una luce; le colonne del logo "respirano" al passaggio del mouse. | Piccole interazioni classico-moderno. |

## 24 ottobre 2026 (sera): fornitori trovati sui siti di confronto

| Scelta | Motivo |
|---|---|
| Cercati nuovi fornitori sovrani sui siti di confronto dei prezzi GPU che usano i concorrenti (getdeploying.com, gpus.io, computeprices.com, flopper.io, vpsbenchmarks.com) e verificati sulle pagine dei fornitori stessi. Nel registro 7 nuovi: Beyond.pl (Polonia, gruppo Kulczyk), Trooper.AI (Germania), Hostinger (sede a Cipro, controllo lituano), Hexabyte (Svezia), SwissGPU (Lugano), Green AI Cloud (Svezia) e Impossible Cloud (Amburgo). Totale 40: 30 sovrani, 5 in revisione, 5 non sovrani. | I concorrenti leggono le stesse fonti pubbliche (pagine prezzi e API dei fornitori); i loro elenchi servono a scoprire nomi, mai come fonte di un prezzo. |
| Nessuno dei nuovi ha un prezzo che l'indice può già leggere: Beyond.pl, Green AI Cloud e Impossible Cloud pubblicano solo prezzi con contratto (riservati); Hostinger non dice in che paese sono le GPU; Trooper.AI non dice se l'IVA è inclusa né il paese di ogni server; SwissGPU fa pagare l'elettricità a parte (CHF 0,30/kWh); Hexabyte ha le L4 in lista d'attesa. Ognuno ha la sua nota nel registro. | Regola 2: niente prezzi indovinati o resi confrontabili con ipotesi. |
| Green AI Cloud è "in revisione": l'8 ottobre 2026 ha firmato la fusione con Pioneer Acquisition I Corp, che si trasferisce nel Delaware; dopo la chiusura (prevista nel secondo trimestre 2027) sarebbe controllata da una società americana. Impossible Cloud è "in revisione" perché le quote dei soci (tra cui Protocol Labs, americana) non sono pubbliche. | Fatti sul controllo contestati o sconosciuti = in revisione (regola sovereignty/1). |
| Hikube ora pubblica i prezzi delle GPU (CHF al mese per scheda, ad ore = mese ÷ 730), ma la GPU si aggiunge a una VM pagata a parte, come centron. Sesterce ora pubblica prezzi a richiesta, ma di capacità rivenduta da altri cloud con nome nascosto (le immagini citano Shadeform, un marketplace americano). Entrambi restano "planned". | Servono due regole che spettano a Massimo: come contare GPU + VM minima (Hikube, centron), e se la capacità rivenduta di un operatore sconosciuto può essere sovrana (Sesterce). |
| Genesis Cloud (Germania) non è nel registro: il sito non risponde (errore 522) e un concorrente scrive che la società è in liquidazione. | Da ricontrollare più avanti. |

## 24 ottobre 2026 (sera): grafico a linea e meccanismo di Anticitera

| Scelta | Motivo |
|---|---|
| Il grafico della pagina "The market" diventa una linea: un punto per fixing, scala da zero, sotto ogni punto una colonna di luce alta quanto il prezzo (un colonnato sotto il suo architrave). Tratteggiata la linea dell'altro paniere; un giorno senza fixing resta vuoto. Passando sopra un giorno: valore, variazione, quotazioni, rapporto con l'altro paniere e cosa è cambiato nel paniere (losanga d'oro); sotto il grafico gli "Annals" elencano questi cambiamenti. Il dato è `days` in `site.py` (`index_days`), al posto delle candele (`ohlc`). | Massimo: le candele non sono intuitive. La scala da zero rende onesta l'altezza delle colonne e mostra subito quanto costano di più gli iperscaler USA. |
| "Behind today's price" apre con il meccanismo di Anticitera (il più antico computer conosciuto, greco) disegnato in punti di luce: ogni ruota è la quotazione di un cloud, con area proporzionale al prezzo, le ruote di ogni paniere ordinate dalla più economica; la ruota d'oro in mezzo è la mediana; un filo di luce porta ogni ruota al suo prezzo sulla scala in euro. Trascinando si girano le ruote. Le liste delle quotazioni restano, chiuse sotto "All N quotes". | Nuova idea classico-moderno chiesta da Massimo: Europa, calcolo e AI in un solo oggetto, meno tabelle in vista. |
