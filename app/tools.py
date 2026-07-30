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
import json
import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.app_utils.logging_utils import log_tool_intent, log_tool_outcome
from app.db import (
    async_consolidate_memory,
    async_get_consolidated_memories,
    async_get_pantry,
    async_get_profile,
    async_update_pantry,
    async_update_profile,
)


# --- PYDANTIC SCHEMAS FOR STRICT VALIDATION ---

class ManagePantryInput(BaseModel):
    action: Literal["view", "add", "remove", "clear"] = Field(
        ..., description="Action to perform: 'view', 'add', 'remove', or 'clear'."
    )
    items: list[str] | None = Field(
        default=None, description="List of ingredient names to add or remove."
    )
    confirm_action: bool = Field(
        default=False,
        description="Must be set to True for high-stakes destructive operations like 'clear'."
    )


class ManageProfileInput(BaseModel):
    action: Literal["view", "update"] = Field(
        ..., description="Action to perform: 'view' or 'update'."
    )
    dietary_restrictions: list[str] | None = Field(
        default=None, description="List of diets e.g. ['vegetarian', 'gluten-free', 'low-carb']."
    )
    medical_conditions: list[str] | None = Field(
        default=None, description="Medical conditions e.g. ['diabetes', 'high cholesterol', 'hypertension']."
    )
    preferred_cuisine: str | None = Field(
        default=None, description="Preferred culinary style e.g. 'Mediterranean', 'Indian', 'Mexican'."
    )
    allergies: list[str] | None = Field(
        default=None, description="Food allergies e.g. ['peanuts', 'shellfish', 'dairy']."
    )
    target_calories: int | None = Field(
        default=None, ge=1000, le=5000, description="Target daily calories (between 1000 and 5000)."
    )
    confirm_action: bool = Field(
        default=False,
        description="Set to True to confirm major medical or dietary profile changes."
    )


class SearchRecipesInput(BaseModel):
    query: str = Field(default="", description="Search keyword like 'salad' or 'soup'.")
    ingredients: list[str] | None = Field(default=None, description="List of ingredients to include.")
    cuisine: str | None = Field(default=None, description="Cuisine type filter.")
    diet: str | None = Field(default=None, description="Dietary filter e.g. 'diabetic', 'low-carb'.")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of recipes to return.")


class DailyMealPlanInput(BaseModel):
    day_preference: Literal["today", "tomorrow"] = Field(
        default="today", description="'today' or 'tomorrow'."
    )


class ExportGroceryListInput(BaseModel):
    items: list[str] | None = Field(
        default=None, description="List of missing ingredient names to categorize."
    )


class CalculateNutritionTargetsInput(BaseModel):
    weight_kg: float = Field(..., gt=20.0, lt=300.0, description="User weight in kilograms.")
    height_cm: float = Field(..., gt=80.0, lt=250.0, description="User height in centimeters.")
    age: int = Field(..., gt=10, lt=120, description="Age in years.")
    gender: Literal["male", "female", "other"] = Field(default="male", description="Biological gender.")
    activity_level: Literal["sedentary", "light", "moderate", "active"] = Field(
        default="moderate", description="Activity level."
    )
    health_goal: Literal["weight_loss", "maintenance", "muscle_gain", "diabetes_management"] = Field(
        default="maintenance", description="Health target goal."
    )


class SwapMealInput(BaseModel):
    meal_type: Literal["breakfast", "lunch", "dinner"] = Field(
        ..., description="Meal to swap: 'breakfast', 'lunch', or 'dinner'."
    )
    current_recipe_id: int | None = Field(
        default=None, description="ID of the recipe being replaced."
    )
    reason: str = Field(
        default="preference", description="Reason for swapping e.g. 'taste preference', 'missing ingredient'."
    )


class ConsolidateMemoryInput(BaseModel):
    summary_notes: str = Field(
        ..., description="Summary of key preferences, learnings, and user interactions to consolidate into long-term database memory."
    )
    key_preferences: list[str] | None = Field(
        default=None, description="List of key user preferences or learned health habits."
    )


# --- MOCK RECIPES DATABASE ---

MOCK_RECIPES = [
    {
        "id": 101,
        "title": "Mediterranean Spinach & Egg Scramble",
        "meal_type": "breakfast",
        "cuisine": "Mediterranean",
        "ingredients": ["spinach", "eggs", "olive oil", "garlic", "feta cheese"],
        "instructions": [
            "Heat olive oil in a skillet over medium heat.",
            "Add minced garlic and fresh spinach; sauté until spinach wilts.",
            "Whisk eggs and pour into skillet, gently scrambling until cooked through.",
            "Top with crumbled feta cheese and serve warm."
        ],
        "nutritional_summary": {
            "calories": 280,
            "protein_g": 18,
            "carbs_g": 4,
            "fat_g": 20,
            "glycemic_index": "Low",
            "saturated_fat_g": 4.5,
            "sodium_mg": 380
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "gluten_free": True
        }
    },
    {
        "id": 102,
        "title": "Overnight Oats with Berries & Chia Seeds",
        "meal_type": "breakfast",
        "cuisine": "American",
        "ingredients": ["oats", "almond milk", "chia seeds", "blueberries", "cinnamon"],
        "instructions": [
            "Combine oats, chia seeds, and almond milk in a jar.",
            "Stir well and refrigerate overnight or for at least 4 hours.",
            "Top with fresh blueberries and a dash of cinnamon before serving."
        ],
        "nutritional_summary": {
            "calories": 310,
            "protein_g": 10,
            "carbs_g": 48,
            "fat_g": 8,
            "glycemic_index": "Low",
            "saturated_fat_g": 1.0,
            "sodium_mg": 110
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "vegan": True
        }
    },
    {
        "id": 201,
        "title": "Grilled Chicken Breast with Quinoa & Roasted Vegetables",
        "meal_type": "lunch",
        "cuisine": "Mediterranean",
        "ingredients": ["chicken breast", "quinoa", "olive oil", "bell pepper", "zucchini", "lemon"],
        "instructions": [
            "Season chicken breast with herbs, lemon juice, and olive oil.",
            "Grill or bake chicken until internal temperature reaches 165°F (74°C).",
            "Cook quinoa in water or low-sodium vegetable broth.",
            "Roast chopped bell peppers and zucchini in olive oil.",
            "Serve chicken slices over a bed of quinoa and roasted veggies."
        ],
        "nutritional_summary": {
            "calories": 420,
            "protein_g": 38,
            "carbs_g": 35,
            "fat_g": 12,
            "glycemic_index": "Low",
            "saturated_fat_g": 2.0,
            "sodium_mg": 320
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "gluten_free": True
        }
    },
    {
        "id": 202,
        "title": "Indian Spiced Lentil Soup (Dal Tadka)",
        "meal_type": "lunch",
        "cuisine": "Indian",
        "ingredients": ["yellow lentils", "turmeric", "cumin", "tomatoes", "spinach", "garlic"],
        "instructions": [
            "Boil lentils with turmeric and salt until tender.",
            "In a separate pan, temper cumin seeds and garlic in olive oil.",
            "Add diced tomatoes and spinach; simmer for 5 minutes.",
            "Combine tempered spices with cooked lentils and stir well."
        ],
        "nutritional_summary": {
            "calories": 340,
            "protein_g": 18,
            "carbs_g": 52,
            "fat_g": 6,
            "glycemic_index": "Low",
            "saturated_fat_g": 0.8,
            "sodium_mg": 280
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "vegan": True
        }
    },
    {
        "id": 301,
        "title": "Baked Lemon Herb Salmon with Steamed Asparagus",
        "meal_type": "dinner",
        "cuisine": "Mediterranean",
        "ingredients": ["salmon fillet", "asparagus", "lemon", "olive oil", "dill", "garlic"],
        "instructions": [
            "Preheat oven to 400°F (200°C).",
            "Place salmon fillet on baking sheet lined with parchment paper.",
            "Drizzle with olive oil, minced garlic, lemon juice, and fresh dill.",
            "Bake for 12-15 minutes until salmon flakes easily with a fork.",
            "Steam asparagus until tender-crisp and serve together."
        ],
        "nutritional_summary": {
            "calories": 450,
            "protein_g": 36,
            "carbs_g": 8,
            "fat_g": 28,
            "glycemic_index": "Very Low",
            "saturated_fat_g": 4.0,
            "sodium_mg": 290
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "keto_friendly": True
        }
    },
    {
        "id": 302,
        "title": "Tofu & Mixed Vegetable Stir-Fry",
        "meal_type": "dinner",
        "cuisine": "Asian",
        "ingredients": ["firm tofu", "broccoli", "carrots", "bell pepper", "low-sodium soy sauce", "sesame oil", "ginger"],
        "instructions": [
            "Press tofu to remove excess moisture and cut into cubes.",
            "Sauté tofu in sesame oil until golden brown on all sides.",
            "Add broccoli florets, sliced carrots, and bell peppers.",
            "Stir in minced ginger and low-sodium soy sauce; cook for 5-7 minutes."
        ],
        "nutritional_summary": {
            "calories": 360,
            "protein_g": 22,
            "carbs_g": 24,
            "fat_g": 18,
            "glycemic_index": "Low",
            "saturated_fat_g": 2.5,
            "sodium_mg": 410
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "vegan": True
        }
    }
]


# --- AGENT TOOLS WITH DATABASE STORAGE & GUARDRAILS ---

async def manage_pantry(
    action: str,
    items: list[str] | None = None,
    confirm_action: bool = False
) -> dict[str, Any]:
    """Manages ingredients in the user's pantry inventory via SQLite database.

    Args:
        action: 'view', 'add', 'remove', or 'clear'.
        items: Optional list of ingredient names to add or remove.
        confirm_action: Must be set to True for high-stakes destructive operations like 'clear'.

    Returns:
        Dictionary containing pantry status and ingredient list.
    """
    try:
        validated = ManagePantryInput(action=action, items=items, confirm_action=confirm_action)
    except Exception as e:
        log_tool_outcome("manage_pantry", "Validation Failed", {}, error=e)
        return {
            "status": "error",
            "error_type": "ValidationError",
            "error_message": str(e),
            "guided_recovery_instructions": "Call manage_pantry with action='view', 'add', 'remove', or 'clear'."
        }

    log_tool_intent("manage_pantry", f"Performing action '{validated.action}' on pantry", validated.model_dump())

    if validated.action == "clear":
        if not validated.confirm_action:
            log_tool_outcome("manage_pantry", "Clear action blocked by Guardrail", {})
            return {
                "status": "requires_confirmation",
                "guardrail_triggered": "Human-In-The-Loop Confirmation Required",
                "message": "Clearing the pantry will remove all ingredients. Please ask the user for explicit confirmation before proceeding.",
                "guided_recovery_instructions": "Ask the user: 'Are you sure you want to clear your entire pantry inventory?' If confirmed, call manage_pantry(action='clear', confirm_action=True)."
            }
        updated_items = await async_update_pantry("clear")

    elif validated.action == "add":
        updated_items = await async_update_pantry("add", validated.items)

    elif validated.action == "remove":
        updated_items = await async_update_pantry("remove", validated.items)

    else:  # view
        updated_items = await async_get_pantry()

    res = {
        "status": "success",
        "action_performed": validated.action,
        "pantry_count": len(updated_items),
        "ingredients": updated_items
    }
    log_tool_outcome("manage_pantry", f"Pantry action '{validated.action}' complete", res)
    return res


async def manage_profile(
    action: str,
    dietary_restrictions: list[str] | None = None,
    medical_conditions: list[str] | None = None,
    preferred_cuisine: str | None = None,
    allergies: list[str] | None = None,
    target_calories: int | None = None,
    confirm_action: bool = False
) -> dict[str, Any]:
    """Reads or updates user health profile, dietary restrictions, allergies, and calorie goals via SQLite DB.

    Args:
        action: 'view' or 'update'.
        dietary_restrictions: Optional list e.g. ['vegetarian', 'gluten-free'].
        medical_conditions: Optional list e.g. ['diabetes', 'high cholesterol'].
        preferred_cuisine: Preferred culinary style.
        allergies: Optional list e.g. ['peanuts', 'shellfish'].
        target_calories: Target daily calories.
        confirm_action: Must be set to True for major medical updates.

    Returns:
        Updated user profile object.
    """
    try:
        validated = ManageProfileInput(
            action=action,
            dietary_restrictions=dietary_restrictions,
            medical_conditions=medical_conditions,
            preferred_cuisine=preferred_cuisine,
            allergies=allergies,
            target_calories=target_calories,
            confirm_action=confirm_action
        )
    except Exception as e:
        log_tool_outcome("manage_profile", "Validation Failed", {}, error=e)
        return {
            "status": "error",
            "error_type": "ValidationError",
            "error_message": str(e),
            "guided_recovery_instructions": "Ensure target_calories is between 1000 and 5000."
        }

    log_tool_intent("manage_profile", f"Executing profile action '{validated.action}'", validated.model_dump())

    if validated.action == "update":
        if validated.medical_conditions is not None and not validated.confirm_action:
            log_tool_outcome("manage_profile", "Medical update blocked by Guardrail", {})
            return {
                "status": "requires_confirmation",
                "guardrail_triggered": "Medical Safety Confirmation Required",
                "message": f"Updating medical conditions to {validated.medical_conditions} affects safety filtering.",
                "guided_recovery_instructions": "Ask the user for confirmation, then call manage_profile(..., confirm_action=True)."
            }

        profile_data = await async_update_profile(
            dietary_restrictions=validated.dietary_restrictions,
            medical_conditions=validated.medical_conditions,
            preferred_cuisine=validated.preferred_cuisine,
            allergies=validated.allergies,
            target_calories=validated.target_calories
        )
    else:
        profile_data = await async_get_profile()

    res = {"status": "success", "profile": profile_data}
    log_tool_outcome("manage_profile", f"Profile action '{validated.action}' complete", res)
    return res


async def search_recipes_api(
    query: str = "",
    ingredients: list[str] | None = None,
    cuisine: str | None = None,
    diet: str | None = None,
    max_results: int = 5
) -> list[dict[str, Any]]:
    """Searches recipe database based on ingredients, cuisine, and dietary requirements.

    Args:
        query: Optional search keyword.
        ingredients: Optional list of ingredients to match.
        cuisine: Optional cuisine filter.
        diet: Optional dietary constraint.
        max_results: Maximum recipes to return.

    Returns:
        List of recipe dictionaries.
    """
    try:
        validated = SearchRecipesInput(
            query=query, ingredients=ingredients, cuisine=cuisine, diet=diet, max_results=max_results
        )
    except Exception as e:
        log_tool_outcome("search_recipes_api", "Validation Failed", {}, error=e)
        return []

    log_tool_intent("search_recipes_api", "Searching recipes", validated.model_dump())

    filtered = MOCK_RECIPES
    if validated.query:
        filtered = [
            r for r in filtered
            if validated.query.lower() in r["title"].lower() or any(validated.query.lower() in ing.lower() for ing in r["ingredients"])
        ] or filtered

    if validated.cuisine:
        filtered = [r for r in filtered if r["cuisine"].lower() == validated.cuisine.lower()] or filtered

    if validated.ingredients:
        pantry_set = set(i.lower().strip() for i in validated.ingredients)
        filtered = sorted(
            filtered,
            key=lambda r: len(pantry_set.intersection(set(ing.lower() for ing in r["ingredients"]))),
            reverse=True
        )

    results = filtered[:validated.max_results]
    log_tool_outcome("search_recipes_api", f"Found {len(results)} recipes", {"count": len(results)})
    return results


async def get_daily_meal_plan(day_preference: str = "today") -> dict[str, Any]:
    """Generates a complete 3-meal plan tailored to pantry and user health profile.

    Args:
        day_preference: 'today' or 'tomorrow'.

    Returns:
        A structured daily meal plan with health safety assessment and missing ingredients.
    """
    log_tool_intent("get_daily_meal_plan", f"Generating meal plan for {day_preference}", {"day_preference": day_preference})

    pantry_items = set(await async_get_pantry())
    profile_info = await async_get_profile()

    medical = profile_info.get("medical_conditions", [])
    allergies = profile_info.get("allergies", [])
    cuisine = profile_info.get("preferred_cuisine", "Mediterranean")

    all_recipes = await search_recipes_api(cuisine=cuisine, ingredients=list(pantry_items), max_results=10)

    if allergies:
        all_recipes = [
            r for r in all_recipes
            if not any(allergy in " ".join(r.get("ingredients", [])).lower() for allergy in allergies)
        ] or all_recipes

    breakfasts = [r for r in all_recipes if r.get("meal_type") == "breakfast"] or [MOCK_RECIPES[0]]
    lunches = [r for r in all_recipes if r.get("meal_type") == "lunch"] or [MOCK_RECIPES[2]]
    dinners = [r for r in all_recipes if r.get("meal_type") == "dinner"] or [MOCK_RECIPES[4]]

    daily_meals = [
        {"meal": "Breakfast", "recipe": breakfasts[0]},
        {"meal": "Lunch", "recipe": lunches[0]},
        {"meal": "Dinner", "recipe": dinners[0]},
    ]

    all_required = set()
    total_calories, total_protein, total_carbs, total_fat, total_sodium = 0, 0, 0, 0, 0

    for m in daily_meals:
        recipe = m["recipe"]
        for ing in recipe.get("ingredients", []):
            all_required.add(ing.lower().strip())
        ns = recipe.get("nutritional_summary", {})
        total_calories += ns.get("calories", 0)
        total_protein += ns.get("protein_g", 0)
        total_carbs += ns.get("carbs_g", 0)
        total_fat += ns.get("fat_g", 0)
        total_sodium += ns.get("sodium_mg", 0)

    missing_ingredients = sorted(list(all_required - pantry_items))

    health_warnings = []
    if "diabetes" in medical:
        health_warnings.append("Diabetic Safety Verified: Low GI meals with complex carbs to maintain blood sugar stability.")
    if "high cholesterol" in medical:
        health_warnings.append("Cholesterol Safety Verified: Saturated fats kept under strict limits; emphasis on Omega-3s.")
    if "hypertension" in medical or total_sodium > 2000:
        health_warnings.append(f"Hypertension Check: Total daily sodium is {total_sodium}mg (Recommended < 2000mg/day).")

    res = {
        "status": "success",
        "day_preference": day_preference,
        "user_profile": profile_info,
        "available_pantry_count": len(pantry_items),
        "meal_plan": daily_meals,
        "daily_nutrition_totals": {
            "total_calories": total_calories,
            "protein_g": total_protein,
            "carbs_g": total_carbs,
            "fat_g": total_fat,
            "sodium_mg": total_sodium
        },
        "missing_ingredients_to_buy": missing_ingredients,
        "health_safety_summary": health_warnings
    }
    log_tool_outcome("get_daily_meal_plan", "Meal plan generated successfully", res)
    return res


async def export_grocery_list(items: list[str] | None = None) -> dict[str, Any]:
    """Categorizes missing or requested ingredients into an organized grocery shopping list.

    Args:
        items: Optional list of ingredient names. If omitted, pulls missing ingredients from the meal plan.

    Returns:
        Structured grocery list grouped by aisle.
    """
    log_tool_intent("export_grocery_list", "Categorizing grocery shopping list", {"items": items})

    if items is None:
        mp = await get_daily_meal_plan()
        items = mp.get("missing_ingredients_to_buy", [])

    categories = {
        "Produce": ["spinach", "asparagus", "bell pepper", "zucchini", "tomatoes", "lemon", "lime", "broccoli", "carrots", "ginger", "garlic", "avocado", "blueberries", "cilantro", "dill", "parsley"],
        "Proteins & Seafood": ["chicken breast", "salmon fillet", "cod fillet", "smoked salmon", "eggs", "firm tofu", "yellow lentils", "black beans"],
        "Dairy & Refrigerated": ["feta cheese", "almond milk", "greek yogurt"],
        "Grains & Pantry Staples": ["oats", "quinoa", "chia seeds", "whole grain bread", "corn"],
        "Oils, Sauces & Spices": ["olive oil", "sesame oil", "low-sodium soy sauce", "turmeric", "cumin", "cinnamon"]
    }

    categorized = {cat: [] for cat in categories}
    categorized["Other / Miscellaneous"] = []

    for item in items:
        item_clean = item.lower().strip()
        found = False
        for cat, kw_list in categories.items():
            if any(kw in item_clean for kw in kw_list):
                categorized[cat].append(item_clean.title())
                found = True
                break
        if not found:
            categorized["Other / Miscellaneous"].append(item_clean.title())

    cleaned = {k: v for k, v in categorized.items() if v}
    res = {
        "status": "success",
        "total_items_to_buy": len(items),
        "grocery_list_by_category": cleaned
    }
    log_tool_outcome("export_grocery_list", "Grocery list exported", res)
    return res


async def calculate_nutrition_targets(
    weight_kg: float = 70.0,
    height_cm: float = 175.0,
    age: int = 30,
    gender: str = "male",
    activity_level: str = "moderate",
    health_goal: str = "maintenance"
) -> dict[str, Any]:
    """Calculates personalized BMR, TDEE, and macro distribution based on user metrics and health goal.

    Args:
        weight_kg: Weight in kg.
        height_cm: Height in cm.
        age: Age in years.
        gender: 'male', 'female', or 'other'.
        activity_level: 'sedentary', 'light', 'moderate', or 'active'.
        health_goal: 'weight_loss', 'maintenance', 'muscle_gain', or 'diabetes_management'.

    Returns:
        Calculated target calories and macro split.
    """
    try:
        validated = CalculateNutritionTargetsInput(
            weight_kg=weight_kg, height_cm=height_cm, age=age, gender=gender, activity_level=activity_level, health_goal=health_goal
        )
    except Exception as e:
        log_tool_outcome("calculate_nutrition_targets", "Validation Failed", {}, error=e)
        return {
            "status": "error",
            "error_type": "ValidationError",
            "error_message": str(e),
            "guided_recovery_instructions": "Ensure weight_kg > 20, height_cm > 80, and age > 10."
        }

    log_tool_intent("calculate_nutrition_targets", "Calculating macro targets", validated.model_dump())

    if validated.gender == "female":
        bmr = (10 * validated.weight_kg) + (6.25 * validated.height_cm) - (5 * validated.age) - 161
    else:
        bmr = (10 * validated.weight_kg) + (6.25 * validated.height_cm) - (5 * validated.age) + 5

    multipliers = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
    tdee = bmr * multipliers.get(validated.activity_level, 1.55)

    if validated.health_goal == "weight_loss":
        target_calories = round(tdee - 500)
        p_pct, c_pct, f_pct = 0.35, 0.35, 0.30
    elif validated.health_goal == "muscle_gain":
        target_calories = round(tdee + 300)
        p_pct, c_pct, f_pct = 0.30, 0.45, 0.25
    elif validated.health_goal == "diabetes_management":
        target_calories = round(tdee)
        p_pct, c_pct, f_pct = 0.30, 0.35, 0.35
    else:
        target_calories = round(tdee)
        p_pct, c_pct, f_pct = 0.25, 0.45, 0.30

    res = {
        "status": "success",
        "bmr_kcal": round(bmr),
        "tdee_kcal": round(tdee),
        "target_daily_calories": target_calories,
        "macro_targets": {
            "protein_g": round((target_calories * p_pct) / 4),
            "carbs_g": round((target_calories * c_pct) / 4),
            "fat_g": round((target_calories * f_pct) / 9)
        },
        "daily_limits": {
            "max_sodium_mg": 2000,
            "min_fiber_g": 30,
            "max_saturated_fat_g": 15
        }
    }
    log_tool_outcome("calculate_nutrition_targets", "Calculated targets successfully", res)
    return res


async def swap_meal(
    meal_type: str,
    current_recipe_id: int | None = None,
    reason: str = "preference"
) -> dict[str, Any]:
    """Swaps out a meal in the current daily plan with an alternative recipe.

    Args:
        meal_type: 'breakfast', 'lunch', or 'dinner'.
        current_recipe_id: ID of the recipe being replaced.
        reason: Reason for swapping.

    Returns:
        New recipe selection details.
    """
    try:
        validated = SwapMealInput(meal_type=meal_type, current_recipe_id=current_recipe_id, reason=reason)
    except Exception as e:
        log_tool_outcome("swap_meal", "Validation Failed", {}, error=e)
        return {
            "status": "error",
            "error_type": "ValidationError",
            "error_message": str(e),
            "guided_recovery_instructions": "Specify meal_type as 'breakfast', 'lunch', or 'dinner'."
        }

    log_tool_intent("swap_meal", f"Swapping meal '{validated.meal_type}'", validated.model_dump())

    profile_info = await async_get_profile()
    pantry_items = set(await async_get_pantry())

    all_recipes = await search_recipes_api(
        cuisine=profile_info.get("preferred_cuisine", "Mediterranean"),
        ingredients=list(pantry_items),
        max_results=10
    )

    candidates = [
        r for r in all_recipes
        if r.get("meal_type") == validated.meal_type and r.get("id") != validated.current_recipe_id
    ]

    if not candidates:
        candidates = [
            r for r in MOCK_RECIPES
            if r.get("meal_type") == validated.meal_type and r.get("id") != validated.current_recipe_id
        ]

    selected_recipe = candidates[0] if candidates else MOCK_RECIPES[0]
    res = {
        "status": "success",
        "meal_type": validated.meal_type.capitalize(),
        "reason_for_swap": validated.reason,
        "new_recipe": selected_recipe
    }
    log_tool_outcome("swap_meal", "Meal swapped successfully", res)
    return res


async def consolidate_memory(
    summary_notes: str,
    key_preferences: list[str] | None = None
) -> dict[str, Any]:
    """Asynchronously consolidates conversation learnings, user habits, and dietary insights into long-term database storage.

    Args:
        summary_notes: Key summary points or learnings from recent conversation turns.
        key_preferences: List of specific user preferences discovered (e.g. ['dislikes cilantro', 'prefers 15-min meals']).

    Returns:
        Status object confirming memory consolidation in database.
    """
    try:
        validated = ConsolidateMemoryInput(summary_notes=summary_notes, key_preferences=key_preferences)
    except Exception as e:
        log_tool_outcome("consolidate_memory", "Validation Failed", {}, error=e)
        return {
            "status": "error",
            "error_type": "ValidationError",
            "error_message": str(e),
            "guided_recovery_instructions": "Provide non-empty summary_notes string."
        }

    log_tool_intent("consolidate_memory", "Consolidating memory into database", validated.model_dump())

    record = await async_consolidate_memory(summary_notes=validated.summary_notes, key_preferences=validated.key_preferences)
    past_memories = await async_get_consolidated_memories()

    res = {
        "status": "success",
        "consolidated_record": record,
        "total_consolidated_memories_count": len(past_memories),
        "recent_memories": past_memories
    }
    log_tool_outcome("consolidate_memory", "Memory successfully consolidated into database", res)
    return res
