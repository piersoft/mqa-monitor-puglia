#!/usr/bin/env python3
"""
Restringe al perimetro pugliese gli snapshot storici ereditati dal
repository nazionale (operazione una tantum, idempotente).

storico.csv e data.json non si toccano: build_site.py li ricalcola ogni
volta dagli snapshot, quindi basta ridurre questi ultimi.

Uso:
    python3 filtra_storico.py --dry-run
    python3 filtra_storico.py
"""

import argparse
import csv
import glob
import gzip
import json
import os


def perimetro_titolari(outdir):
    with open(os.path.join(outdir, "titolari_puglia.json"), encoding="utf-8") as f:
        return {t["id"].lower() for t in json.load(f)["titolari"]}


def perimetro_org(outdir, catalog, titolari):
    """Organizzazioni che ospitano i titolari del perimetro.

    Si filtra riga per riga sul perimetro IPA e su tutti gli snapshot: un
    ente puo' aver cambiato canale nel tempo, e l'ultimo giorno da solo
    non lo direbbe.
    """
    files = sorted(glob.glob(os.path.join(outdir, "titolari", "%s_*.csv" % catalog)))
    slug = set()
    for path in files:
        with open(path, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r["id"].lower() in titolari:
                    slug.update(x for x in (r.get("via") or "").split(";") if x)
    return slug


def filtra_csv(path, tieni, secco):
    with open(path, encoding="utf-8") as f:
        r = csv.DictReader(f)
        campi, righe = r.fieldnames, list(r)
    resta = [x for x in righe if tieni(x)]
    if not secco and len(resta) != len(righe):
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campi)
            w.writeheader()
            w.writerows(resta)
    return len(righe), len(resta)


def filtra_gz(path, tieni, secco):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        r = csv.DictReader(f)
        campi, righe = r.fieldnames, list(r)
    resta = [x for x in righe if tieni(x)]
    if not secco and len(resta) != len(righe):
        with gzip.open(path, "wt", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=campi)
            w.writeheader()
            w.writerows(resta)
    return len(righe), len(resta)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="./mqa")
    ap.add_argument("--catalog", default="dati-gov-it")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    tit = perimetro_titolari(a.outdir)
    org = perimetro_org(a.outdir, a.catalog, tit)
    print("perimetro: %d titolari, %d organizzazioni (%s)"
          % (len(tit), len(org), ", ".join(sorted(org)[:6])))

    gruppi = [
        ("titolari", os.path.join(a.outdir, "titolari", "%s_*.csv" % a.catalog),
         filtra_csv, lambda r: r["id"].lower() in tit),
        ("organizzazioni", os.path.join(a.outdir, "organizzazioni", "%s_*.csv" % a.catalog),
         filtra_csv, lambda r: r.get("slug") in org),
        ("dataset", os.path.join(a.outdir, "dataset", "%s_*.csv.gz" % a.catalog),
         filtra_gz, lambda r: r.get("org_slug") in org),
    ]
    for nome, patt, fn, tieni in gruppi:
        files = sorted(glob.glob(patt))
        prima = dopo = 0
        for p in files:
            x, y = fn(p, tieni, a.dry_run)
            prima += x
            dopo += y
        print("  %-15s %2d file   %7d -> %6d righe" % (nome, len(files), prima, dopo))
    if a.dry_run:
        print("\n(dry-run: nessun file modificato)")


if __name__ == "__main__":
    main()
