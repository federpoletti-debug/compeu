# CLAUDE.md: CompEU

Istruzioni per Claude Code, lette all'inizio di ogni sessione.

## Il progetto

- **CompEU** (fino al 21 ottobre 2026 si chiamava Ceresio Index): indice giornaliero del prezzo del compute GPU sovrano europeo, con sede a Lugano.
- Il sito è progettato in Claude Design: canvas "CompEU" https://claude.ai/artifact/TmU5uVTA8s9GRMcLzgrKA7 (home desktop, telefono, metodologia). Il codice del sito segue quel design.
- Cartella locale: `Desktop/ceresio-index` (nome vecchio, il repository GitHub è `federpoletti-debug/compeu`).
- Fase 1 (questo repository): raccolta prezzi, classificazione sovrano/non sovrano, sito statico che si aggiorna da solo.
- Fase 2 (intermediazione fisica) e fase 3 (derivati cash-settled) sono roadmap: **non costruirle**. I derivati richiedono licenze (FinIA/MiFID) e un amministratore di benchmark autorizzato (BMR). Dati e metodo sono già pensati per non doverli rifare.
- Concorrente diretto: Era Compute (era.dev). Noi ci differenziamo su sovranità = controllo societario, onestà dei dati, ledger verificabile.

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
uv run compeu build --single    # un solo file HTML (anteprime, Artifact)
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

## Stato al 21 ottobre 2026

- Primo fixing reale il 20 ottobre 2026: CSX-H100 €2,87 (OVHcloud, Scaleway, Verda), CHX-H100 €7,02 (AWS, Azure). Copertura frontier: 3 sovrani su 9.
- 8 collector attivi: Scaleway, OVHcloud, Hetzner, Verda, Exoscale, AWS, Azure, RunPod.
- Repository locale, non ancora su GitHub: il workflow giornaliero parte solo dopo il primo push.

## Prossimi passi

1. Creare il repository GitHub (o Codeberg), push, attivare Pages; aggiornare `repo` in `site/site.yaml`.
2. Dominio e hosting europeo (Scaleway Object Storage già previsto nel workflow).
3. Decidere Exoscale e Nebius (oggi `under_review`): servono i fatti sul controllo.
4. Collector: Nebius (pagina prezzi), Google Cloud (chiave API gratuita), IONOS, AWS European Sovereign Cloud.
5. Contatti con Infomaniak, Polarise, Safe Swiss Cloud, Hikube per dati di Livello 2.
