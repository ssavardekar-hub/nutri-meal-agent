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

import pytest
from app.tools import (
    calculate_nutrition_targets,
    consolidate_memory,
    export_grocery_list,
    get_daily_meal_plan,
    manage_pantry,
    manage_profile,
    search_recipes_api,
    swap_meal,
)


@pytest.mark.asyncio
async def test_manage_pantry_view_add_remove_clear(tmp_path, monkeypatch):
    test_db = tmp_path / "nutrimeal_test.db"
    monkeypatch.setattr("app.db.DB_FILE", test_db)

    res_init = await manage_pantry(action="view")
    assert res_init["status"] == "success"

    res_add = await manage_pantry(action="add", items=["Avocado", "Chia Seeds"])
    assert "avocado" in res_add["ingredients"]
    assert "chia seeds" in res_add["ingredients"]

    res_rem = await manage_pantry(action="remove", items=["spinach"])
    assert "spinach" not in res_rem["ingredients"]

    res_guardrail = await manage_pantry(action="clear")
    assert res_guardrail["status"] == "requires_confirmation"

    res_clear = await manage_pantry(action="clear", confirm_action=True)
    assert res_clear["pantry_count"] == 0
    assert res_clear["ingredients"] == []


@pytest.mark.asyncio
async def test_manage_profile_view_and_update(tmp_path, monkeypatch):
    test_db = tmp_path / "nutrimeal_test.db"
    monkeypatch.setattr("app.db.DB_FILE", test_db)

    res_init = await manage_profile(action="view")
    assert res_init["status"] == "success"

    res_update = await manage_profile(
        action="update",
        dietary_restrictions=["vegan", "gluten-free"],
        medical_conditions=["hypertension"],
        preferred_cuisine="Indian",
        allergies=["peanuts"],
        target_calories=1800,
        confirm_action=True
    )
    p = res_update["profile"]
    assert p["dietary_restrictions"] == ["vegan", "gluten-free"]
    assert p["medical_conditions"] == ["hypertension"]
    assert p["preferred_cuisine"] == "Indian"
    assert p["allergies"] == ["peanuts"]
    assert p["target_calories"] == 1800


@pytest.mark.asyncio
async def test_search_recipes_api_mock_fallback():
    recipes_spinach = await search_recipes_api(query="spinach")
    assert len(recipes_spinach) > 0

    recipes_med = await search_recipes_api(cuisine="Mediterranean")
    assert len(recipes_med) > 0


@pytest.mark.asyncio
async def test_get_daily_meal_plan(tmp_path, monkeypatch):
    test_db = tmp_path / "nutrimeal_test.db"
    monkeypatch.setattr("app.db.DB_FILE", test_db)

    await manage_pantry(action="add", items=["spinach", "eggs", "olive oil"])
    await manage_profile(action="update", medical_conditions=["diabetes", "hypertension"], confirm_action=True)

    plan = await get_daily_meal_plan(day_preference="today")
    assert plan["status"] == "success"
    assert len(plan["meal_plan"]) == 3


@pytest.mark.asyncio
async def test_export_grocery_list(tmp_path, monkeypatch):
    test_db = tmp_path / "nutrimeal_test.db"
    monkeypatch.setattr("app.db.DB_FILE", test_db)

    items_to_buy = ["asparagus", "salmon fillet", "feta cheese", "quinoa", "turmeric"]
    grocery = await export_grocery_list(items=items_to_buy)

    assert grocery["status"] == "success"
    cats = grocery["grocery_list_by_category"]
    assert "Produce" in cats


@pytest.mark.asyncio
async def test_calculate_nutrition_targets():
    targets = await calculate_nutrition_targets(
        weight_kg=75.0,
        height_cm=180.0,
        age=35,
        gender="male",
        activity_level="moderate",
        health_goal="weight_loss"
    )
    assert targets["status"] == "success"


@pytest.mark.asyncio
async def test_swap_meal(tmp_path, monkeypatch):
    test_db = tmp_path / "nutrimeal_test.db"
    monkeypatch.setattr("app.db.DB_FILE", test_db)

    swapped = await swap_meal(meal_type="breakfast", current_recipe_id=101, reason="taste preference")
    assert swapped["status"] == "success"


@pytest.mark.asyncio
async def test_consolidate_memory(tmp_path, monkeypatch):
    test_db = tmp_path / "nutrimeal_test.db"
    monkeypatch.setattr("app.db.DB_FILE", test_db)

    mem_res = await consolidate_memory(
        summary_notes="User prefers low sodium dinners and dislikes cilantro.",
        key_preferences=["no_cilantro", "low_sodium"]
    )
    assert mem_res["status"] == "success"
    assert mem_res["consolidated_record"]["summary_notes"] == "User prefers low sodium dinners and dislikes cilantro."
    assert mem_res["total_consolidated_memories_count"] > 0
