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
    export_grocery_list,
    get_daily_meal_plan,
    manage_pantry,
    manage_profile,
    search_recipes_api,
    swap_meal,
)


@pytest.mark.asyncio
async def test_manage_pantry_view_add_remove_clear(tmp_path, monkeypatch):
    test_pantry_file = tmp_path / "pantry.json"
    monkeypatch.setattr("app.tools.PANTRY_FILE", test_pantry_file)

    # Initial view should set default items
    res_init = await manage_pantry(action="view")
    assert res_init["status"] == "success"
    assert "spinach" in res_init["ingredients"]

    # Add items
    res_add = await manage_pantry(action="add", items=["Avocado", "Chia Seeds"])
    assert "avocado" in res_add["ingredients"]
    assert "chia seeds" in res_add["ingredients"]

    # Remove item
    res_rem = await manage_pantry(action="remove", items=["spinach"])
    assert "spinach" not in res_rem["ingredients"]

    # Clear pantry without confirm_action triggers guardrail
    res_guardrail = await manage_pantry(action="clear")
    assert res_guardrail["status"] == "requires_confirmation"

    # Clear pantry with confirm_action=True
    res_clear = await manage_pantry(action="clear", confirm_action=True)
    assert res_clear["pantry_count"] == 0
    assert res_clear["ingredients"] == []


@pytest.mark.asyncio
async def test_manage_profile_view_and_update(tmp_path, monkeypatch):
    test_profile_file = tmp_path / "profile.json"
    monkeypatch.setattr("app.tools.PROFILE_FILE", test_profile_file)

    # Initial view
    res_init = await manage_profile(action="view")
    assert res_init["status"] == "success"
    assert "diabetes" in res_init["profile"]["medical_conditions"]

    # Update profile with confirm_action=True
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
    # Test query filter
    recipes_spinach = await search_recipes_api(query="spinach")
    assert len(recipes_spinach) > 0
    assert any("spinach" in r["title"].lower() or "spinach" in " ".join(r["ingredients"]).lower() for r in recipes_spinach)

    # Test cuisine filter
    recipes_med = await search_recipes_api(cuisine="Mediterranean")
    assert len(recipes_med) > 0
    assert all(r["cuisine"].lower() == "mediterranean" for r in recipes_med)


@pytest.mark.asyncio
async def test_get_daily_meal_plan(tmp_path, monkeypatch):
    test_pantry_file = tmp_path / "pantry.json"
    test_profile_file = tmp_path / "profile.json"
    monkeypatch.setattr("app.tools.PANTRY_FILE", test_pantry_file)
    monkeypatch.setattr("app.tools.PROFILE_FILE", test_profile_file)

    await manage_pantry(action="add", items=["spinach", "eggs", "olive oil"])
    await manage_profile(action="update", medical_conditions=["diabetes", "hypertension"], confirm_action=True)

    plan = await get_daily_meal_plan(day_preference="today")
    assert plan["status"] == "success"
    assert len(plan["meal_plan"]) == 3
    assert "total_calories" in plan["daily_nutrition_totals"]
    assert any("Diabetic Safety" in warning for warning in plan["health_safety_summary"])


@pytest.mark.asyncio
async def test_export_grocery_list(tmp_path, monkeypatch):
    test_pantry_file = tmp_path / "pantry.json"
    test_profile_file = tmp_path / "profile.json"
    monkeypatch.setattr("app.tools.PANTRY_FILE", test_pantry_file)
    monkeypatch.setattr("app.tools.PROFILE_FILE", test_profile_file)

    items_to_buy = ["asparagus", "salmon fillet", "feta cheese", "quinoa", "turmeric"]
    grocery = await export_grocery_list(items=items_to_buy)

    assert grocery["status"] == "success"
    cats = grocery["grocery_list_by_category"]
    assert "Produce" in cats
    assert "Asparagus" in cats["Produce"]
    assert "Proteins & Seafood" in cats
    assert "Salmon Fillet" in cats["Proteins & Seafood"]


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
    assert targets["target_daily_calories"] > 1000
    assert targets["macro_targets"]["protein_g"] > 0
    assert targets["daily_limits"]["max_sodium_mg"] == 2000


@pytest.mark.asyncio
async def test_swap_meal(tmp_path, monkeypatch):
    test_pantry_file = tmp_path / "pantry.json"
    test_profile_file = tmp_path / "profile.json"
    monkeypatch.setattr("app.tools.PANTRY_FILE", test_pantry_file)
    monkeypatch.setattr("app.tools.PROFILE_FILE", test_profile_file)

    swapped = await swap_meal(meal_type="breakfast", current_recipe_id=101, reason="taste preference")
    assert swapped["status"] == "success"
    assert swapped["meal_type"] == "Breakfast"
    assert swapped["new_recipe"]["id"] != 101
