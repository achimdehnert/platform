# DROP DEBUGGING GUIDE

## SCHRITT 1: BROWSER-KONSOLE CHECKEN

1. Öffne `/reader/book/3/chapter/1/` in Chrome/Edge
2. Drücke F12 → Console Tab
3. Lade Seite neu
4. Schaue nach diesen Meldungen:

**ERWARTETE AUSGABEN:**

✅ **Wenn alles OK:**
```
Drop zone initialized for chapter: 123
```

❌ **Wenn Chapter nicht in DB:**
```
No chapter ID available for drop zone
```

❌ **Wenn Drop-Zone fehlt:**
```
No drop zone found
```

---

## SCHRITT 2: DRAG TESTEN

1. Öffne `/bookwriting/illustrations/gallery/`
2. F12 → Console
3. Klicke und ziehe ein Bild
4. Schaue in Console

**ERWARTETE AUSGABE:**
```
💡 Tip: Drag images to chapter pages to assign them!
```

---

## SCHRITT 3: ELEMENT INSPEKTION

1. Auf Chapter-Reader-Seite
2. F12 → Elements Tab
3. Suche nach: `class="image-drop-zone"`
4. Prüfe `data-chapter-id` Attribut

**SOLLTE SO AUSSEHEN:**
```html
<div class="image-drop-zone" data-chapter-id="123" style="...display: none;">
```

---

## SCHRITT 4: NETZWERK-REQUEST CHECKEN

1. Ziehe Bild auf Chapter-Seite
2. F12 → Network Tab
3. Schaue nach POST zu `/illustrations/api/assign-to-chapter/`

**MÖGLICHE FEHLER:**
- 403 Forbidden → CSRF-Problem
- 404 Not Found → URL falsch
- 500 Server Error → Backend-Problem

---

## HÄUFIGE PROBLEME:

### Problem: "No chapter ID available"
**Ursache:** Chapter existiert nicht in Datenbank  
**Lösung:** Chapter muss als BookChapters-Objekt existieren

### Problem: Drop-Zone erscheint nicht
**Ursache:** JavaScript nicht geladen oder Fehler  
**Lösung:** Schaue in Console nach Fehlern

### Problem: "CSRF token missing"
**Ursache:** CSRF-Cookie fehlt  
**Lösung:** Prüfe Cookie in Application Tab

---

## BITTE SENDE MIR:

1. **Console-Ausgaben** (Screenshot oder Text)
2. **Fehlermeldungen** (rot in Console)
3. **Network Request Status** (wenn Drop ausgeführt)
