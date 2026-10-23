# CLAUDE.md: CompEU

Istruzioni per Claude Code, lette all'inizio di ogni sessione.

## Il progetto

- **CompEU** (fino al 21 ottobre 2026 si chiamava Ceresio Index): indice giornaliero del prezzo del compute GPU sovrano europeo, con sede a Lugano.
- Il sito è progettato in Claude Design: canvas "CompEU" https://claude.ai/artifact/TmU5uVTA8s9GRMcLzgrKA7 (home, telefono, perché la sovranità, indice, metodo). Il sito esegue proprio quelle tavole: sono copiate in `site/design/` (vedi "Sito e design").
- Cartella locale: `Desktop/ceresio-index` (nome vecchio, il repository GitHub è `federpoletti-debug/compeu`).
- Fase 1 (questo repository): raccolta prezzi, classificazione sovrano/non sovrano, sito statico che si aggiorna da solo.
- Fase 2 (intermediazione fisica) e fase 3 (derivati cash-settled) sono roadmap: **non costruirle**. I derivati richiedono licenze (FinIA/MiFID) e un amministratore di benchmark autorizzato (BMR). Dati e metodo sono già pensati per non doverli rifare.
- Concorrente diretto: Era Compute (era.dev). Noi ci differenziamo su sovranità = controllo societario, onestà dei dati, ledger verificabile.
- Tesi e sviluppo del business (23 ottobre 2026): documento Claude https://claude.ai/artifact/RbbdVAeQjx8AAAu3fCJ819. In fase 1 solo link dichiarati verso i fornitori e richieste di offerta inoltrate, niente rivendita; passaggio alle fasi 2 e 3 solo superando i "cancelli" scritti nel documento.

## Tre regole non negoziabili

1. **"Sovrano" = sede legale e controllo in UE o Svizzera, fuori dalla portata del CLOUD Act.** Non la posizione dei server. La regola è in `registry/rules/sovereignty-v1.yaml`; lo stato si calcola dai fatti in `registry/providers.yaml`, mai scritto a mano. Cambiare la regola = nuovo file `sovereignty-v2.yaml`.
2. **Mai inventare, interpolare o riportare avanti un prezzo.** Dato mancante = gap dichiarato.
3. **Il ledger (`ledger/`) si scrive solo in coda.** Mai modificare o cancellare una riga. `uv run compeu verify --against <ref>` lo controlla; la CI lo blocca.

## Come lavorare con Massimo

- Rispondi in italiano, frasi brevi e semplici. Il primo termine tecnico va spiegato con un esempio numerico.
- Codice, commenti, nomi e testi del sito in inglese.
- Massimo vuole lavoro autonomo: scegli il default migliore, procedi, e a fine lavoro elenca cosa non hai potuto fare. Chiedi solo per scelte che spettano a lui (legali, commerciali, account, pubblicazione).
- Ogni scelta non ovvia va in `docs/decisioni.md` (data, scelta, motivo).

## Comandi

```bash
uv sync --system-certs           # ambiente (Avast su questo PC: serve --system-certs)
uv run compeu daily             # cambi BCE + raccolta + fixing del giorno
uv run compeu classify          # stato di sovranità di ogni fornitore
uv run compeu build             # sito in dist/
uv run compeu verify            # controlla le catene di hash
uv run pytest; uv run ruff check .; uv run ruff format .
```

Su questo PC Windows: `UV_PYTHON_INSTALL_DIR="$USERPROFILE/.uv/python"` prima dei comandi uv (l'app Claude virtualizza AppData).
Le prove che scaricano dati vanno fatte con `COMPEU_ROOT` che punta a una copia di `registry/` in una cartella temporanea, per non scrivere righe di prova nel ledger vero.

## Regole del codice

- Un collector per fornitore in `src/compeu/collectors/`: `fetch()` fa la rete, `parse()` è puro e testato su risposte reali ridotte.
- Nessun valore indovinato: nome GPU sconosciuto = `unmapped` e nota nel run; prezzo senza valuta = scartato e segnalato.
- Parametri del metodo in `registry/methodology/`, impostazioni del sito in `site/site.yaml`.
- Prima di ogni commit: `uv run pytest`, `uv run ruff check .`, `uv run ruff format .`.
- Nessun push se Massimo non lo chiede.
- Il ledger lo scrive GitHub ogni mattina (05:20 UTC, commit di `compeu-bot`): **prima di lavorare, `git pull`**, e non lanciare `compeu daily` in locale sul ramo main (creerebbe righe in conflitto con quelle del bot).
- `gh` (GitHub CLI) è in `C:\Program Files\GitHub CLI\gh.exe` e funziona solo dallo strumento PowerShell (il login è nel keyring di Windows).

## Sito e design

- Ogni pagina è una tavola di Claude Design (`site/design/*.dc.html`, copia esatta del file `project/*.dc.html` del canvas). `src/compeu/dc.py` la legge; `site/static/js/dcrun.js` la disegna nel browser con Preact; `compeu build` mette i dati del ledger al posto di quelli del canvas e i file di `site/static/img` al posto delle immagini caricate (`site/design/assets.yaml`).
- Per cambiare il design: modificare il canvas, rileggere le tavole (Artifact read di `project/<nome>.dc.html`), copiarle in `site/design/`, `uv run compeu build`, test, commit, push: il workflow Site pubblica. Un'immagine nuova nel canvas va aggiunta anche in `assets.yaml` e `site/static/img/`.
- Nelle tavole: niente `{{...}}` dentro `<text>` SVG (non si vede), link tra pagine scritti come `Why.dc.html`, dati solo dentro `const D = ...;` su una riga.
- Il design 3 usa WebGL per statue e architetture (`site/static/3d/*.json` per le scansioni, edifici generati nel codice delle tavole) e un canvas 2D per la mappa; i colori dei dati sono controllati per daltonismo (blu #3987E5 sovrani, arancio #D95926 USA, anello vuoto per "in revisione"). Nella mappa l'altezza delle colonne è il prezzo (stessi pixel per euro, righello in euro). Una statua nuova va caricata nel canvas come asset e aggiunta in `assets.yaml` e `site/static/3d/`.

## Stato al 22 ottobre 2026

- Primo fixing reale il 20 ottobre 2026: CSX-H100 €2,87 (OVHcloud, Scaleway, Verda), CHX-H100 €7,02 (AWS, Azure). Copertura frontier: 3 sovrani su 9.
- 17 collector: Scaleway, OVHcloud, Hetzner, Verda, Exoscale, Nebius, Lyceum, Seeweb, UpCloud, Leafcloud, IONOS, Koyeb, CloudFerro, evroc, AWS, Azure, RunPod (dal 24 ottobre CloudFerro ed evroc; UpCloud bloccato da Cloudflare sui server di GitHub). 33 fornitori nel registro (25 sovrani, 3 in revisione, 5 non sovrani); in attesa di prezzi confrontabili: Outscale, cloudscale, Elastx, centron, STACKIT, T Cloud Public, Gcore. Solo GPU per l'AI, mai cloud generico.
- Metodologia index/2 dal 22 ottobre 2026: Exoscale e Nebius (controllo in revisione) contano nel paniere sovrano per decisione di Massimo.
- Repository pubblico https://github.com/federpoletti-debug/compeu, CI verde, raccolta giornaliera attiva, Pages su https://federpoletti-debug.github.io/compeu/.
- Design 3 (scuro, "Europa classica di notte": mappa 3D con colonne di luce, statue a punti di luce, incisioni oro su nero, niente Svizzera nel marchio) online dal 23 ottobre: le pagine del sito sono le tavole del canvas, con i dati di ogni mattina. Design 1 e 2 archiviati (tag `design-v1`, `design-v2`). Primo fixing con index/2: CSX-H100 €3,42, CHX-H100 €7,00. Dalla sera del 23 ottobre design 3.1: titoli in Cormorant Garamond, logo tempio-grafico, Venere Italica di Canova che diventa i prezzi in apertura, mappa nella sezione I, Rotonda e serliana di Palladio, tempio e trifora nel metodo, Augusto che diventa il mercato, Venere di Thorvaldsen nell'indice.

## Prossimi passi

1. Indirizzo di contatto vero al posto di [CONTACT EMAIL] (tavole Main, poi build).
2. Dominio e hosting europeo (Scaleway Object Storage già previsto nel workflow).
3. Exoscale e Nebius contano per decisione (index/2): confermare i fatti sul controllo con un parere.
4. Collector: STACKIT e Open Telekom Cloud (da GitHub rispondono), Google Cloud (chiave API gratuita), IONOS, AWS European Sovereign Cloud.
5. Contatti con Infomaniak, Polarise, Safe Swiss Cloud, Hikube per dati di Livello 2.
