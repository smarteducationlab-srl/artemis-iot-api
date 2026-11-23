# Documentazione pubblica API Artemis

Swagger UI legge lo snapshot locale `openapi.yaml` della [specifica pubblica
esposta dal gateway CNAF](https://iot.artemis.cnaf.infn.it/lab/openapi.yaml).
Non copiare la specifica di un branch candidato: lo stesso numero di versione
non garantisce le stesse operazioni.

Dopo un rollout CNAF, con Python 3 e PyYAML:

```sh
python3 scripts/sync-openapi.py          # verifica, senza modifiche
python3 scripts/sync-openapi.py --write  # aggiorna lo snapshot locale
git diff -- openapi.yaml                # verifica prima di pubblicare
```

Lo script esegue solo una lettura HTTPS del contratto pubblico: non richiede
token e non modifica il gateway.

La CI usa `python3 scripts/sync-openapi.py --validate-local`: controlla i
percorsi pubblici e i riferimenti dello snapshot senza dipendere da CNAF.
