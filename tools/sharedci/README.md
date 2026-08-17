# shared-ci Pin-Werkzeuge

Entstanden am 2026-08-17 bei der Vereinheitlichung der Flotte auf `v1.1.10`
(37 PRs über ~30 Repos). **Sie liegen hier, weil sie wieder gebraucht werden:**
`iilgmbh/shared-ci` hat keinen beweglichen Major-Tag, jeder Consumer pinnt eine
Punktversion — jeder shared-ci-Fix erfordert also erneut einen Sweep.
Siehe [platform#2037](https://github.com/achimdehnert/platform/issues/2037), Befund 1.

| Skript | Zweck |
|---|---|
| `pin_landschaft.py` | Misst, welche shared-ci-Version jedes Repo in welcher Datei pinnt. Deckt **Workflows und Actions** ab — die Action-Ebene fehlte in der ersten Messung und verbarg acht Repos mit `gitleaks-scan@v1.0.0`. |
| `pin_sync.py` | Hebt **alle** shared-ci-Referenzen eines Repos auf eine Zielversion, legt Branch + Commits an. Erst `--apply` schreibt; ohne Flag Trockenlauf. |
| `pin_liste.sh` | Liest je Repo/Datei den exakt gepinnten Ref aus. Eingabe: `repo pfad` je Zeile. |

## Vor jedem Einsatz

1. **Preflight:** Input-Flächen der betroffenen Reusables zwischen altem und neuem
   Pin vergleichen — entfällt ein Input, bricht der Consumer. Am 2026-08-17 fing
   das `ghcr_push_token`, das `_deploy-unified.yml` gegenüber `v1.0.11` verloren hat.
2. **Gestaffelt mergen**, nicht im Block: neun gleichzeitige Merges haben am
   2026-07-27 über ein GHCR-Rate-Limit fünf Deploys rot gefärbt.
3. **Deploys danach gegenlesen** — `run-conclusion` allein belegt nicht, dass die
   Änderung live ist.

## Bekannte Grenze

`pin_landschaft.py` trägt eine **hartkodierte Repo-Liste**. Richtig wäre
`scripts/repo-registry.yaml` als Quelle (siehe `policies/ssot-vor-individualloesung.md`);
die Liste stammt aus dem Sweep-Tag und ist bewusst als Schuld hinterlassen, nicht
als Entwurf. Wer das Werkzeug das nächste Mal anfasst, zieht sie aus der Registry.
