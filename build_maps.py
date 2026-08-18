#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_maps.py - genera docs/maps_data.json per le due mappe del monitoraggio MQA.

  Mappa puntuale COMUNI -> livello TITOLARI (dct:rightsHolder + dct:identifier)

Enti centrali, agenzie, partecipate, universita', ASL, consorzi: esclusi.

Dipendenze: solo stdlib.
Input : docs/data.json, docs/comuni_coords.json
Output: docs/maps_data.json
"""

import json
import os
import re
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(HERE, "docs")
DATA_JSON = os.path.join(DOCS, "data.json")
COORDS_JSON = os.path.join(DOCS, "comuni_coords.json")
OUT_JSON = os.path.join(DOCS, "maps_data.json")


# Titolare comunale con codice IPA formalmente valido: c_ + catastale (lettera + 3 cifre)
RE_IPA_COMUNE = re.compile(r"^c_[a-z]\d{3}$", re.I)
# Titolare il cui nome dichiara un comune ma il cui identificativo e' fuori standard
RE_NOME_COMUNE = re.compile(r"^(comune|citta|citt\u00e0)\b", re.I)
# Le Citta' metropolitane sono enti di area vasta, non comuni: fuori dalla mappa
RE_AREA_VASTA = re.compile(r"^citt[a\u00e0]\s+metropolitana", re.I)

# Comuni soppressi o denominazioni non risolvibili: mappatura manuale.
# None = da escludere (ente non piu' esistente).
OVERRIDE_COMUNI = {
    "comune di genova - musei e biblioteche": "c_d969",
    "comune di vodo di cadore": "c_m108",
    "comune di lentiai": None,          # fuso in Borgo Valbelluna (2019)
    "comune di castellavazzo": None,    # fuso in Longarone (2016)
    "comune di santa caterina d'este": None,  # non e' un comune
}

# Codici IPA errati riscontrati sui titolari: correzione verso il codice reale.
# None = ente soppresso, il dato non viene mappato.
OVERRIDE_CODICI = {
    "c_l390": "c_i390",   # San Vincenzo (LI)
    "c_l344": "c_i344",   # Sant'Ippolito (PU)
    "c_f633": "c_f653",   # Monte Urano (FM)
    "c_e667": "c_m312",   # Lonato del Garda (BS)
    "c_f474": None,       # Monteciccardo, fuso in Pesaro (2024)
    "c_969": "c_d969",    # Genova
    "c_cp112": "c_m323",  # Castelfranco Piandiscò
    # errori nel catalogo regionale pugliese: I letta come L
    "c_l887": "c_i887",   # Specchia (LE), non Vignole Borbera (AL)
    "c_l172": "c_i172",   # Santa Cesarea Terme (LE), non Tinnura (OR)
    "c_l115": "c_i115",   # San Pietro in Lama (LE), non Ternate (VA)
}


def norm(s):
    """Normalizzazione per il confronto fra denominazioni."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z]", "", s.lower())


def norm_comune(s):
    """Normalizzazione specifica per i nomi di comune."""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"^(comune|citta|city)\s+(di|del|della|dello|delle|dei|d')?\s*", "", s.strip())
    s = re.sub(r"\s*-\s*(istituzione|servizio|ufficio|settore|direzione|area|dipartimento).*$", "", s)
    return re.sub(r"[^a-z]", "", s)


def carica_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------
# Mappa 1 - comuni (livello titolari)
# --------------------------------------------------------------------------

def costruisci_comuni(data, coords):
    enti = data["livelli"]["holder"]["enti"]

    per_nome = {}
    for cod, v in coords.items():
        per_nome.setdefault(norm_comune(v[2]), []).append(cod)

    acc = {}
    scartati = []

    def risolvi(ente):
        ident = ente["id"].strip()
        low = ident.lower()

        if low in OVERRIDE_CODICI:
            return OVERRIDE_CODICI[low], "codice_corretto"
        if RE_IPA_COMUNE.match(ident):
            return (low, "codice_ipa") if low in coords else (None, "codice_ignoto")

        if RE_AREA_VASTA.match(ente["nome"].strip()):
            return None, "non_comune"
        if not RE_NOME_COMUNE.match(ente["nome"].strip()):
            return None, "non_comune"

        chiave = ente["nome"].strip().lower()
        if chiave in OVERRIDE_COMUNI:
            return OVERRIDE_COMUNI[chiave], "override_nome"

        cand = per_nome.get(norm_comune(ente["nome"]), [])
        if len(cand) == 1:
            return cand[0], "nome"
        return None, "ambiguo" if cand else "non_risolto"

    for ente in enti:
        cod, motivo = risolvi(ente)
        if cod is None:
            if motivo not in ("non_comune", "codice_ignoto"):
                scartati.append({"id": ente["id"], "nome": ente["nome"],
                                 "n": ente["n"], "motivo": motivo})
            continue

        lat, lon, nome, reg, prov = coords[cod]
        rec = acc.setdefault(cod, {
            "cod": cod, "nome": nome, "reg": reg, "prov": prov,
            "lat": lat, "lon": lon, "n": 0, "somma": 0.0, "fonti": [],
            "reg_cat": None,
        })
        rec["n"] += ente["n"]
        rec["somma"] += ente["media"] * ente["n"]
        rec["fonti"].append({"id": ente["id"], "n": ente["n"],
                             "mqa": ente["media"], "via": motivo})
        # se anche uno solo dei titolari ricondotti al comune arriva dal
        # catalogo della propria Regione, il comune vi e' federato
        if ente.get("reg"):
            rec["reg_cat"] = ente["reg"]

    comuni = []
    for rec in acc.values():
        if rec["n"] <= 0:
            continue
        mqa = round(rec["somma"] / rec["n"], 1)
        comuni.append({
            "cod": rec["cod"], "nome": rec["nome"], "reg": rec["reg"],
            "prov": rec["prov"], "lat": rec["lat"], "lon": rec["lon"],
            "n": rec["n"], "mqa": mqa, "rating": rating(mqa),
            "fonti": len(rec["fonti"]), "cat": rec["reg_cat"],
        })

    comuni.sort(key=lambda x: -x["n"])
    return comuni, scartati


def rating(mqa):
    if mqa is None:
        return None
    if mqa >= 351:
        return "Excellent"
    if mqa >= 221:
        return "Good"
    if mqa >= 121:
        return "Sufficient"
    return "Bad"


def main():
    print("build_maps.py - generazione dati mappe")

    data = carica_json(DATA_JSON)
    coords = carica_json(COORDS_JSON)
    print("  data.json aggiornato al %s | coordinate: %d comuni"
          % (data.get("aggiornato"), len(coords)))

    comuni, scartati = costruisci_comuni(data, coords)

    out = {
        "aggiornato": data.get("aggiornato"),
        "catalogo": data.get("catalogo"),
        "max_score": data.get("max_score", 405),
        "comuni": comuni,
        "scartati": scartati,
        "totali": {
            "comuni": len(comuni),
            "dataset_comuni": sum(c["n"] for c in comuni),
        },
    }

    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, separators=(",", ":"))

    t = out["totali"]
    print("  comuni mappati      : %d (%d dataset)" % (t["comuni"], t["dataset_comuni"]))
    print("  titolari non mappati: %d" % len(scartati))
    print("  scritto %s (%.0f KB)" % (OUT_JSON, os.path.getsize(OUT_JSON) / 1024))


if __name__ == "__main__":
    main()
