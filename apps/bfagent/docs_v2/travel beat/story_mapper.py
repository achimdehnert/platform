"""
Travel Story - Story Mapper
===========================
Part 2: Mapping Logic
"""

from typing import List, Dict, Tuple
from datetime import date

from models import ReadingSchedule, ReadingSlot, DaySchedule, ReadingContext
from story_models import (
    StoryAct, StoryBeat, PacingType, LocationSyncType,
    ChapterOutline, StoryOutline, StoryPreferences,
    ACT_DISTRIBUTION, BEATS_BY_ACT, BEAT_DESCRIPTIONS, BEAT_PACING,
)


# ═══════════════════════════════════════════════════════════════
# PACING MAPPING
# ═══════════════════════════════════════════════════════════════

def get_context_pacing(context: ReadingContext) -> PacingType:
    """Map reading context to optimal pacing"""
    mapping = {
        ReadingContext.TRANSPORT: PacingType.ACTION,
        ReadingContext.MORNING: PacingType.REFLECTIVE,
        ReadingContext.POOL: PacingType.ATMOSPHERIC,
        ReadingContext.EVENING: PacingType.EMOTIONAL,
        ReadingContext.CAFE: PacingType.ATMOSPHERIC,
        ReadingContext.WAITING: PacingType.ACTION,
    }
    return mapping.get(context, PacingType.ATMOSPHERIC)


def blend_pacing(beat_pacing: PacingType, context_pacing: PacingType) -> PacingType:
    """Blend beat's ideal pacing with context's ideal pacing"""
    # Priority: Beat pacing wins for key moments
    key_beats_pacing = [PacingType.ACTION]  # Action beats stay action
    
    if beat_pacing in key_beats_pacing:
        return beat_pacing
    
    # For emotional/reflective beats, context can influence
    if context_pacing == PacingType.ACTION and beat_pacing == PacingType.EMOTIONAL:
        return PacingType.EMOTIONAL  # Keep emotional for important beats
    
    return beat_pacing


# ═══════════════════════════════════════════════════════════════
# LOCATION SYNC
# ═══════════════════════════════════════════════════════════════

def determine_story_location(
    reader_location: str,
    sync_mode: LocationSyncType,
    trip_origin: str,
    act: StoryAct,
    is_travel_day: bool
) -> Tuple[str, LocationSyncType]:
    """
    Determine story location based on reader location and sync mode.
    Returns (story_location, actual_sync_type)
    """
    if sync_mode == LocationSyncType.EXACT:
        if is_travel_day:
            return "In Transit / Unterwegs", LocationSyncType.METAPHORICAL
        return reader_location, LocationSyncType.EXACT
    
    elif sync_mode == LocationSyncType.INSPIRED:
        # Use similar atmosphere but maybe different city
        return f"Inspiriert von {reader_location}", LocationSyncType.INSPIRED
    
    else:
        return "Fiktiver Ort", LocationSyncType.INDEPENDENT


def get_emotional_tone(act: StoryAct, beat: StoryBeat, is_arrival: bool = False) -> str:
    """Determine emotional tone for a chapter"""
    tones = {
        StoryAct.ACT_1: "Neugier, Aufbruch, Entdeckung",
        StoryAct.ACT_2A: "Vertiefung, Annäherung, Komplikation",
        StoryAct.ACT_2B: "Spannung, Krise, Verzweiflung",
        StoryAct.ACT_3: "Entschlossenheit, Konfrontation, Auflösung",
    }
    
    base_tone = tones.get(act, "")
    
    # Specific beat overrides
    if beat == StoryBeat.HOOK:
        return "Fesselnd, mysteriös, einladend"
    elif beat == StoryBeat.MIDPOINT:
        return "Schock, Neuorientierung, Wendepunkt"
    elif beat == StoryBeat.DARK_NIGHT:
        return "Verzweiflung, Tiefpunkt, innere Konfrontation"
    elif beat == StoryBeat.CLIMAX:
        return "Intensität, Entscheidung, alles oder nichts"
    elif beat == StoryBeat.FINAL_IMAGE:
        return "Erfüllung, Transformation, Hoffnung"
    
    if is_arrival:
        return f"{base_tone}, Ankunft-Aufregung"
    
    return base_tone


# ═══════════════════════════════════════════════════════════════
# MAIN MAPPER CLASS
# ═══════════════════════════════════════════════════════════════

class StoryMapper:
    """
    Maps story beats to reading schedule slots.
    """
    
    def __init__(
        self,
        reading_schedule: ReadingSchedule,
        story_preferences: StoryPreferences,
        trip_origin: str = "Unknown"
    ):
        self.schedule = reading_schedule
        self.preferences = story_preferences
        self.trip_origin = trip_origin
        
        # Calculate totals
        self.total_words = reading_schedule.recommended_word_count
        self.total_reading_minutes = reading_schedule.total_reading_minutes
        
        # Determine sync mode
        self.sync_mode = LocationSyncType(story_preferences.location_sync)
    
    def generate_outline(self) -> StoryOutline:
        """
        Generate complete story outline mapped to travel schedule.
        """
        # 1. Calculate act boundaries (word counts)
        act_words = self._calculate_act_words()
        
        # 2. Flatten all reading slots with metadata
        all_slots = self._flatten_slots()
        
        # 3. Assign acts and beats to slots
        chapters = self._assign_chapters(all_slots, act_words)
        
        # 4. Build story outline
        outline = StoryOutline(
            title=f"Travel Story: {self.schedule.trip_name}",
            total_words=self.total_words,
            total_chapters=len(chapters),
            chapters=chapters,
            genre=self.preferences.genre,
            location_sync_mode=self.sync_mode,
        )
        
        return outline
    
    def _calculate_act_words(self) -> Dict[StoryAct, int]:
        """Calculate word count for each act"""
        return {
            act: int(self.total_words * percentage)
            for act, percentage in ACT_DISTRIBUTION.items()
        }
    
    def _flatten_slots(self) -> List[Dict]:
        """Flatten all reading slots into a list with metadata"""
        slots = []
        
        for day in self.schedule.daily_schedules:
            is_first_day = day.day_number == 1
            is_last_day = day.day_number == self.schedule.total_days
            
            # Check if this is a travel day (has transport slot)
            is_travel_day = any(
                slot.context == ReadingContext.TRANSPORT 
                for slot in day.reading_slots
            )
            
            for slot in day.reading_slots:
                slots.append({
                    "slot": slot,
                    "date": day.date,
                    "day_number": day.day_number,
                    "location": day.location,
                    "is_first_day": is_first_day,
                    "is_last_day": is_last_day,
                    "is_travel_day": is_travel_day,
                    "word_budget": slot.word_budget,
                })
        
        return slots
    
    def _assign_chapters(
        self, 
        slots: List[Dict], 
        act_words: Dict[StoryAct, int]
    ) -> List[ChapterOutline]:
        """
        Assign chapters to reading slots based on word budgets.
        """
        chapters = []
        chapter_number = 1
        
        # Track progress through story
        current_act_index = 0
        acts = list(StoryAct)
        current_act = acts[current_act_index]
        
        current_beat_index = 0
        current_act_beats = BEATS_BY_ACT[current_act]
        
        words_in_current_act = 0
        act_target = act_words[current_act]
        
        for slot_data in slots:
            slot = slot_data["slot"]
            
            # Check if we need to move to next act
            if words_in_current_act >= act_target and current_act_index < len(acts) - 1:
                current_act_index += 1
                current_act = acts[current_act_index]
                current_act_beats = BEATS_BY_ACT[current_act]
                current_beat_index = 0
                words_in_current_act = 0
                act_target = act_words[current_act]
            
            # Get current beat
            if current_beat_index < len(current_act_beats):
                current_beat, beat_weight = current_act_beats[current_beat_index]
            else:
                # Stay on last beat of act
                current_beat, beat_weight = current_act_beats[-1]
            
            # Determine word target for this chapter
            word_target = min(slot.word_budget, 4000)  # Cap at 4000 words per chapter
            word_target = max(word_target, 2000)  # Minimum 2000 words
            
            # Determine story location
            story_location, actual_sync = determine_story_location(
                reader_location=slot_data["location"],
                sync_mode=self.sync_mode,
                trip_origin=self.trip_origin,
                act=current_act,
                is_travel_day=slot_data["is_travel_day"],
            )
            
            # Special handling for first and last chapters
            if slot_data["is_first_day"] and slot.context == ReadingContext.TRANSPORT:
                story_location = f"{self.trip_origin} → {slot_data['location']}"
                current_beat = StoryBeat.HOOK
            
            if slot_data["is_last_day"] and slot.context == ReadingContext.TRANSPORT:
                story_location = f"{slot_data['location']} → {self.trip_origin}"
                current_beat = StoryBeat.FINAL_IMAGE
            
            # Determine pacing
            beat_pacing = BEAT_PACING.get(current_beat, PacingType.ATMOSPHERIC)
            context_pacing = get_context_pacing(slot.context)
            final_pacing = blend_pacing(beat_pacing, context_pacing)
            
            # Create chapter
            chapter = ChapterOutline(
                chapter_number=chapter_number,
                title=None,  # Can be generated later
                word_target=word_target,
                act=current_act,
                beats=[current_beat],
                story_location=story_location,
                reader_location=slot_data["location"],
                location_sync=actual_sync,
                pacing=final_pacing,
                emotional_tone=get_emotional_tone(
                    current_act, 
                    current_beat,
                    is_arrival=slot_data["is_travel_day"]
                ),
                reading_date=slot_data["date"],
                reading_context=slot.context.value,
                beat_description=BEAT_DESCRIPTIONS.get(current_beat, ""),
                chapter_end_hook=self._generate_hook_hint(current_beat, current_act),
                special_instructions=self._get_special_instructions(
                    slot_data, current_beat, current_act
                ),
            )
            
            chapters.append(chapter)
            
            # Update tracking
            chapter_number += 1
            words_in_current_act += word_target
            
            # Check if we should move to next beat
            beat_target = act_target * beat_weight
            if words_in_current_act >= beat_target * (current_beat_index + 1):
                current_beat_index = min(current_beat_index + 1, len(current_act_beats) - 1)
        
        return chapters
    
    def _generate_hook_hint(self, beat: StoryBeat, act: StoryAct) -> str:
        """Generate chapter-end hook suggestion"""
        hooks = {
            StoryBeat.HOOK: "Ende mit einer Frage oder einem Geheimnis",
            StoryBeat.SETUP: "Hinweis auf kommende Veränderung",
            StoryBeat.INCITING_INCIDENT: "Cliffhanger: Die Entscheidung steht bevor",
            StoryBeat.FIRST_PLOT_POINT: "Protagonist betritt unbekanntes Terrain",
            StoryBeat.MIDPOINT: "Schock-Enthüllung, die alles verändert",
            StoryBeat.DARK_NIGHT: "Hoffnungsschimmer am dunkelsten Punkt",
            StoryBeat.CLIMAX: "Der finale Moment beginnt",
            StoryBeat.FINAL_IMAGE: "Echo des Anfangs, aber transformiert",
        }
        return hooks.get(beat, "Spannung halten, Neugier wecken")
    
    def _get_special_instructions(
        self, 
        slot_data: Dict, 
        beat: StoryBeat,
        act: StoryAct
    ) -> List[str]:
        """Generate special instructions for chapter"""
        instructions = []
        
        # Location sync instructions
        if self.sync_mode == LocationSyncType.EXACT:
            instructions.append(
                f"LOCATION-SYNC: Leser ist in {slot_data['location']} - "
                f"nutze echte Orte und Details"
            )
        
        # Context-specific
        if slot_data["slot"].context == ReadingContext.TRANSPORT:
            instructions.append(
                "TRANSPORT-LESEN: Pacing hoch halten, Cliffhanger einbauen"
            )
        elif slot_data["slot"].context == ReadingContext.EVENING:
            instructions.append(
                "ABEND-LESEN: Emotionale Tiefe, Reflexion, intime Momente"
            )
        elif slot_data["slot"].context == ReadingContext.POOL:
            instructions.append(
                "POOL-LESEN: Atmosphärisch, sinnlich, entspanntes Tempo"
            )
        
        # First/last day
        if slot_data["is_first_day"]:
            instructions.append("REISE-START: Aufbruchstimmung spiegeln")
        if slot_data["is_last_day"]:
            instructions.append("REISE-ENDE: Abschluss, Rückkehr, Transformation")
        
        # Genre-specific
        if self.preferences.genre == "romance":
            if act == StoryAct.ACT_2A:
                instructions.append("ROMANCE: Annäherung und Spannung aufbauen")
            elif act == StoryAct.ACT_2B:
                instructions.append("ROMANCE: Konflikt in Beziehung, Black Moment")
        
        if self.preferences.genre == "thriller":
            if act == StoryAct.ACT_2B:
                instructions.append("THRILLER: Gefahr eskaliert, Protagonist in Bedrängnis")
        
        # Spice level
        if self.preferences.spice_level in ["moderate", "spicy"]:
            if act in [StoryAct.ACT_2A, StoryAct.ACT_2B]:
                instructions.append(f"SPICE: {self.preferences.spice_level} - intime Szenen möglich")
        
        return instructions


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════

def map_story_to_travel(
    reading_schedule: ReadingSchedule,
    story_preferences: StoryPreferences,
    trip_origin: str = "Unknown"
) -> StoryOutline:
    """
    Convenience function to map story to travel schedule.
    """
    mapper = StoryMapper(reading_schedule, story_preferences, trip_origin)
    return mapper.generate_outline()
