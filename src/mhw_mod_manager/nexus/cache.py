"""SQLite cache for Nexus Mods metadata."""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from ..core.config import get_data_dir
from ..core.models import NexusMod, NexusModFile

logger = logging.getLogger(__name__)


class NexusCache:
    """SQLite-based cache for Nexus Mods data."""

    def __init__(self, cache_db_path: Optional[Path] = None) -> None:
        """Initialize the cache.

        Args:
            cache_db_path: Path to cache database. If None, uses default location.
        """
        if cache_db_path is None:
            cache_db_path = get_data_dir() / "nexus_cache.db"

        self.cache_db_path = cache_db_path
        self._ensure_database()

    def _ensure_database(self) -> None:
        """Ensure database exists with proper schema."""
        self.cache_db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()

            # Create mods table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mods (
                    mod_id INTEGER PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at TIMESTAMP NOT NULL
                )
            """
            )

            # Create mod_files table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mod_files (
                    mod_id INTEGER NOT NULL,
                    file_id INTEGER NOT NULL,
                    data TEXT NOT NULL,
                    cached_at TIMESTAMP NOT NULL,
                    PRIMARY KEY (mod_id, file_id)
                )
            """
            )

            # Create mod_lists table for trending/latest/updated
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS mod_lists (
                    list_type TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    cached_at TIMESTAMP NOT NULL
                )
            """
            )

            # Create indexes
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mods_cached_at
                ON mods(cached_at)
            """
            )
            cursor.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_mod_files_cached_at
                ON mod_files(cached_at)
            """
            )

            conn.commit()
        finally:
            conn.close()

    def cache_mod(self, mod: NexusMod) -> None:
        """Cache a mod's metadata.

        Args:
            mod: Mod to cache.
        """
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO mods (mod_id, data, cached_at)
                VALUES (?, ?, ?)
            """,
                (mod.mod_id, mod.model_dump_json(), datetime.now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_mod(self, mod_id: int, max_age_hours: int = 1) -> Optional[NexusMod]:
        """Get a cached mod.

        Args:
            mod_id: Mod ID.
            max_age_hours: Maximum age of cached data in hours.

        Returns:
            Cached mod or None if not found or expired.
        """
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data, cached_at FROM mods
                WHERE mod_id = ?
            """,
                (mod_id,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            data_json, cached_at_str = row
            cached_at = datetime.fromisoformat(cached_at_str)

            # Check if expired
            if datetime.now() - cached_at > timedelta(hours=max_age_hours):
                return None

            data = json.loads(data_json)
            return NexusMod(**data)
        except Exception as e:
            logger.warning(f"Failed to retrieve cached mod {mod_id}: {e}")
            return None
        finally:
            conn.close()

    def cache_mod_files(self, mod_id: int, files: list[NexusModFile]) -> None:
        """Cache mod files list.

        Args:
            mod_id: Mod ID.
            files: List of mod files to cache.
        """
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()

            # Delete old entries for this mod
            cursor.execute("DELETE FROM mod_files WHERE mod_id = ?", (mod_id,))

            # Insert new entries
            for mod_file in files:
                cursor.execute(
                    """
                    INSERT INTO mod_files (mod_id, file_id, data, cached_at)
                    VALUES (?, ?, ?, ?)
                """,
                    (
                        mod_id,
                        mod_file.file_id,
                        mod_file.model_dump_json(),
                        datetime.now(),
                    ),
                )

            conn.commit()
        finally:
            conn.close()

    def get_mod_files(self, mod_id: int, max_age_minutes: int = 15) -> Optional[list[NexusModFile]]:
        """Get cached mod files.

        Args:
            mod_id: Mod ID.
            max_age_minutes: Maximum age of cached data in minutes.

        Returns:
            List of cached mod files or None if not found or expired.
        """
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data, cached_at FROM mod_files
                WHERE mod_id = ?
                ORDER BY file_id
            """,
                (mod_id,),
            )
            rows = cursor.fetchall()

            if not rows:
                return None

            # Check if any entry is expired
            files = []
            for data_json, cached_at_str in rows:
                cached_at = datetime.fromisoformat(cached_at_str)
                if datetime.now() - cached_at > timedelta(minutes=max_age_minutes):
                    return None

                data = json.loads(data_json)
                files.append(NexusModFile(**data))

            return files
        except Exception as e:
            logger.warning(f"Failed to retrieve cached files for mod {mod_id}: {e}")
            return None
        finally:
            conn.close()

    def cache_mod_list(self, list_type: str, mods: list[NexusMod]) -> None:
        """Cache a list of mods (trending, latest, updated).

        Args:
            list_type: Type of list (trending, latest, updated).
            mods: List of mods to cache.
        """
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()

            # Serialize list
            data_json = json.dumps([mod.model_dump(mode="json") for mod in mods])

            cursor.execute(
                """
                INSERT OR REPLACE INTO mod_lists (list_type, data, cached_at)
                VALUES (?, ?, ?)
            """,
                (list_type, data_json, datetime.now()),
            )
            conn.commit()
        finally:
            conn.close()

    def get_mod_list(self, list_type: str, max_age_minutes: int = 15) -> Optional[list[NexusMod]]:
        """Get a cached mod list.

        Args:
            list_type: Type of list (trending, latest, updated).
            max_age_minutes: Maximum age of cached data in minutes.

        Returns:
            List of cached mods or None if not found or expired.
        """
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT data, cached_at FROM mod_lists
                WHERE list_type = ?
            """,
                (list_type,),
            )
            row = cursor.fetchone()

            if not row:
                return None

            data_json, cached_at_str = row
            cached_at = datetime.fromisoformat(cached_at_str)

            # Check if expired
            if datetime.now() - cached_at > timedelta(minutes=max_age_minutes):
                return None

            data_list = json.loads(data_json)
            return [NexusMod(**item) for item in data_list]
        except Exception as e:
            logger.warning(f"Failed to retrieve cached list {list_type}: {e}")
            return None
        finally:
            conn.close()

    def clear_expired(self, mod_max_age_hours: int = 24, list_max_age_hours: int = 1) -> int:
        """Clear expired cache entries.

        Args:
            mod_max_age_hours: Maximum age for mod details.
            list_max_age_hours: Maximum age for mod lists.

        Returns:
            Number of entries deleted.
        """
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()
            total_deleted = 0

            # Clear old mods
            mod_cutoff = datetime.now() - timedelta(hours=mod_max_age_hours)
            cursor.execute("DELETE FROM mods WHERE cached_at < ?", (mod_cutoff,))
            total_deleted += cursor.rowcount

            # Clear old files
            cursor.execute("DELETE FROM mod_files WHERE cached_at < ?", (mod_cutoff,))
            total_deleted += cursor.rowcount

            # Clear old lists
            list_cutoff = datetime.now() - timedelta(hours=list_max_age_hours)
            cursor.execute("DELETE FROM mod_lists WHERE cached_at < ?", (list_cutoff,))
            total_deleted += cursor.rowcount

            conn.commit()
            return total_deleted
        finally:
            conn.close()

    def clear_all(self) -> None:
        """Clear all cached data."""
        conn = sqlite3.connect(self.cache_db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM mods")
            cursor.execute("DELETE FROM mod_files")
            cursor.execute("DELETE FROM mod_lists")
            conn.commit()
        finally:
            conn.close()
