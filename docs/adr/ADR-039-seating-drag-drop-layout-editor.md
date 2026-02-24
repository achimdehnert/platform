---
status: deprecated
date: 2026-02-21
decision-makers: Achim Dehnert
---

# ADR-039: Seating Drag & Drop Layout-Editor

_Visueller Grundriss-Editor für freie Tisch-Positionierung im Wedding Hub_

| Feld | Wert |
| --- | --- |
| **ADR-ID** | ADR-039 |
| **Titel** | Seating Drag & Drop Layout-Editor |
| **Status** | Proposed |
| **Datum** | 2026-02-16 |
| **Review-Datum** | – |
| **Autor** | Achim Dehnert / Claude AI |
| **Reviewer** | – |
| **Betrifft** | wedding-hub |
| **Related ADRs** | ADR-027 (Shared Backend Services), ADR-022 (Platform Consistency Standard) |
| **Supersedes** | – |

---

## Änderungshistorie

| Version | Datum | Änderung |
| --- | --- | --- |
| v1 | 2026-02-16 | Initialer Entwurf. Library-Vergleich (interact.js vs Konva.js vs Fabric.js), gestufter Implementierungsansatz, Backend-Endpoints, Frontend-Architektur. |
| v1.1 | 2026-02-16 | Offene Fragen Q-1 bis Q-5 entschieden: Eigene View (Q-1), Hintergrund spaeter (Q-2), konfigurierbare Dimensionen mit `width`/`height`-Feldern + Shape-Defaults (Q-5), Print-View spaeter (Q-4). Model-Erweiterung und Rollout-Plan entsprechend angepasst. |

---

## 1. Kontext und Problemstellung

### 1.1 Ausgangslage

Das Wedding Hub bietet bereits eine Sitzplatz-Verwaltung mit Gaeste-zu-Tisch-Zuweisung per SortableJS Drag & Drop. Die bestehende Loesung ordnet Gaeste Tischen zu, bietet aber **keine visuelle Raumplanung** — Tische werden als Liste dargestellt, nicht als raeumliches Layout.

Das bestehende `TablePlan`-Model enthaelt bereits vorbereitete Felder fuer eine visuelle Positionierung:

```python
class TablePlan(WeddingScopedModel):
    class Shape(models.TextChoices):
        ROUND = "round", "Rund"
        RECTANGULAR = "rectangular", "Rechteckig"
        OVAL = "oval", "Oval"
        U_SHAPE = "u_shape", "U-Form"

    name = models.CharField(max_length=50)
    shape = models.CharField(max_length=20, choices=Shape.choices, default=Shape.ROUND)
    capacity = models.PositiveSmallIntegerField(default=8)
    # Position im Canvas (fuer Drag&Drop-Editor) — UNGENUTZT
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
```

Die Felder `position_x` und `position_y` existieren, werden aber im aktuellen UI nicht genutzt.

### 1.2 Probleme

- **Keine Raumvisualisierung:** Event-Planer koennen sich die raeumliche Anordnung der Tische nicht vorstellen und muessen diese mental oder auf Papier planen.
- **Fehlende Grundriss-Zuordnung:** Es gibt keinen Bezug zwischen Tischplan und realer Location-Geometrie (Waende, Buehne, Eingang, Tanzflaeche).
- **Ungenutzte Datenfelder:** `position_x`/`position_y` sind implementiert aber wirkungslos — toter Code.
- **UX-Luecke:** Die Gaeste-Zuweisung funktioniert, aber die vorgelagerte Frage "Wo steht welcher Tisch im Raum?" bleibt unbeantwortet.
- **Kein Rotation-Support:** Rechteckige Tische und U-Form-Tische muessen drehbar sein, das Model hat kein `rotation`-Feld.

### 1.3 Ziel

Ein visueller Layout-Editor, in dem Event-Planer Tische per Drag & Drop auf einem Grundriss frei positionieren koennen — mit Snap-to-Grid, Auto-Save und nahtloser Integration in die bestehende Gaeste-Zuweisung.

---

## 2. Entscheidungskriterien

- **HTMX-Stack-Kompatibilitaet:** Loesung muss sich in den bestehenden Django + HTMX + Tailwind Stack einfuegen, ohne React/Vue-Dependency.
- **DOM-Kompatibilitaet:** Tisch-Elemente muessen als DOM-Knoten vorliegen, damit SortableJS Gaeste-Chips weiterhin funktionieren.
- **Inkrementelle Einfuehrung:** Phase 1 muss in 2-3 Tagen implementierbar sein; fortgeschrittene Features (Canvas, SVG-Import) spaeter.
- **Mobile Touch-Support:** Event-Planer arbeiten haeufig am Tablet vor Ort in der Location.
- **Performance:** Muss fluessig bleiben bei typischen Hochzeiten (10-30 Tische, bis zu 200 Gaeste).
- **Bundle Size:** Minimaler Footprint fuer die initiale Implementierung.
- **Upgrade-Pfad:** Spaeterer Wechsel zu einer Canvas-Library muss moeglich sein, ohne Backend-Aenderungen.

---

## 3. Bewertete Optionen

### 3.1 Vergleichsmatrix

| Kriterium | **Option A: CSS + interact.js** | **Option B: Konva.js** | **Option C: Fabric.js** |
| --- | --- | --- | --- |
| **Prinzip** | DOM-Elemente mit `position: absolute` | HTML5 Canvas, Scene Graph | HTML5 Canvas, Object Model |
| **Drag & Drop** | Nativ, wenig Code | Built-in, performant | Built-in + Selection Handles |
| **Tisch-Formen** | CSS Shapes + SVG Icons | Canvas Shapes (Rect, Circle) | Canvas Shapes + SVG Import |
| **Snap-to-Grid** | interact.js `snap()` Modifier | Manuell, aber einfach | Manuell |
| **Zoom/Pan** | CSS `transform: scale()` | Built-in Layer System | Built-in Viewport |
| **HTMX-Kompatibilitaet** | Perfekt (bleibt im DOM) | Gut (JSON-Sync noetig) | Gut (JSON-Sync noetig) |
| **Gaeste-Chips sichtbar** | Ja, normales HTML | Text auf Canvas | Text auf Canvas |
| **Rotation** | CSS `transform: rotate()` | Built-in | Built-in + Controls |
| **Bundle Size** | ~15 KB (interact.js) | ~140 KB | ~300 KB |
| **Lernkurve** | Sehr niedrig | Mittel | Mittel |
| **Aufwand Phase 1** | ~2-3 Tage | ~4-5 Tage | ~5-6 Tage |
| **Mobile Touch** | interact.js Touch-Support | Exzellent (Pinch-to-Zoom) | Gut |
| **Skalierung 500+ Objekte** | Eingeschraenkt (DOM-Limit) | Exzellent | Gut |
| **SVG-Grundriss-Import** | Nein | Nein (Plugin noetig) | Ja (Built-in) |

### 3.2 Option A: CSS + interact.js (DOM-basiert)

**Beschreibung:** Tische werden als `<div>`-Elemente mit `position: absolute` innerhalb eines `position: relative` Containers gerendert. Die Bibliothek interact.js (15 KB) stellt Drag & Drop mit Snap-to-Grid, Boundary-Restriction und Touch-Support bereit.

**Vorteile:**
- Bleibt vollstaendig im DOM → HTMX, SortableJS, Tailwind funktionieren weiterhin
- Gaeste-Chips sind normales HTML (keine Canvas-Text-Rendering-Probleme)
- Minimaler Lernaufwand fuer das bestehende Team
- Kleinster Bundle-Footprint (15 KB)
- Inkrementell erweiterbar

**Nachteile:**
- DOM-basiert skaliert nicht ueber ~100 Elemente hinaus
- Kein nativer SVG-Grundriss-Import
- Zoom/Pan muss manuell via CSS Transforms implementiert werden
- Keine Built-in Selection Handles fuer Resize

### 3.3 Option B: Konva.js (Canvas-basiert)

**Beschreibung:** HTML5 Canvas mit Scene-Graph-Architektur. Konva.js (140 KB, 13.7k GitHub Stars) bietet ein Layer-System, in dem ein statischer Grundriss-Layer vom interaktiven Tisch-Layer getrennt werden kann.

**Vorteile:**
- Exzellente Performance bei 500+ Objekten durch Dirty-Region-Detection
- Built-in Touch-Support inkl. Pinch-to-Zoom
- Layer-System fuer Grundriss vs. interaktive Elemente
- Gute Dokumentation mit vielen interaktiven Beispielen

**Nachteile:**
- Canvas-Rendering → SortableJS-Gaeste-Chips muessen als separate DOM-Overlay-Schicht implementiert werden
- HTMX-Integration erfordert JSON-Sync-Layer
- Groesserer Implementierungsaufwand (4-5 Tage)
- Kein SVG-Export (Dealbreaker fuer Print-Sitzplan?)

### 3.4 Option C: Fabric.js (Canvas-basiert)

**Beschreibung:** Canvas-Library mit objektorientiertem Modell (300 KB). Bietet automatische Selection Handles, SVG-Import/Export und ein umfangreiches Animationssystem.

**Vorteile:**
- Automatische Resize-/Rotations-Handles
- SVG-Import fuer Location-Grundrisse
- SVG-Export fuer druckbare Sitzplaene
- Groesste Feature-Abdeckung out-of-the-box

**Nachteile:**
- Groesster Bundle (300 KB)
- Hoechster Implementierungsaufwand (5-6 Tage)
- Dieselben DOM-Kompatibilitaetsprobleme wie Konva.js
- Overhead fuer den Wedding-Hub Use Case (Image-Editing-Features ungenutzt)

---

## 4. Entscheidung

### Gestufter Ansatz: Option A (Phase 1) → Option B (Phase 2)

**Phase 1 — interact.js (CSS/DOM-basiert):** Schneller Einstieg, der perfekt in den bestehenden HTMX-Stack passt. Gaeste-Chips, SortableJS-Zuweisung und Tailwind-Styling funktionieren ohne Anpassung weiter.

**Phase 2 — Konva.js (Canvas-basiert):** Upgrade-Option fuer komplexe Venue Maps mit Reihenbestuhlung (500+ Sitze), SVG-Grundriss-Import und Echtzeit-Kollaboration. Wird nur implementiert, wenn Phase 1 an DOM-Performance-Grenzen stoesst.

### Begruendung

| Kriterium | Bewertung |
| --- | --- |
| HTMX-Stack-Kompatibilitaet | Option A ist die einzige Option, die vollstaendig im DOM bleibt |
| DOM-Kompatibilitaet | Option A = nativ, Option B/C = Overlay-Workaround noetig |
| Inkrementelle Einfuehrung | Option A in 2-3 Tagen, Option B/C 4-6 Tage |
| Mobile Touch-Support | Alle Optionen ausreichend, interact.js reicht fuer 10-30 Tische |
| Performance | Fuer typische Hochzeiten (10-30 Tische) ist DOM-Rendering ausreichend |
| Bundle Size | Option A = 15 KB vs. 140/300 KB — faellt ins Gewicht bei mobile |
| Upgrade-Pfad | Backend-API bleibt identisch, nur Frontend-Rendering aendert sich |

---

## 5. Technische Umsetzung

### 5.1 Model-Erweiterung

Das bestehende `TablePlan`-Model wird um drei Felder erweitert:

```python
# apps/events/models.py — TablePlan Erweiterung

# Shape-spezifische Default-Dimensionen (in Pixel fuer den Editor)
SHAPE_DEFAULTS = {
    "round":       {"width": 120, "height": 120},
    "rectangular": {"width": 160, "height": 100},
    "oval":        {"width": 160, "height": 120},
    "u_shape":     {"width": 180, "height":  80},
}

class TablePlan(WeddingScopedModel):
    # ... bestehende Felder ...

    # NEU: Rotation fuer Layout-Editor
    rotation = models.FloatField(
        default=0,
        help_text="Rotation in Grad (0-360), relevant fuer rechteckige und U-Form-Tische"
    )

    # NEU: Konfigurierbare Tisch-Dimensionen (Q-5)
    width = models.PositiveSmallIntegerField(
        default=0,
        help_text="Breite in Pixel im Editor. 0 = Shape-Default verwenden."
    )
    height = models.PositiveSmallIntegerField(
        default=0,
        help_text="Hoehe in Pixel im Editor. 0 = Shape-Default verwenden."
    )

    @property
    def display_width(self):
        return self.width or SHAPE_DEFAULTS.get(self.shape, {}).get("width", 120)

    @property
    def display_height(self):
        return self.height or SHAPE_DEFAULTS.get(self.shape, {}).get("height", 120)
```

**Migration:** Additive Migration (3 neue Felder), kein Breaking Change. Default `0`/`0`/`0` fuer alle bestehenden Tische — Properties liefern Shape-Defaults.

### 5.2 Backend-Endpoints

Zwei neue Endpoints fuer die Position-Speicherung:

```python
# apps/events/views_seating.py

@org_member_required
@require_POST
def update_table_position(request):
    """Einzelne Tisch-Position nach Drag-End speichern."""
    table_id = request.POST.get("table_id")
    pos_x = float(request.POST.get("position_x", 0))
    pos_y = float(request.POST.get("position_y", 0))
    rotation = float(request.POST.get("rotation", 0))

    table = get_object_or_404(
        TablePlan, pk=table_id,
        wedding__organization=request.organization
    )
    table.position_x = pos_x
    table.position_y = pos_y
    table.rotation = rotation
    table.save(update_fields=["position_x", "position_y", "rotation"])

    return JsonResponse({"ok": True, "table_id": str(table.pk)})


@org_member_required
@require_POST
def save_layout(request):
    """Bulk-Save aller Tisch-Positionen (Auto-Save / expliziter Save)."""
    import json
    data = json.loads(request.body)
    positions = data.get("positions", [])

    wedding = get_object_or_404(
        Wedding, organization=request.organization
    )

    updated = 0
    for pos in positions:
        updated += TablePlan.objects.filter(
            pk=pos["table_id"], wedding=wedding
        ).update(
            position_x=pos["x"],
            position_y=pos["y"],
            rotation=pos.get("rotation", 0),
        )

    return JsonResponse({"ok": True, "saved": updated})
```

**URL-Pattern (Q-1: Eigene View):**

```python
# apps/events/urls.py
urlpatterns += [
    # Layout-Editor als eigene View (Q-1)
    path("seating/layout/", views_seating.seating_layout,
         name="seating_layout"),
    # API-Endpoints fuer Position-Speicherung
    path("seating/position/", views_seating.update_table_position,
         name="update_table_position"),
    path("seating/layout/save/", views_seating.save_layout,
         name="save_layout"),
]
```

### 5.3 Frontend-Architektur

```text
┌──────────────────────────────────────────────────────────────┐
│  Layout Editor (Admin View)                                  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Canvas-Area (position: relative, overflow: hidden) │     │
│  │                                                     │     │
│  │  ┌────────┐  ┌────────────┐                         │     │
│  │  │ T1  ○  │  │   T2  ▬▬   │  ← draggable           │     │
│  │  │ (8 Pl) │  │  (12 Pl)   │    interact.js          │     │
│  │  └────────┘  └────────────┘                         │     │
│  │       ┌────────┐                                    │     │
│  │       │ T3  ○  │  ← Grid-Snap (20px)               │     │
│  │       └────────┘                                    │     │
│  └─────────────────────────────────────────────────────┘     │
│                                                              │
│  [+ Tisch hinzufuegen]  [💾 Speichern]  [Zoom: +/−]        │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐     │
│  │  Sidebar: Nicht zugeordnete Gaeste (SortableJS)     │     │
│  │  ┌─────────┐ ┌──────────┐ ┌─────────────┐          │     │
│  │  │ Max M.  │ │ Anna S.  │ │ Familie H.  │          │     │
│  │  └─────────┘ └──────────┘ └─────────────┘          │     │
│  └─────────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────────┘
```

### 5.4 interact.js Kern-Implementierung

```javascript
// static/js/layout-editor.js

(function () {
    const CSRF = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const SAVE_URL = document.getElementById('floor-plan').dataset.saveUrl;
    let isDirty = false;

    // Draggable mit Snap-to-Grid und Boundary-Restriction
    interact('.table-draggable').draggable({
        inertia: true,
        modifiers: [
            interact.modifiers.snap({
                targets: [interact.snappers.grid({ x: 20, y: 20 })],
                range: 15,
                relativePoints: [{ x: 0.5, y: 0.5 }]
            }),
            interact.modifiers.restrictRect({
                restriction: '#floor-plan',
                endOnly: true
            })
        ],
        listeners: {
            move(event) {
                const el = event.target;
                const x = (parseFloat(el.dataset.x) || 0) + event.dx;
                const y = (parseFloat(el.dataset.y) || 0) + event.dy;
                el.style.transform = `translate(${x}px, ${y}px)`;
                el.dataset.x = x;
                el.dataset.y = y;
                isDirty = true;
            },
            end(event) {
                if (isDirty) saveLayout();
            }
        }
    });

    function saveLayout() {
        const tables = document.querySelectorAll('.table-draggable');
        const positions = Array.from(tables).map(el => ({
            table_id: el.dataset.tableId,
            x: parseFloat(el.dataset.x) || 0,
            y: parseFloat(el.dataset.y) || 0,
            rotation: parseFloat(el.dataset.rotation) || 0,
        }));

        fetch(SAVE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF,
            },
            body: JSON.stringify({ positions }),
            credentials: 'same-origin',
        })
        .then(r => r.json())
        .then(data => {
            isDirty = false;
            showToast('Layout gespeichert', 'success');
        })
        .catch(() => showToast('Speichern fehlgeschlagen', 'error'));
    }

    // Zoom via Ctrl+Scroll
    const floorPlan = document.getElementById('floor-plan');
    let scale = 1;
    floorPlan.addEventListener('wheel', function (e) {
        if (e.ctrlKey) {
            e.preventDefault();
            scale = Math.min(2, Math.max(0.5, scale + (e.deltaY > 0 ? -0.1 : 0.1)));
            floorPlan.style.transform = `scale(${scale})`;
            floorPlan.style.transformOrigin = `${e.offsetX}px ${e.offsetY}px`;
        }
    });
})();
```

### 5.5 Template-Struktur

```html
<!-- templates/dashboard/events/seating_layout.html -->

<div id="floor-plan"
     class="relative bg-gray-50 border-2 border-dashed border-gray-300
            rounded-xl overflow-hidden"
     style="width: 100%; height: 600px;"
     data-save-url="{% url 'events:save_layout' %}">

    <!-- Grid Overlay -->
    <div class="absolute inset-0 pointer-events-none"
         style="background-image: radial-gradient(circle, #ddd 1px, transparent 1px);
                background-size: 40px 40px;"></div>

    {% for table in tables %}
    <div class="table-draggable absolute cursor-grab active:cursor-grabbing
                bg-white shadow-md border-2 border-gray-200 hover:border-rose-400
                flex flex-col items-center justify-center text-center transition-shadow
                {% if table.shape == 'round' %}rounded-full{% else %}rounded-xl{% endif %}"
         data-table-id="{{ table.pk }}"
         data-x="{{ table.position_x }}"
         data-y="{{ table.position_y }}"
         data-rotation="{{ table.rotation }}"
         style="transform: translate({{ table.position_x }}px, {{ table.position_y }}px)
                           rotate({{ table.rotation }}deg);
                width: {{ table.display_width }}px;
                height: {{ table.display_height }}px;">

        <span class="font-bold text-sm text-gray-800">{{ table.name }}</span>
        <span class="text-xs text-gray-500 mt-1">
            {{ table.seats.count }}/{{ table.capacity }}
        </span>
        <!-- Kapazitaets-Indikator -->
        <div class="w-8 h-1 rounded-full mt-1
            {% if table.is_full %}bg-red-400
            {% elif table.occupancy_percent > 75 %}bg-amber-400
            {% else %}bg-green-400{% endif %}">
        </div>
    </div>
    {% endfor %}
</div>
```

---

## 6. Rollout-Plan

### Phase 1: interact.js Layout-Editor (Sprint 1, ~2-3 Tage)

| Schritt | Aufgabe | Aufwand |
| --- | --- | --- |
| 1.1 | Migration: `rotation`, `width`, `height` Felder auf `TablePlan` + `SHAPE_DEFAULTS` + Properties | 1h |
| 1.2 | Backend: `seating_layout` View + `update_table_position` + `save_layout` Endpoints | 2.5h |
| 1.3 | Frontend: interact.js Integration, Snap-to-Grid, Boundary | 4h |
| 1.4 | Template: `seating_layout.html` mit Grid-Overlay, Tab-Navigation zur bestehenden Seating-Uebersicht | 2.5h |
| 1.5 | CSS: Tisch-Formen (round, rectangular, oval, U-Shape) mit konfigurierbaren Dimensionen | 1.5h |
| 1.6 | Auto-Save + Toast-Feedback | 1h |
| 1.7 | Zoom (Ctrl+Scroll) | 1h |
| 1.8 | Tests: Endpoint-Tests + manueller E2E-Test | 2h |
| **Gesamt** | | **~15.5h (~2 Tage)** |

### Phase 1b: Erweiterungen (Sprint 2, ~1-2 Tage)

| Schritt | Aufgabe | Aufwand |
| --- | --- | --- |
| 1b.1 | Rotation-Control (Drehgriff oder Kontextmenue) | 3h |
| 1b.2 | Tisch hinzufuegen / entfernen direkt im Editor | 2h |
| 1b.3 | Collision Detection (Warnung bei Ueberlappung) | 2h |
| 1b.4 | Print-View / PDF-Export des Layouts | 3h |
| **Gesamt** | | **~10h (~1.5 Tage)** |

### Phase 2: Konva.js Upgrade (bei Bedarf, ~4-5 Tage)

| Trigger fuer Phase 2 | Beschreibung |
| --- | --- |
| > 50 Tische pro Event | DOM-Performance reicht nicht mehr aus |
| SVG-Grundriss-Import | Location-Grundrisse als Hintergrund einblenden |
| Reihenbestuhlung | 500+ einzelne Sitze (Konferenz-Modus) |
| Echtzeit-Kollaboration | Mehrere Planer gleichzeitig am Layout |

**Backend bleibt identisch** — nur das Frontend-Rendering wechselt von DOM auf Canvas.

---

## 7. Risiken

| ID | Risiko | Wahrscheinlichkeit | Impact | Mitigation |
| --- | --- | --- | --- | --- |
| R-1 | interact.js wird nicht mehr maintained | Niedrig | Mittel | Library ist stabil (15 KB, wenig Bugs). Fallback: Vanilla JS Drag API |
| R-2 | DOM-Performance bei grossen Events | Niedrig | Mittel | Phase-2-Upgrade auf Konva.js. Typische Hochzeiten haben 10-30 Tische |
| R-3 | Touch-UX auf kleinen Smartphones | Mittel | Niedrig | Primaerer Use Case ist Tablet/Desktop. Smartphone: Read-only-View |
| R-4 | Concurrent Edits (mehrere Planer) | Niedrig | Hoch | Phase 1: Last-Write-Wins. Phase 2: Optimistic Locking via `updated_at` |
| R-5 | hx-boost Interferenz mit interact.js | Mittel | Mittel | `hx-boost="false"` auf Layout-Editor-Container (bekanntes Pattern, vgl. SortableJS-Fix) |

---

## 8. Offene Fragen

| ID | Frage | Status | Entscheidung |
| --- | --- | --- | --- |
| Q-1 | Soll der Layout-Editor als eigene View oder Tab in der bestehenden Seating-Uebersicht leben? | **Entschieden** | **Eigene View.** Separate Route `seating/layout/` neben der bestehenden `seating/`-Uebersicht. Verlinkung ueber Tab-Navigation. |
| Q-2 | Brauchen wir einen Hintergrund-Upload (Foto des Raumes) schon in Phase 1? | **Entschieden** | **Nein, spaeter.** Hintergrund-Upload (Location-Foto oder Grundriss) wird auf Phase 2 verschoben. |
| Q-3 | Soll die Rotation per Drag-Handle, Kontextmenue oder Eingabefeld gesteuert werden? | **Offen** | Wird in Phase 1b evaluiert. Alle drei Varianten sind mit interact.js realisierbar. |
| Q-4 | Ist ein Print-View (PDF-Export des Layouts) fuer die Location-Besichtigung erforderlich? | **Entschieden** | **Ja, aber spaeter.** Print-View/PDF-Export wird in Phase 1b oder Phase 2 umgesetzt. |
| Q-5 | Sollen Tisch-Dimensionen (Breite/Hoehe) konfigurierbar sein oder fest pro Shape? | **Entschieden** | **Ja, konfigurierbar.** Erfordert zwei neue Model-Felder (`width`, `height`) mit Shape-spezifischen Defaults. |

---

## Anhang: CDN-Referenz

```html
<!-- interact.js v1.10.x (Phase 1) -->
<script src="https://cdn.jsdelivr.net/npm/interactjs/dist/interact.min.js"></script>

<!-- Konva.js v9.x (Phase 2, nur bei Bedarf) -->
<script src="https://unpkg.com/konva@9/konva.min.js"></script>
```
