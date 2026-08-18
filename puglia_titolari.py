#!/usr/bin/env python3
"""
Elenco dei titolari presenti nel catalogo regionale pugliese.

Ricava da dati.puglia.it/ckan la faccettatura su holder_identifier, che
contiene il codice IPA del titolare (dct:rightsHolder). E' il filtro che
definisce il perimetro di questa versione regionale di mqa-monitor.

Uso:
    python3 puglia_titolari.py
    python3 puglia_titolari.py --outdir ./mqa
"""

import argparse
import datetime as dt
import json
import os
import re
import urllib.parse
import urllib.request

CKAN_PUGLIA = "https://dati.puglia.it/ckan/api/3/action/package_search"
UA = "mqa-monitor-puglia (+https://github.com/piersoft/mqa-monitor-puglia)"
COMUNE_RE = re.compile(r"^c_[a-z]\d{3}$")
FUORI = {"m_amte"}  # titolari nazionali fuori perimetro regionale


def scarica(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def normalizza(codice):
    """Ripulisce i valori malformati: ':asl_vvta' -> 'asl_vvta'."""
    return codice.strip().strip(":").lower()


def raccogli():
    q = urllib.parse.urlencode({
        "rows": 0,
        "facet.field": '["holder_identifier"]',
        "facet.limit": 300,
    })
    d = scarica(CKAN_PUGLIA + "?" + q)["result"]
    facce = d.get("facets", {}).get("holder_identifier", {})
    if not facce:
        raise SystemExit("faccetta holder_identifier assente: verificare l'API")

    titolari = {}
    for grezzo, n in facce.items():
        cod = normalizza(grezzo)
        if cod in FUORI:
            continue
        voce = titolari.setdefault(cod, {"id": cod, "n_ckan": 0, "grezzo": []})
        voce["n_ckan"] += n
        if grezzo != cod:
            voce["grezzo"].append(grezzo)
        voce["comune"] = bool(COMUNE_RE.match(cod))

    return d["count"], sorted(titolari.values(), key=lambda x: -x["n_ckan"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="./mqa")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    totale, titolari = raccogli()
    comuni = [t for t in titolari if t["comune"]]
    out = {
        "aggiornato": dt.date.today().isoformat(),
        "fonte": CKAN_PUGLIA,
        "dataset_catalogo": totale,
        "n_titolari": len(titolari),
        "n_comuni": len(comuni),
        "titolari": titolari,
    }
    dest = os.path.join(a.outdir, "titolari_puglia.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    print("catalogo dati.puglia.it: %d dataset" % totale)
    print("titolari: %d  (comuni: %d, %d dataset)"
          % (len(titolari), len(comuni), sum(t["n_ckan"] for t in comuni)))
    print("scritto %s" % dest)


if __name__ == "__main__":
    main()
