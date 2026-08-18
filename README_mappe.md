# Mappa territoriale — mqa-monitor-puglia

Mappa dei comuni pugliesi, servita come pagina statica su GitHub Pages.

Nella versione nazionale ([mqa-monitor](https://github.com/piersoft/mqa-monitor))
le mappe sono due: quella dei comuni e una coropletica delle regioni, alimentata
dal livello organizzazioni e ristretta ai cataloghi federati su dati.gov.it. Qui
il territorio è uno solo, quindi lo strato regionale è stato rimosso insieme ai
suoi dati e ai suoi filtri.

## File

| File | Ruolo | Rigenerato |
|---|---|---|
| `build_maps.py` | genera i dati della mappa | a ogni run |
| `docs/mappe.html` | pagina Leaflet | mai |
| `docs/comuni_coords.json` | centroidi e denominazioni dei comuni | una tantum |
| `docs/maps_data.json` | output di `build_maps.py` | a ogni run |

`comuni_coords.json` è una cache statica: va committata una volta e non toccata
dal workflow. Si rigenera solo quando Istat modifica i confini comunali, cioè in
pratica a ogni fusione.

## Come si compone il dato

I comuni vengono dal livello **titolari** di `docs/data.json`
(`dct:rightsHolder` più `dct:identifier`), già ristretto al perimetro pugliese da
`mqa_sparql.py`. Il codice IPA è ricondotto al codice catastale e da lì al
centroide.

L'area del cerchio è proporzionale al numero di dataset, il colore al punteggio
MQA — oppure, con il selettore, di nuovo al numero di dataset. Le due letture
sono filtrabili in modo indipendente dalla legenda.

## Codici IPA errati

Il catalogo regionale dichiara tre codici con la lettera `I` scritta `L`, che
ricondurrebbero il comune a un centroide di un'altra regione. Sono corretti in
`OVERRIDE_CODICI` dentro `build_maps.py` e segnalati alla Regione per la
correzione a monte:

| dichiarato | comune reale | dove finirebbe |
|---|---|---|
| `c_l887` | Specchia (LE) | Vignole Borbera (AL) |
| `c_l172` | Santa Cesarea Terme (LE) | Tinnura (OR) |
| `c_l115` | San Pietro in Lama (LE) | Ternate (VA) |

## Esecuzione

`build_maps.py` legge `docs/data.json`, quindi va lanciato **dopo**
`build_site.py`. Non richiede rete: nella versione nazionale interroga
`harvest_source_list` per sapere quali cataloghi regionali sono federati, qui non
serve.

    python3 build_site.py
    python3 build_maps.py
