"""platform#2253 Schritt 2 — Merkmale auf dem TRAIN-Split, eine Regel auf TEST.

Pre-Registrierung: Merkmale ausschliesslich aus dem Erstauftritts-Text (Slug +
Retro, in dem die Klasse zuerst auftrat), entwickelt NUR an Klassen mit
Erstauftritt vor 2026-07-15, bewertet ausschliesslich am Test-Split.
Erfolg = Lift >= 1,5 x Basisrate auf dem Test-Split.

Damit der Test-Split nicht durch Mehrfachprobieren verbraucht wird, waehlt
dieses Skript auf TRAIN genau EINE Regel (bestes Lift bei Mindest-Support) und
wendet sie danach EINMAL auf TEST an. Die Trainrangliste wird vollstaendig
gedruckt, auch die schlechten Zeilen.
"""

import datetime
import re
import sys

sys.path.insert(0, "/home/devuser/github/platform/tools")
import gate_wirkung as gw  # noqa: E402

HEUTE = datetime.date(2026, 8, 28)
CUT = datetime.date(2026, 7, 15)
TESTMAX = HEUTE - datetime.timedelta(days=30)
MIN_SUPPORT_TRAIN = 8

retros = gw.lies_retros(gw.standard_verzeichnisse())

occ: dict[str, list[datetime.date]] = {}
erst_retro: dict[str, tuple] = {}
for r in retros:
    d = datetime.date.fromisoformat(str(r[0])[:10])
    for s in r[1]:
        occ.setdefault(s, []).append(d)
        if s not in erst_retro or d < erst_retro[s][0]:
            erst_retro[s] = (d, r)
for v in occ.values():
    v.sort()

zeilen = []
for s, dates in occ.items():
    first = dates[0]
    if (HEUTE - first).days < 30:
        continue
    rueckfall = any(0 < (d - first).days <= 30 for d in dates[1:])
    split = "train" if first < CUT else ("test" if first <= TESTMAX else "zu-jung")
    _, retro = erst_retro[s]
    zeilen.append(
        {
            "slug": s,
            "first": first,
            "rueckfall": rueckfall,
            "split": split,
            "n_befunde": len(retro[1]),
            "gefangen": s in (retro[3] if len(retro) > 3 else []),
            "datei": retro[2],
        }
    )

MERKMALE = {
    "slug nennt eine Verneinung": lambda z: bool(
        re.search(r"(^|-)(no|not|without|missing|ohne|never|fehlt)(-|$)", z["slug"])
    ),
    "slug >= 5 Woerter": lambda z: z["slug"].count("-") + 1 >= 5,
    "slug nennt prod/deploy": lambda z: bool(re.search(r"prod|deploy|host|runner", z["slug"])),
    "slug nennt gate/check/guard": lambda z: bool(re.search(r"gate|check|guard|drill", z["slug"])),
    "slug nennt pr/merge/issue": lambda z: bool(re.search(r"\bpr-|-pr\b|merge|issue|commit", z["slug"])),
    "slug nennt test/nachweis": lambda z: bool(re.search(r"test|proof|nachweis|verify", z["slug"])),
    "Erstretro trug >= 8 Befunde": lambda z: z["n_befunde"] >= 8,
    "Erstretro trug < 5 Befunde": lambda z: z["n_befunde"] < 5,
    "beim Erstauftritt gefangen": lambda z: z["gefangen"],
    "Erstretro aus platform": lambda z: "-platform-" in z["datei"],
}


def quote(rs):
    n = len(rs)
    k = sum(1 for r in rs if r["rueckfall"])
    return n, k, (k / n if n else 0.0)


train = [z for z in zeilen if z["split"] == "train"]
test = [z for z in zeilen if z["split"] == "test"]
n_tr, k_tr, basis_tr = quote(train)
n_te, k_te, basis_te = quote(test)

print(f"TRAIN {k_tr}/{n_tr} = {basis_tr:.0%}   TEST {k_te}/{n_te} = {basis_te:.0%}")
print(f"Marge auf TEST: {1.5 * basis_te:.1%} (1,5 x Basisrate)\n")
print(f"{'Merkmal':<32}{'Support':>8}{'Quote':>8}{'Lift':>7}")
print("-" * 55)

rangliste = []
for name, f in MERKMALE.items():
    tref = [z for z in train if f(z)]
    n, k, q = quote(tref)
    lift = (q / basis_tr) if basis_tr and n else 0.0
    rangliste.append((name, n, q, lift, f))
    print(f"{name:<32}{n:>8}{q:>8.0%}{lift:>7.2f}")

geeignet = [r for r in rangliste if r[1] >= MIN_SUPPORT_TRAIN]
if not geeignet:
    print(f"\nKein Merkmal erreicht Support >= {MIN_SUPPORT_TRAIN} auf TRAIN.")
    sys.exit(0)

gewaehlt = max(geeignet, key=lambda r: r[3])
name, n, q, lift, f = gewaehlt
print(f"\nAuf TRAIN gewaehlt (einmalig, danach TEST): «{name}» — {q:.0%}, Lift {lift:.2f}")

tref = [z for z in test if f(z)]
n_s, k_s, q_s = quote(tref)
lift_te = (q_s / basis_te) if basis_te and n_s else 0.0
print(f"\nTEST-Anwendung: {k_s}/{n_s} = {q_s:.0%}  ·  Lift {lift_te:.2f}")
for z in tref:
    print(f"   {z['slug']:<52} {'JA' if z['rueckfall'] else 'nein'}")
print()
if n_s == 0:
    print("VERDIKT: Regel greift auf TEST nicht — kein Lift messbar. Kill-Gate.")
elif lift_te >= 1.5:
    print(f"VERDIKT: Marge erreicht ({lift_te:.2f} >= 1,50).")
else:
    print(f"VERDIKT: Marge verfehlt ({lift_te:.2f} < 1,50). Kill-Gate greift.")
