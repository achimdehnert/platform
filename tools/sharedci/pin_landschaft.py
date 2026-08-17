import base64
import re
import subprocess

REPOS = """achimdehnert/travel-beat achimdehnert/recruiting-hub achimdehnert/137-hub
achimdehnert/coach-hub achimdehnert/illustration-hub achimdehnert/pptx-hub
achimdehnert/weltenhub iilgmbh/ausschreibungs-hub iilgmbh/tax-hub achimdehnert/dev-hub
achimdehnert/apo-hub achimdehnert/onboarding-hub achimdehnert/trading-hub
achimdehnert/billing-hub achimdehnert/mcp-hub achimdehnert/dms-hub iilgmbh/risk-hub
meiki-lra/frist-hub achimdehnert/decks-hub meiki-lra/meiki-hub
iilgmbh/iil-voice-agent achimdehnert/bahn-hub achimdehnert/design-hub iilgmbh/desktop-setup iilgmbh/django-lms-lite iilgmbh/iil-fieldprefill iilgmbh/illustration-fw iilgmbh/nl2iot-hub achimdehnert/lastwar-bot achimdehnert/cad-hub achimdehnert/learn-hub achimdehnert/research-hub achimdehnert/dms-hub iilgmbh/iil-testkit""".split()


def gh(*a):
    r = subprocess.run(["gh", *a], capture_output=True, text=True)
    return r.stdout if not r.returncode else ""


gesamt = {}
for repo in REPOS:
    dateien = gh(
        "api", f"repos/{repo}/contents/.github/workflows", "-q", ".[].name"
    ).split()
    for f in dateien:
        c = gh("api", f"repos/{repo}/contents/.github/workflows/{f}", "-q", ".content")
        if not c:
            continue
        try:
            t = base64.b64decode(c).decode()
        except Exception:
            continue
        for wf, ref in re.findall(
            r"shared-ci/\.github/workflows/([\w.-]+)@([\w.\-/]+)", t
        ):
            gesamt.setdefault(wf, {}).setdefault(ref, []).append(
                f"{repo.split('/')[1]}:{f}"
            )
for wf in sorted(gesamt):
    refs = gesamt[wf]
    print(f"\n=== {wf} — {len(refs)} verschiedene Pins")
    for ref in sorted(refs):
        print(f"  {ref:<12} {len(refs[ref])}x  {', '.join(sorted(refs[ref]))[:110]}")
