---
title: "[Konzepttitel]"
id: "CONCEPT-XXX"
status: "draft"  # draft | review | accepted | superseded
date: YYYY-MM-DD
author: [Achim Dehnert]
related_adrs: []
tags: []
---

# [Konzepttitel]

> **Zweck**: Konzeptpapiere sind *pre-ADR*-Dokumente. Sie analysieren eine Technologie,
> ein Muster oder eine Integration *bevor* eine Entscheidung getroffen wird.
> Ein Konzeptpapier mündet entweder in ein ADR oder wird als "nicht weiterverfolgt" archiviert.
>
> **Abgrenzung zu ADRs**: ADRs dokumentieren *getroffene* Entscheidungen.
> Konzeptpapiere dokumentieren *Analyse und Optionen* vor der Entscheidung.

---

## 1. Executive Summary

> 3–5 Sätze: Was wird analysiert, warum ist es relevant, was ist die Kernaussage?

---

## 2. Motivation und Problemkontext

### 2.1 Ausgangssituation

> Welches Problem oder welche Lücke soll adressiert werden?

### 2.2 Relevante bestehende ADRs

| ADR | Titel | Relevanz |
|-----|-------|----------|
| ADR-XXX | ... | ... |

### 2.3 Nicht-Ziele

> Was wird in diesem Konzept explizit *nicht* behandelt?

---

## 3. Technologie- / Konzept-Analyse

### 3.1 Überblick

### 3.2 Kernfähigkeiten

| Fähigkeit | Beschreibung | Relevanz für Platform |
|-----------|-------------|----------------------|
| ... | ... | hoch / mittel / niedrig |

### 3.3 Architektur / Funktionsweise

### 3.4 Einschränkungen und Risiken

| Einschränkung | Schwere | Mitigation |
|---------------|---------|------------|
| ... | HIGH/MEDIUM/LOW | ... |

---

## 4. Integrations-Szenarien

### Szenario A — [Name] (Empfohlen)

**Beschreibung**: ...
**Aufwand**: LOW / MEDIUM / HIGH
**Nutzen**: ...
**Abhängigkeiten**: ...

### Szenario B — [Name]

**Beschreibung**: ...

### Szenario C — Nicht integrieren

**Begründung**: ...

---

## 5. Bewertungsmatrix

| Kriterium | Gewicht | Szenario A | Szenario B | Szenario C |
|-----------|---------|------------|------------|------------|
| Technischer Nutzen | 30% | ... | ... | ... |
| Implementierungsaufwand | 25% | ... | ... | ... |
| Wartbarkeit | 20% | ... | ... | ... |
| Risiko (invertiert) | 15% | ... | ... | ... |
| Strategische Passung | 10% | ... | ... | ... |
| **Gesamt** | 100% | **X.X** | **X.X** | **X.X** |

---

## 6. Empfehlung

### 6.1 Empfohlenes Szenario

### 6.2 Nächste Schritte

| Schritt | Verantwortlich | Zieldatum | Ergebnis |
|---------|---------------|-----------|----------|
| ... | ... | ... | ADR-XXX / Prototyp / Verworfen |

### 6.3 ADR-Kandidaten

- [ ] ADR-XXX: ...

---

## 7. Offene Fragen

| Frage | Priorität | Wer klärt es? |
|-------|-----------|---------------|
| ... | HIGH/MEDIUM/LOW | ... |

---

## 8. Referenzen

- [Link / Dokument / ADR]

---

## Changelog

| Datum | Autor | Änderung |
|-------|-------|----------|
| YYYY-MM-DD | ... | Initial Draft |
