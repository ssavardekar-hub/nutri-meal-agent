# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

DB_FILE = Path("nutrimeal.db")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db_sync() -> None:
    """Synchronously initializes SQLite schema tables for pantry, profile, and memory consolidation."""
    conn = _get_connection()
    cursor = conn.cursor()

    # System Metadata Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_metadata (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    # Pantry Items Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pantry_items (
            ingredient_name TEXT PRIMARY KEY,
            added_at TEXT
        )
    """)

    # User Profile Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            dietary_restrictions TEXT,
            medical_conditions TEXT,
            preferred_cuisine TEXT,
            allergies TEXT,
            target_calories INTEGER,
            updated_at TEXT
        )
    """)

    # Long-term Consolidated Memory & Vector/Text Context Store
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_consolidations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            summary_notes TEXT NOT NULL,
            key_preferences TEXT,
            consolidated_at TEXT
        )
    """)

    # Seed initial defaults on first table initialization only
    cursor.execute("SELECT value FROM system_metadata WHERE key = 'initialized'")
    meta_row = cursor.fetchone()
    if not meta_row:
        cursor.execute("""
            INSERT INTO user_profiles (id, dietary_restrictions, medical_conditions, preferred_cuisine, allergies, target_calories, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?)
        """, (
            json.dumps(["low-carb"]),
            json.dumps(["diabetes", "high cholesterol"]),
            "Mediterranean",
            json.dumps([]),
            2000,
            datetime.now(timezone.utc).isoformat()
        ))

        defaults = ["spinach", "eggs", "oats", "chicken breast", "olive oil", "salmon fillet", "quinoa", "garlic", "lemon"]
        for item in defaults:
            cursor.execute(
                "INSERT OR IGNORE INTO pantry_items (ingredient_name, added_at) VALUES (?, ?)",
                (item.lower().strip(), datetime.now(timezone.utc).isoformat())
            )

        cursor.execute("INSERT INTO system_metadata (key, value) VALUES ('initialized', 'true')")

    conn.commit()
    conn.close()


async def init_db() -> None:
    await asyncio.to_thread(init_db_sync)


# --- PANTRY DATABASE OPERATIONS ---

def _get_pantry_sync() -> list[str]:
    init_db_sync()
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_name FROM pantry_items ORDER BY ingredient_name ASC")
    rows = cursor.fetchall()
    conn.close()
    return [r["ingredient_name"] for r in rows]


def _update_pantry_sync(action: str, items: list[str] | None = None) -> list[str]:
    init_db_sync()
    conn = _get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()

    if action == "clear":
        cursor.execute("DELETE FROM pantry_items")
    elif action == "add" and items:
        for item in items:
            if item.strip():
                cursor.execute(
                    "INSERT OR REPLACE INTO pantry_items (ingredient_name, added_at) VALUES (?, ?)",
                    (item.lower().strip(), now_str)
                )
    elif action == "remove" and items:
        for item in items:
            cursor.execute(
                "DELETE FROM pantry_items WHERE ingredient_name = ?",
                (item.lower().strip(),)
            )

    conn.commit()
    conn.close()
    return _get_pantry_sync()


async def async_get_pantry() -> list[str]:
    return await asyncio.to_thread(_get_pantry_sync)


async def async_update_pantry(action: str, items: list[str] | None = None) -> list[str]:
    return await asyncio.to_thread(_update_pantry_sync, action, items)


# --- PROFILE DATABASE OPERATIONS ---

def _get_profile_sync() -> dict[str, Any]:
    init_db_sync()
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM user_profiles WHERE id = 1")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return {
            "dietary_restrictions": ["low-carb"],
            "medical_conditions": ["diabetes", "high cholesterol"],
            "preferred_cuisine": "Mediterranean",
            "allergies": [],
            "target_calories": 2000
        }

    return {
        "dietary_restrictions": json.loads(row["dietary_restrictions"]),
        "medical_conditions": json.loads(row["medical_conditions"]),
        "preferred_cuisine": row["preferred_cuisine"],
        "allergies": json.loads(row["allergies"]),
        "target_calories": row["target_calories"]
    }


def _update_profile_sync(
    dietary_restrictions: list[str] | None = None,
    medical_conditions: list[str] | None = None,
    preferred_cuisine: str | None = None,
    allergies: list[str] | None = None,
    target_calories: int | None = None
) -> dict[str, Any]:
    current = _get_profile_sync()
    if dietary_restrictions is not None:
        current["dietary_restrictions"] = [d.lower().strip() for d in dietary_restrictions]
    if medical_conditions is not None:
        current["medical_conditions"] = [m.lower().strip() for m in medical_conditions]
    if preferred_cuisine is not None:
        current["preferred_cuisine"] = preferred_cuisine.strip()
    if allergies is not None:
        current["allergies"] = [a.lower().strip() for a in allergies]
    if target_calories is not None:
        current["target_calories"] = target_calories

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_profiles
        SET dietary_restrictions = ?, medical_conditions = ?, preferred_cuisine = ?, allergies = ?, target_calories = ?, updated_at = ?
        WHERE id = 1
    """, (
        json.dumps(current["dietary_restrictions"]),
        json.dumps(current["medical_conditions"]),
        current["preferred_cuisine"],
        json.dumps(current["allergies"]),
        current["target_calories"],
        datetime.now(timezone.utc).isoformat()
    ))
    conn.commit()
    conn.close()
    return current


async def async_get_profile() -> dict[str, Any]:
    return await asyncio.to_thread(_get_profile_sync)


async def async_update_profile(
    dietary_restrictions: list[str] | None = None,
    medical_conditions: list[str] | None = None,
    preferred_cuisine: str | None = None,
    allergies: list[str] | None = None,
    target_calories: int | None = None
) -> dict[str, Any]:
    return await asyncio.to_thread(
        _update_profile_sync, dietary_restrictions, medical_conditions, preferred_cuisine, allergies, target_calories
    )


# --- MEMORY CONSOLIDATION DATABASE OPERATIONS ---

def _consolidate_memory_sync(summary_notes: str, key_preferences: list[str] | None = None) -> dict[str, Any]:
    init_db_sync()
    conn = _get_connection()
    cursor = conn.cursor()
    now_str = datetime.now(timezone.utc).isoformat()
    pref_str = json.dumps(key_preferences or [])

    cursor.execute("""
        INSERT INTO memory_consolidations (summary_notes, key_preferences, consolidated_at)
        VALUES (?, ?, ?)
    """, (summary_notes, pref_str, now_str))

    conn.commit()
    conn.close()
    return {
        "status": "success",
        "summary_notes": summary_notes,
        "key_preferences": key_preferences or [],
        "consolidated_at": now_str
    }


def _get_consolidated_memories_sync() -> list[dict[str, Any]]:
    init_db_sync()
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM memory_consolidations ORDER BY id DESC LIMIT 5")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r["id"],
            "summary_notes": r["summary_notes"],
            "key_preferences": json.loads(r["key_preferences"]),
            "consolidated_at": r["consolidated_at"]
        }
        for r in rows
    ]


async def async_consolidate_memory(summary_notes: str, key_preferences: list[str] | None = None) -> dict[str, Any]:
    return await asyncio.to_thread(_consolidate_memory_sync, summary_notes, key_preferences)


async def async_get_consolidated_memories() -> list[dict[str, Any]]:
    return await asyncio.to_thread(_get_consolidated_memories_sync)
