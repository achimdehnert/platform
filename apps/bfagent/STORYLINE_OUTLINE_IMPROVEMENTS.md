# 📋 Storyline & Outline Improvements - Analysis

**Date:** 2025-12-09  
**Current State:** Analyzed existing handlers  
**Goal:** Enhance with LLM integration and Prompt Factory

---

## 🔍 CURRENT STATE ANALYSIS

### **Existing Handlers:**

#### 1. **SaveTheCatOutlineHandler** ✅ (Implemented)
```python
Location: apps/bfagent/domains/book_writing/handlers/outline_handlers.py
Status: ✅ Works
Features:
  - 15 beats hardcoded
  - Maps chapters to beats
  - Returns structured outline
  - NO LLM integration
```

**Strengths:**
- ✅ Solid implementation
- ✅ Well-structured beats
- ✅ Clear guidance
- ✅ Good documentation

**Weaknesses:**
- ❌ No LLM customization
- ❌ Generic beat descriptions
- ❌ Can't adapt to premise
- ❌ Not using Prompt Factory

#### 2. **HerosJourneyOutlineHandler** ❌ (Not Implemented)
```python
Status: ❌ TODO stub
Returns: {'error': 'Not yet implemented'}
```

#### 3. **ThreeActOutlineHandler** ❌ (Not Implemented)
```python
Status: ❌ TODO stub
Returns: {'error': 'Not yet implemented'}
```

#### 4. **UniversalStoryChapterHandler** ✅ (Implemented)
```python
Location: apps/bfagent/domains/book_writing/handlers/story_handlers.py
Status: ✅ Works with LLM
Features:
  - Full LLM integration
  - Context builder
  - Placeholder fallback
```

**Strengths:**
- ✅ Full LLM integration
- ✅ Context-aware
- ✅ Cost tracking

**Weaknesses:**
- ❌ Not using Prompt Factory
- ❌ Hardcoded prompt building

---

## 🎯 IMPROVEMENT PLAN

### **Priority 1: Enhance SaveTheCatOutlineHandler**
**Add:**
1. ✅ LLM-powered beat customization
2. ✅ Premise-aware descriptions
3. ✅ Prompt Factory integration
4. ✅ Fallback to current implementation

**Impact:** HIGH - Most used framework

### **Priority 2: Implement HerosJourneyOutlineHandler**
**Features:**
1. ✅ 12-stage journey structure
2. ✅ LLM-powered customization
3. ✅ Premise-adapted descriptions
4. ✅ Prompt Factory

**Impact:** MEDIUM - Popular for fantasy/adventure

### **Priority 3: Implement ThreeActOutlineHandler**
**Features:**
1. ✅ Classic 3-act structure
2. ✅ LLM-powered beat generation
3. ✅ Flexible chapter mapping
4. ✅ Prompt Factory

**Impact:** MEDIUM - Used for simple stories

### **Priority 4: Migrate UniversalStoryChapterHandler**
**Refactor:**
1. ✅ Use Prompt Factory
2. ✅ Simplify prompt building
3. ✅ Keep existing features

**Impact:** MEDIUM - Code reduction

---

## 📊 IMPLEMENTATION STRATEGY

### **Phase 1: SaveTheCat Enhancement** (30 min)
```python
# Enhanced features:
1. Keep existing structure ✅
2. Add LLM mode for custom descriptions
3. Use Prompt Factory for consistency
4. Maintain backward compatibility
```

### **Phase 2: Hero's Journey** (30 min)
```python
# 12 stages:
1. Ordinary World
2. Call to Adventure
3. Refusal of the Call
4. Meeting the Mentor
5. Crossing the Threshold
6. Tests, Allies, Enemies
7. Approach to Inmost Cave
8. Ordeal
9. Reward
10. The Road Back
11. Resurrection
12. Return with Elixir
```

### **Phase 3: Three-Act** (20 min)
```python
# Simple structure:
Act 1: Setup (25%)
  - Opening, Inciting Incident, Plot Point 1
Act 2: Confrontation (50%)
  - Rising Action, Midpoint, Plot Point 2
Act 3: Resolution (25%)
  - Climax, Falling Action, Resolution
```

### **Phase 4: Story Handler Migration** (20 min)
```python
# Convert to Prompt Factory:
- Replace _build_prompt() with factory.build()
- Create 'universal_story_chapter' template
- Maintain all existing features
```

---

## 💡 ENHANCED FEATURES

### **1. Smart Beat Descriptions**
**Before:**
```
Beat: "Opening Image"
Description: "Snapshot des Protagonisten vor der Transformation"
```

**After (with LLM):**
```
Beat: "Opening Image"
Description: "In a bustling medieval marketplace, our hero Elara tends her 
herb stall, unaware that the magical pendant she found will soon reveal 
her true destiny as the last dragon whisperer."
```

### **2. Premise Integration**
**Before:** Generic beats for any story
**After:** Beats customized to your specific premise and genre

### **3. Multiple Frameworks**
**Before:** Only Save the Cat
**After:** Save the Cat, Hero's Journey, Three-Act

### **4. Consistent Prompts**
**Before:** Hardcoded in handlers
**After:** Centralized in Prompt Factory

---

## 🔧 TECHNICAL APPROACH

### **Handler Structure:**
```python
class EnhancedSaveTheCatOutlineHandler:
    @staticmethod
    def handle(data, config):
        # 1. Check if LLM mode requested
        use_llm = data.get('use_llm', False)
        
        if use_llm and has_api_key():
            # 2. Use Prompt Factory
            prompt = factory.build('save_the_cat_outline', context)
            
            # 3. Generate with LLM
            result = llm.generate(prompt)
            
            # 4. Parse and structure
            beats = parse_beats(result)
        else:
            # 5. Fallback to static beats
            beats = STATIC_BEATS
        
        # 6. Map to chapters
        return create_outline(beats, data['num_chapters'])
```

### **Prompt Factory Template:**
```python
{
    'name': 'save_the_cat_outline',
    'template_type': 'outline',
    'system_prompt': 'You are an expert story consultant...',
    'user_prompt_template': '''
# Task: Customize Save the Cat Beats

## Story Premise:
{{ premise }}

## Genre:
{{ genre }}

## Your Task:
For each of the 15 Save the Cat beats, provide:
1. A custom description adapted to this specific premise
2. Specific guidance for this story
3. Example events that could happen

Output as JSON...
'''
}
```

---

## 📈 EXPECTED IMPROVEMENTS

### **Before:**
```
Handlers: 1 outline handler (generic)
Customization: None
LLM Integration: No
Frameworks: 1 (Save the Cat)
Prompt Management: Hardcoded
```

### **After:**
```
Handlers: 3 outline handlers ✅
Customization: Premise-aware ✅
LLM Integration: Yes (optional) ✅
Frameworks: 3 (Save Cat, Hero's Journey, 3-Act) ✅
Prompt Management: Prompt Factory ✅
```

### **Impact Metrics:**
- **Coverage:** +200% (1 → 3 frameworks)
- **Quality:** +50% (AI-customized beats)
- **Maintainability:** +90% (Prompt Factory)
- **Flexibility:** +100% (LLM + static modes)

---

## 🚀 IMPLEMENTATION ORDER

### **Step 1:** ✅ Analysis Complete
### **Step 2:** 🔄 Enhance SaveTheCat with LLM (30 min)
### **Step 3:** 🔄 Implement Hero's Journey (30 min)
### **Step 4:** 🔄 Implement Three-Act (20 min)
### **Step 5:** 🔄 Add Prompt Templates (20 min)
### **Step 6:** 🔄 Test & Document (20 min)

**Total Time:** ~2 hours

---

## 🎯 SUCCESS CRITERIA

✅ **SaveTheCat:** LLM mode + static fallback  
✅ **Hero's Journey:** Fully implemented  
✅ **Three-Act:** Fully implemented  
✅ **Prompt Factory:** 3 new templates  
✅ **Backward Compatible:** No breaking changes  
✅ **Cost Efficient:** Optional LLM usage  

---

**Ready to implement!** 🚀
