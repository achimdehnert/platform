# 🔒 Illustration System - Permissions & Access Control

## ✅ IMPLEMENTIERT: Role-Based Access Control

Das Illustration System verwendet jetzt ein **konsequentes Permission-System** mit User- und Rollenrechten.

---

## 🎯 **PERMISSION MIXINS**

### **1. IllustrationOwnerMixin**
**Zweck:** Stellt sicher, dass User nur eigene Ressourcen zugreifen können

**Prüfungen:**
- ✅ User ist eingeloggt
- ✅ User besitzt die Ressource (`user` field)
- ✅ **ODER** User ist Staff/Superuser (Admin Override)

**Verwendung:**
```python
class GeneratedImageDetailView(LoginRequiredMixin, IllustrationOwnerMixin, DetailView):
    model = GeneratedImage
```

**Verhalten:**
- User A kann **nur** eigene Images sehen
- User B kann **NICHT** Images von User A sehen
- Staff/Admin können **ALLE** Images sehen

---

### **2. IllustrationListOwnerFilterMixin**
**Zweck:** Automatisches Filtern von List Views auf User's Daten

**Prüfungen:**
- ✅ Regular User: Nur eigene Daten
- ✅ Staff/Superuser: Alle Daten

**Verwendung:**
```python
class GeneratedImageListView(LoginRequiredMixin, IllustrationListOwnerFilterMixin, ListView):
    model = GeneratedImage
```

**Verhalten:**
- List zeigt **automatisch nur User's eigene Images**
- Keine manuelle Filterung nötig
- Staff sieht alle Images

---

### **3. IllustrationProjectAccessMixin**
**Zweck:** Zugriff basierend auf Project-Ownership

**Prüfungen:**
- ✅ User besitzt das Project
- ✅ **ODER** User ist Team Member (wenn Team-System existiert)
- ✅ **ODER** User ist Staff/Superuser

**Verwendung:**
```python
# Für zukünftige Features wie "Generate for Project"
class ProjectImageGenerateView(IllustrationProjectAccessMixin, FormView):
    # Requires project_id in URL or form
```

---

## 🛡️ **ANGEWENDET AUF VIEWS:**

### **Style Profiles:**
```python
# Liste - Automatisches Filtern
class StyleProfileListView(LoginRequiredMixin, IllustrationListOwnerFilterMixin, ListView)

# Detail - Owner Check
class StyleProfileDetailView(LoginRequiredMixin, IllustrationOwnerMixin, DetailView)

# Create - User wird automatisch gesetzt
class StyleProfileCreateView(LoginRequiredMixin, CreateView):
    def form_valid(self, form):
        form.instance.user = self.request.user  # ✅ Owner automatisch
```

### **Generated Images:**
```python
# Gallery - Automatisches Filtern
class GeneratedImageListView(LoginRequiredMixin, IllustrationListOwnerFilterMixin, ListView)

# Detail - Owner Check
class GeneratedImageDetailView(LoginRequiredMixin, IllustrationOwnerMixin, DetailView)
```

### **Image Generation:**
```python
# Generation - User wird bei Create gesetzt
class GenerateImageView(LoginRequiredMixin, FormView):
    def form_valid(self, form):
        GeneratedImage.objects.create(
            user=self.request.user,  # ✅ Owner automatisch
            ...
        )
```

---

## 🚨 **SICHERHEITS-FEATURES:**

### **1. URL Manipulation Protection**
```
Vorher (❌ UNSICHER):
User A: /images/123/  → Bild von User A ✅
User A: /images/456/  → Bild von User B ✅ (PROBLEM!)

Nachher (✅ SICHER):
User A: /images/123/  → Bild von User A ✅
User A: /images/456/  → 403 Forbidden ❌
```

### **2. List Filtering**
```
Vorher (❌ UNSICHER):
Gallery zeigt alle Bilder (mit manueller Filterung)

Nachher (✅ SICHER):
Gallery zeigt automatisch nur User's eigene Bilder
```

### **3. Automatic Owner Assignment**
```python
# ✅ Bei Create wird User automatisch gesetzt
generated_image = GeneratedImage.objects.create(
    user=self.request.user,  # Automatisch
    ...
)
```

---

## 👥 **ROLLEN-HIERARCHIE:**

### **Regular User:**
- ✅ Kann **NUR** eigene Images/Styles sehen/bearbeiten/löschen
- ❌ Kann **NICHT** Images/Styles anderer User sehen
- ✅ List Views zeigen automatisch nur eigene Daten

### **Staff User:**
- ✅ Kann **ALLE** Images/Styles sehen
- ✅ Kann **ALLE** Images/Styles bearbeiten/löschen
- ✅ Admin Override für Support/Debugging

### **Superuser:**
- ✅ Vollzugriff auf alles
- ✅ Gleiche Rechte wie Staff + mehr Django-Admin Rechte

---

## 🧪 **TESTING:**

### **Test 1: Owner kann eigene Ressourcen sehen**
```python
# User A erstellt Image
image = GeneratedImage.objects.create(user=user_a, ...)

# User A kann auf /images/<id>/ zugreifen
response = client.get(f'/images/{image.id}/')
assert response.status_code == 200  # ✅
```

### **Test 2: User kann fremde Ressourcen NICHT sehen**
```python
# User A erstellt Image
image = GeneratedImage.objects.create(user=user_a, ...)

# User B versucht zuzugreifen
client.force_login(user_b)
response = client.get(f'/images/{image.id}/')
assert response.status_code == 403  # ✅ Forbidden
```

### **Test 3: Staff kann alles sehen**
```python
# User A erstellt Image
image = GeneratedImage.objects.create(user=user_a, ...)

# Staff User greift zu
client.force_login(staff_user)
response = client.get(f'/images/{image.id}/')
assert response.status_code == 200  # ✅
```

---

## 📝 **IMPLEMENTATION FILES:**

```
apps/bfagent/mixins/
└── illustration_permissions.py          # Permission Mixins

apps/bfagent/views/
├── illustration_views.py                # Views mit Mixins
└── illustration_generation_views.py     # Generation View

apps/bfagent/models_illustration.py      # Models mit user field
```

---

## 🎯 **VORTEILE:**

1. **✅ Sicherheit:** User können nur eigene Daten sehen
2. **✅ Konsistenz:** Gleiche Logik in allen Views
3. **✅ Wartbarkeit:** Zentrale Permission-Logik in Mixins
4. **✅ Flexibilität:** Einfach erweiterbar (z.B. Team-Member Rechte)
5. **✅ Admin-Friendly:** Staff kann alles sehen für Support
6. **✅ Testbar:** Klare Test-Szenarien

---

## 🔜 **ZUKÜNFTIGE ERWEITERUNGEN:**

### **Team Member Support:**
```python
def test_func(self):
    # Current: Owner oder Staff
    if obj.user == self.request.user:
        return True
    
    # Future: ODER Team Member
    if hasattr(obj.project, 'team_members'):
        if self.request.user in obj.project.team_members.all():
            return True
    
    return False
```

### **Fine-Grained Permissions:**
```python
# z.B. Custom Permissions für Image Actions
class ImageApprovalPermission:
    def has_permission(self, user, image):
        return user.has_perm('bfagent.approve_image')
```

---

## ✅ **STATUS: PRODUCTION READY**

Alle Illustration Views sind jetzt mit **role-based access control** ausgestattet!

**Tested:** ✅  
**Secure:** ✅  
**Consistent:** ✅  
**Ready for Production:** ✅
