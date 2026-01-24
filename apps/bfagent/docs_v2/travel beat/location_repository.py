"""
Travel Story - Location Database
================================
Part 2: SQLite Schema und Repository
"""

import sqlite3
import json
from typing import List, Optional, Tuple
from pathlib import Path
from datetime import datetime

from location_models import (
    BaseLocation, LocationLayer, UserWorld, MergedLocationData,
    LayerType, District, LayerPlace, SensoryDetails,
    PersonalPlace, StoryCharacter, LocationMemory,
)


# ═══════════════════════════════════════════════════════════════
# DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════

SCHEMA = """
-- ═══════════════════════════════════════════════════════════════
-- SCHICHT 1: BASE_LOCATIONS (shared)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS base_locations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    region TEXT,
    coordinates TEXT,  -- JSON [lat, lon]
    timezone TEXT DEFAULT 'UTC',
    languages TEXT,    -- JSON array
    currency TEXT DEFAULT 'EUR',
    climate TEXT,
    best_seasons TEXT, -- JSON array
    districts TEXT,    -- JSON array of District objects
    population INTEGER,
    known_for TEXT,    -- JSON array
    generated_at TEXT,
    source TEXT DEFAULT 'web_research',
    quality_score REAL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_base_locations_country ON base_locations(country);

-- ═══════════════════════════════════════════════════════════════
-- SCHICHT 2: LOCATION_LAYERS (shared, genre-spezifisch)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS location_layers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    location_id TEXT NOT NULL,
    layer_type TEXT NOT NULL,
    atmospheres TEXT,       -- JSON dict
    places TEXT,            -- JSON array of LayerPlace objects
    sensory TEXT,           -- JSON SensoryDetails object
    story_hooks TEXT,       -- JSON array
    scene_settings TEXT,    -- JSON array
    potential_conflicts TEXT, -- JSON array
    generated_at TEXT,
    quality_score REAL DEFAULT 0.0,
    
    FOREIGN KEY (location_id) REFERENCES base_locations(id),
    UNIQUE(location_id, layer_type)
);

CREATE INDEX IF NOT EXISTS idx_layers_location ON location_layers(location_id);
CREATE INDEX IF NOT EXISTS idx_layers_type ON location_layers(layer_type);

-- ═══════════════════════════════════════════════════════════════
-- SCHICHT 3: USER_WORLDS (user-spezifisch)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS user_worlds (
    user_id TEXT PRIMARY KEY,
    interests_primary TEXT,    -- JSON array of LayerType values
    interests_secondary TEXT,  -- JSON array
    interests_avoid TEXT,      -- JSON array
    personal_places TEXT,      -- JSON array of PersonalPlace objects
    story_universe_name TEXT,
    characters TEXT,           -- JSON array of StoryCharacter objects
    location_memories TEXT,    -- JSON array of LocationMemory objects
    triggers_avoid TEXT,       -- JSON array
    preferred_spice_level TEXT DEFAULT 'mild',
    preferred_ending TEXT DEFAULT 'happy',
    stories_generated INTEGER DEFAULT 0,
    total_words_read INTEGER DEFAULT 0,
    favorite_locations TEXT,   -- JSON array
    created_at TEXT,
    updated_at TEXT
);

-- ═══════════════════════════════════════════════════════════════
-- CACHE TABLE (für Web-Research Ergebnisse)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS research_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_key TEXT UNIQUE NOT NULL,  -- z.B. "barcelona:base" oder "barcelona:romance"
    result TEXT NOT NULL,            -- JSON
    created_at TEXT,
    expires_at TEXT,                 -- Optional: Cache-Ablauf
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_cache_key ON research_cache(query_key);
"""


# ═══════════════════════════════════════════════════════════════
# REPOSITORY CLASS
# ═══════════════════════════════════════════════════════════════

class LocationRepository:
    """
    Repository für Location-Datenbank.
    Verwaltet alle 3 Schichten.
    """
    
    def __init__(self, db_path: str = "locations.db"):
        self.db_path = db_path
        self._conn = None
        self._init_db()
    
    def _init_db(self):
        """Initialisiere Datenbank mit Schema"""
        conn = self._get_conn()
        conn.executescript(SCHEMA)
        conn.commit()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection (reuse for in-memory)"""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn
    
    # ═══════════════════════════════════════════════════════════
    # SCHICHT 1: BASE_LOCATIONS
    # ═══════════════════════════════════════════════════════════
    
    def get_base_location(self, location_id: str) -> Optional[BaseLocation]:
        """Hole BaseLocation nach ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM base_locations WHERE id = ?",
                (location_id.lower(),)
            ).fetchone()
            
            if not row:
                return None
            
            return self._row_to_base_location(row)
    
    def save_base_location(self, location: BaseLocation) -> bool:
        """Speichere BaseLocation"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO base_locations (
                    id, name, country, region, coordinates, timezone,
                    languages, currency, climate, best_seasons, districts,
                    population, known_for, generated_at, source, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                location.id.lower(),
                location.name,
                location.country,
                location.region,
                json.dumps(location.coordinates) if location.coordinates else None,
                location.timezone,
                json.dumps(location.languages),
                location.currency,
                location.climate,
                json.dumps(location.best_seasons),
                json.dumps([d.to_dict() for d in location.districts]),
                location.population,
                json.dumps(location.known_for),
                location.generated_at,
                location.source,
                location.quality_score,
            ))
            return True
    
    def list_base_locations(self) -> List[Tuple[str, str, str]]:
        """Liste alle BaseLocations (id, name, country)"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT id, name, country FROM base_locations ORDER BY name"
            ).fetchall()
            return [(r["id"], r["name"], r["country"]) for r in rows]
    
    def _row_to_base_location(self, row: sqlite3.Row) -> BaseLocation:
        """Konvertiere DB-Row zu BaseLocation"""
        districts = []
        if row["districts"]:
            districts = [District.from_dict(d) for d in json.loads(row["districts"])]
        
        coords = None
        if row["coordinates"]:
            coords = tuple(json.loads(row["coordinates"]))
        
        return BaseLocation(
            id=row["id"],
            name=row["name"],
            country=row["country"],
            region=row["region"],
            coordinates=coords,
            timezone=row["timezone"] or "UTC",
            languages=json.loads(row["languages"]) if row["languages"] else [],
            currency=row["currency"] or "EUR",
            climate=row["climate"] or "",
            best_seasons=json.loads(row["best_seasons"]) if row["best_seasons"] else [],
            districts=districts,
            population=row["population"],
            known_for=json.loads(row["known_for"]) if row["known_for"] else [],
            generated_at=row["generated_at"] or "",
            source=row["source"] or "web_research",
            quality_score=row["quality_score"] or 0.0,
        )
    
    # ═══════════════════════════════════════════════════════════
    # SCHICHT 2: LOCATION_LAYERS
    # ═══════════════════════════════════════════════════════════
    
    def get_location_layer(
        self, 
        location_id: str, 
        layer_type: LayerType
    ) -> Optional[LocationLayer]:
        """Hole Layer für Location und Typ"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM location_layers WHERE location_id = ? AND layer_type = ?",
                (location_id.lower(), layer_type.value)
            ).fetchone()
            
            if not row:
                return None
            
            return self._row_to_location_layer(row)
    
    def save_location_layer(self, layer: LocationLayer) -> bool:
        """Speichere LocationLayer"""
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO location_layers (
                    location_id, layer_type, atmospheres, places, sensory,
                    story_hooks, scene_settings, potential_conflicts,
                    generated_at, quality_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                layer.location_id.lower(),
                layer.layer_type.value,
                json.dumps(layer.atmospheres),
                json.dumps([p.to_dict() for p in layer.places]),
                json.dumps(layer.sensory.to_dict()),
                json.dumps(layer.story_hooks),
                json.dumps(layer.scene_settings),
                json.dumps(layer.potential_conflicts),
                layer.generated_at,
                layer.quality_score,
            ))
            return True
    
    def get_layers_for_location(self, location_id: str) -> List[LayerType]:
        """Liste alle verfügbaren Layer-Typen für eine Location"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT layer_type FROM location_layers WHERE location_id = ?",
                (location_id.lower(),)
            ).fetchall()
            return [LayerType(r["layer_type"]) for r in rows]
    
    def _row_to_location_layer(self, row: sqlite3.Row) -> LocationLayer:
        """Konvertiere DB-Row zu LocationLayer"""
        places = []
        if row["places"]:
            places = [LayerPlace.from_dict(p) for p in json.loads(row["places"])]
        
        sensory = SensoryDetails()
        if row["sensory"]:
            sensory = SensoryDetails.from_dict(json.loads(row["sensory"]))
        
        return LocationLayer(
            location_id=row["location_id"],
            layer_type=LayerType(row["layer_type"]),
            atmospheres=json.loads(row["atmospheres"]) if row["atmospheres"] else {},
            places=places,
            sensory=sensory,
            story_hooks=json.loads(row["story_hooks"]) if row["story_hooks"] else [],
            scene_settings=json.loads(row["scene_settings"]) if row["scene_settings"] else [],
            potential_conflicts=json.loads(row["potential_conflicts"]) if row["potential_conflicts"] else [],
            generated_at=row["generated_at"] or "",
            quality_score=row["quality_score"] or 0.0,
        )
    
    # ═══════════════════════════════════════════════════════════
    # SCHICHT 3: USER_WORLDS
    # ═══════════════════════════════════════════════════════════
    
    def get_user_world(self, user_id: str) -> Optional[UserWorld]:
        """Hole UserWorld nach ID"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM user_worlds WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if not row:
                return None
            
            return self._row_to_user_world(row)
    
    def save_user_world(self, world: UserWorld) -> bool:
        """Speichere UserWorld"""
        world.updated_at = datetime.now().isoformat()
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO user_worlds (
                    user_id, interests_primary, interests_secondary, interests_avoid,
                    personal_places, story_universe_name, characters, location_memories,
                    triggers_avoid, preferred_spice_level, preferred_ending,
                    stories_generated, total_words_read, favorite_locations,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                world.user_id,
                json.dumps([i.value for i in world.interests_primary]),
                json.dumps([i.value for i in world.interests_secondary]),
                json.dumps([i.value for i in world.interests_avoid]),
                json.dumps([p.to_dict() for p in world.personal_places]),
                world.story_universe_name,
                json.dumps([c.to_dict() for c in world.characters]),
                json.dumps([m.to_dict() for m in world.location_memories]),
                json.dumps(world.triggers_avoid),
                world.preferred_spice_level,
                world.preferred_ending,
                world.stories_generated,
                world.total_words_read,
                json.dumps(world.favorite_locations),
                world.created_at,
                world.updated_at,
            ))
            return True
    
    def get_or_create_user_world(self, user_id: str) -> UserWorld:
        """Hole UserWorld oder erstelle neue"""
        world = self.get_user_world(user_id)
        if not world:
            world = UserWorld(user_id=user_id)
            self.save_user_world(world)
        return world
    
    def _row_to_user_world(self, row: sqlite3.Row) -> UserWorld:
        """Konvertiere DB-Row zu UserWorld"""
        return UserWorld(
            user_id=row["user_id"],
            interests_primary=[LayerType(i) for i in json.loads(row["interests_primary"] or "[]")],
            interests_secondary=[LayerType(i) for i in json.loads(row["interests_secondary"] or "[]")],
            interests_avoid=[LayerType(i) for i in json.loads(row["interests_avoid"] or "[]")],
            personal_places=[PersonalPlace.from_dict(p) for p in json.loads(row["personal_places"] or "[]")],
            story_universe_name=row["story_universe_name"],
            characters=[StoryCharacter.from_dict(c) for c in json.loads(row["characters"] or "[]")],
            location_memories=[LocationMemory.from_dict(m) for m in json.loads(row["location_memories"] or "[]")],
            triggers_avoid=json.loads(row["triggers_avoid"] or "[]"),
            preferred_spice_level=row["preferred_spice_level"] or "mild",
            preferred_ending=row["preferred_ending"] or "happy",
            stories_generated=row["stories_generated"] or 0,
            total_words_read=row["total_words_read"] or 0,
            favorite_locations=json.loads(row["favorite_locations"] or "[]"),
            created_at=row["created_at"] or "",
            updated_at=row["updated_at"] or "",
        )
    
    # ═══════════════════════════════════════════════════════════
    # CACHE
    # ═══════════════════════════════════════════════════════════
    
    def get_cached(self, query_key: str) -> Optional[dict]:
        """Hole gecachtes Ergebnis"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT result, expires_at FROM research_cache WHERE query_key = ?",
                (query_key,)
            ).fetchone()
            
            if not row:
                return None
            
            # Check expiry
            if row["expires_at"]:
                if datetime.fromisoformat(row["expires_at"]) < datetime.now():
                    return None  # Expired
            
            # Update hit count
            conn.execute(
                "UPDATE research_cache SET hit_count = hit_count + 1 WHERE query_key = ?",
                (query_key,)
            )
            
            return json.loads(row["result"])
    
    def save_cache(self, query_key: str, result: dict, ttl_days: int = 30):
        """Speichere in Cache"""
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(days=ttl_days)).isoformat()
        
        with self._get_conn() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO research_cache (query_key, result, created_at, expires_at, hit_count)
                VALUES (?, ?, ?, ?, 0)
            """, (
                query_key,
                json.dumps(result),
                datetime.now().isoformat(),
                expires_at,
            ))
    
    # ═══════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════
    
    def get_stats(self) -> dict:
        """Hole Datenbank-Statistiken"""
        with self._get_conn() as conn:
            base_count = conn.execute("SELECT COUNT(*) FROM base_locations").fetchone()[0]
            layer_count = conn.execute("SELECT COUNT(*) FROM location_layers").fetchone()[0]
            user_count = conn.execute("SELECT COUNT(*) FROM user_worlds").fetchone()[0]
            cache_count = conn.execute("SELECT COUNT(*) FROM research_cache").fetchone()[0]
            cache_hits = conn.execute("SELECT SUM(hit_count) FROM research_cache").fetchone()[0] or 0
            
            return {
                "base_locations": base_count,
                "location_layers": layer_count,
                "user_worlds": user_count,
                "cache_entries": cache_count,
                "cache_hits": cache_hits,
            }
