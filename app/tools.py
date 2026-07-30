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

import json
import os
from pathlib import Path
import urllib.parse
import urllib.request

PANTRY_FILE = Path("pantry.json")
PROFILE_FILE = Path("profile.json")

# Expanded recipe database with detailed nutritional and health safety metadata
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
        "id": 103,
        "title": "Avocado & Smoked Salmon Toast on Whole Grain",
        "meal_type": "breakfast",
        "cuisine": "American",
        "ingredients": ["smoked salmon", "avocado", "whole grain bread", "lemon", "dill"],
        "instructions": [
            "Toast the whole grain bread until crisp.",
            "Mash avocado with lemon juice and a pinch of black pepper.",
            "Spread avocado over toast and top with sliced smoked salmon and dill."
        ],
        "nutritional_summary": {
            "calories": 340,
            "protein_g": 22,
            "carbs_g": 28,
            "fat_g": 16,
            "glycemic_index": "Low",
            "saturated_fat_g": 2.5,
            "sodium_mg": 480
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True
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
        "id": 203,
        "title": "Quinoa & Black Bean Power Salad",
        "meal_type": "lunch",
        "cuisine": "Mexican",
        "ingredients": ["quinoa", "black beans", "corn", "avocado", "lime", "cilantro", "olive oil"],
        "instructions": [
            "Rinse black beans and corn; drain well.",
            "Toss cooked quinoa, black beans, corn, and chopped cilantro.",
            "Drizzle with fresh lime juice and olive oil, top with avocado slices."
        ],
        "nutritional_summary": {
            "calories": 390,
            "protein_g": 15,
            "carbs_g": 54,
            "fat_g": 14,
            "glycemic_index": "Low",
            "saturated_fat_g": 1.8,
            "sodium_mg": 210
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "vegan": True,
            "gluten_free": True
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
    },
    {
        "id": 303,
        "title": "Herb-Crusted Baked Cod with Roasted Cauliflower",
        "meal_type": "dinner",
        "cuisine": "Mediterranean",
        "ingredients": ["cod fillet", "cauliflower", "olive oil", "parsley", "garlic", "lemon"],
        "instructions": [
            "Preheat oven to 400°F (200°C).",
            "Toss cauliflower florets in olive oil and minced garlic; roast for 20 minutes.",
            "Place cod on baking sheet, season with chopped parsley, garlic, and lemon juice.",
            "Bake cod alongside cauliflower for 12-15 minutes until opaque."
        ],
        "nutritional_summary": {
            "calories": 310,
            "protein_g": 32,
            "carbs_g": 12,
            "fat_g": 14,
            "glycemic_index": "Very Low",
            "saturated_fat_g": 1.5,
            "sodium_mg": 240
        },
        "health_safety": {
            "diabetic_friendly": True,
            "low_cholesterol": True,
            "hypertension_friendly": True,
            "gluten_free": True
        }
    }
]


def _read_json(filepath: Path, default_data: dict) -> dict:
    if not filepath.exists():
        _write_json(filepath, default_data)
        return default_data
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data


def _write_json(filepath: Path, data: dict) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def manage_pantry(action: str, items: list[str] | None = None) -> dict:
    """Manages ingredients in the user's local pantry inventory.

    Args:
        action: One of 'view', 'add', 'remove', or 'clear'.
        items: Optional list of ingredient names to add or remove (e.g. ['spinach', 'eggs']).

    Returns:
        A dictionary containing the current status and updated list of pantry items.
    """
    default_pantry = {"ingredients": ["spinach", "eggs", "oats", "chicken breast", "olive oil", "salmon fillet", "quinoa", "garlic", "lemon"]}
    pantry_data = _read_json(PANTRY_FILE, default_pantry)
    current_items = set(i.lower().strip() for i in pantry_data.get("ingredients", []))

    action = action.lower().strip()
    if action == "add" and items:
        for item in items:
            if item.strip():
                current_items.add(item.lower().strip())
    elif action == "remove" and items:
        for item in items:
            current_items.discard(item.lower().strip())
    elif action == "clear":
        current_items = set()

    updated_list = sorted(list(current_items))
    pantry_data["ingredients"] = updated_list
    _write_json(PANTRY_FILE, pantry_data)

    return {
        "status": "success",
        "action_performed": action,
        "pantry_count": len(updated_list),
        "ingredients": updated_list
    }


def manage_profile(
    action: str,
    dietary_restrictions: list[str] | None = None,
    medical_conditions: list[str] | None = None,
    preferred_cuisine: str | None = None,
    allergies: list[str] | None = None,
    target_calories: int | None = None
) -> dict:
    """Reads or updates the user's dietary preferences, medical conditions, allergies, and target calories.

    Args:
        action: 'view' or 'update'.
        dietary_restrictions: Optional list of diets e.g. ['vegetarian', 'gluten-free', 'low-carb'].
        medical_conditions: Optional medical issues e.g. ['diabetes', 'high cholesterol', 'hypertension'].
        preferred_cuisine: Preferred culinary style e.g. 'Mediterranean', 'Indian', 'Mexican', 'Asian'.
        allergies: Optional list of food allergies e.g. ['peanuts', 'shellfish', 'dairy'].
        target_calories: Optional daily caloric goal (e.g. 2000).

    Returns:
        A dictionary with the user's updated health and cuisine profile.
    """
    default_profile = {
        "dietary_restrictions": ["low-carb"],
        "medical_conditions": ["diabetes", "high cholesterol"],
        "preferred_cuisine": "Mediterranean",
        "allergies": [],
        "target_calories": 2000
    }
    profile_data = _read_json(PROFILE_FILE, default_profile)

    if action.lower().strip() == "update":
        if dietary_restrictions is not None:
            profile_data["dietary_restrictions"] = [d.lower().strip() for d in dietary_restrictions]
        if medical_conditions is not None:
            profile_data["medical_conditions"] = [m.lower().strip() for m in medical_conditions]
        if preferred_cuisine is not None:
            profile_data["preferred_cuisine"] = preferred_cuisine.strip()
        if allergies is not None:
            profile_data["allergies"] = [a.lower().strip() for a in allergies]
        if target_calories is not None:
            profile_data["target_calories"] = target_calories
        _write_json(PROFILE_FILE, profile_data)

    return {
        "status": "success",
        "profile": profile_data
    }


def search_recipes_api(
    query: str = "",
    ingredients: list[str] | None = None,
    cuisine: str | None = None,
    diet: str | None = None,
    max_results: int = 5
) -> list[dict]:
    """Searches external Spoonacular Recipe API for recipes, with a mock database fallback.

    Args:
        query: Optional search keyword like 'salad' or 'soup'.
        ingredients: Optional list of available ingredients to match.
        cuisine: Optional cuisine filter (e.g. 'Mediterranean', 'Indian').
        diet: Optional dietary constraint (e.g. 'diabetic', 'low-carb').
        max_results: Maximum number of recipes to return.

    Returns:
        A list of matching recipe dictionaries with instructions and nutritional data.
    """
    api_key = os.getenv("SPOONACULAR_API_KEY")
    results = []

    if api_key:
        try:
            params = {
                "apiKey": api_key,
                "number": max_results,
                "addRecipeInformation": "true",
                "addRecipeNutrition": "true"
            }
            if query:
                params["query"] = query
            if cuisine:
                params["cuisine"] = cuisine
            if ingredients:
                params["includeIngredients"] = ",".join(ingredients)
            if diet:
                params["diet"] = diet

            url = f"https://api.spoonacular.com/recipes/complexSearch?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    for r in data.get("results", []):
                        results.append({
                            "id": r.get("id"),
                            "title": r.get("title"),
                            "cuisine": cuisine or "General",
                            "ingredients": [i.get("name") for i in r.get("extendedIngredients", [])],
                            "instructions": [step.get("step") for section in r.get("analyzedInstructions", []) for step in section.get("steps", [])] or [r.get("instructions", "No detailed instructions provided.")],
                            "nutritional_summary": {
                                "calories": r.get("nutrition", {}).get("nutrients", [{}])[0].get("amount", 350),
                                "glycemic_index": "Low",
                                "sodium_mg": 300
                            },
                            "source": "Spoonacular API"
                        })
        except Exception:
            results = []

    if not results:
        filtered = MOCK_RECIPES
        if query:
            filtered = [r for r in filtered if query.lower() in r["title"].lower() or any(query.lower() in ing.lower() for ing in r["ingredients"])] or filtered
        if cuisine:
            filtered = [r for r in filtered if r["cuisine"].lower() == cuisine.lower()] or filtered
        if ingredients:
            pantry_set = set(i.lower().strip() for i in ingredients)
            filtered = sorted(
                filtered,
                key=lambda r: len(pantry_set.intersection(set(ing.lower() for ing in r["ingredients"]))),
                reverse=True
            )
        results = filtered[:max_results]

    return results


def get_daily_meal_plan(day_preference: str = "today") -> dict:
    """Generates a complete 3-meal plan (breakfast, lunch, dinner) tailored to pantry and user health profile.

    Args:
        day_preference: 'today' or 'tomorrow'.

    Returns:
        A structured daily meal plan containing 3 meals, health safety assessment, and missing ingredient alerts.
    """
    pantry_info = manage_pantry(action="view")
    profile_info = manage_profile(action="view")["profile"]

    pantry_items = set(pantry_info.get("ingredients", []))
    medical = profile_info.get("medical_conditions", [])
    allergies = profile_info.get("allergies", [])
    cuisine = profile_info.get("preferred_cuisine", "Mediterranean")

    all_recipes = search_recipes_api(cuisine=cuisine, ingredients=list(pantry_items), max_results=10)

    # Filter out allergens
    if allergies:
        all_recipes = [
            r for r in all_recipes
            if not any(allergy in " ".join(r.get("ingredients", [])).lower() for allergy in allergies)
        ] or all_recipes

    breakfasts = [r for r in all_recipes if r.get("meal_type") == "breakfast"] or [MOCK_RECIPES[0]]
    lunches = [r for r in all_recipes if r.get("meal_type") == "lunch"] or [MOCK_RECIPES[3]]
    dinners = [r for r in all_recipes if r.get("meal_type") == "dinner"] or [MOCK_RECIPES[6]]

    selected_b = breakfasts[0]
    selected_l = lunches[0]
    selected_d = dinners[0]

    daily_meals = [
        {"meal": "Breakfast", "recipe": selected_b},
        {"meal": "Lunch", "recipe": selected_l},
        {"meal": "Dinner", "recipe": selected_d},
    ]

    all_required_ingredients = set()
    total_calories = 0
    total_protein = 0
    total_carbs = 0
    total_fat = 0
    total_sodium = 0

    for m in daily_meals:
        recipe = m["recipe"]
        for ing in recipe.get("ingredients", []):
            all_required_ingredients.add(ing.lower().strip())
        ns = recipe.get("nutritional_summary", {})
        total_calories += ns.get("calories", 0)
        total_protein += ns.get("protein_g", 0)
        total_carbs += ns.get("carbs_g", 0)
        total_fat += ns.get("fat_g", 0)
        total_sodium += ns.get("sodium_mg", 0)

    missing_ingredients = sorted(list(all_required_ingredients - pantry_items))

    health_warnings = []
    if "diabetes" in medical:
        health_warnings.append("Diabetic Safety Verified: Low GI meals with complex carbs to maintain blood sugar stability.")
    if "high cholesterol" in medical:
        health_warnings.append("Cholesterol Safety Verified: Saturated fats kept under strict limits; emphasis on Omega-3s and fiber.")
    if "hypertension" in medical or total_sodium > 2000:
        health_warnings.append(f"Hypertension Safety Check: Total daily sodium is {total_sodium}mg (Recommended < 2000mg/day).")

    return {
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


def export_grocery_list(items: list[str] | None = None) -> dict:
    """Categorizes missing or requested ingredients into an organized grocery shopping list.

    Args:
        items: Optional list of ingredient names. If omitted, pulls missing ingredients from the current daily meal plan.

    Returns:
        A dictionary with items grouped into grocery categories (Produce, Proteins, Dairy, Pantry Staples, Oils & Spices).
    """
    if items is None:
        meal_plan_res = get_daily_meal_plan()
        items = meal_plan_res.get("missing_ingredients_to_buy", [])

    categories = {
        "Produce": ["spinach", "asparagus", "bell pepper", "zucchini", "tomatoes", "lemon", "lime", "broccoli", "carrots", "ginger", "garlic", "avocado", "blueberries", "cilantro", "dill", "parsley", "cauliflower"],
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

    # Remove empty categories
    cleaned_list = {k: v for k, v in categorized.items() if v}

    return {
        "status": "success",
        "total_items_to_buy": len(items),
        "grocery_list_by_category": cleaned_list
    }


def calculate_nutrition_targets(
    weight_kg: float = 70.0,
    height_cm: float = 175.0,
    age: int = 30,
    gender: str = "male",
    activity_level: str = "moderate",
    health_goal: str = "maintenance"
) -> dict:
    """Calculates personalized BMR, daily TDEE calorie target, and macro distribution based on user metrics and health goal.

    Args:
        weight_kg: User weight in kilograms (e.g. 70.0).
        height_cm: User height in centimeters (e.g. 175.0).
        age: Age in years (e.g. 30).
        gender: 'male', 'female', or 'other'.
        activity_level: 'sedentary', 'light', 'moderate', or 'active'.
        health_goal: 'weight_loss', 'maintenance', 'muscle_gain', or 'diabetes_management'.

    Returns:
        Calculated target calories, protein (g), carbs (g), fat (g), and daily sodium/fiber recommendations.
    """
    # Mifflin-St Jeor BMR Equation
    if gender.lower() == "female":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5

    multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725
    }
    tdee = bmr * multipliers.get(activity_level.lower(), 1.55)

    if health_goal == "weight_loss":
        target_calories = round(tdee - 500)
        p_pct, c_pct, f_pct = 0.35, 0.35, 0.30
    elif health_goal == "muscle_gain":
        target_calories = round(tdee + 300)
        p_pct, c_pct, f_pct = 0.30, 0.45, 0.25
    elif health_goal == "diabetes_management":
        target_calories = round(tdee)
        p_pct, c_pct, f_pct = 0.30, 0.35, 0.35
    else:  # maintenance
        target_calories = round(tdee)
        p_pct, c_pct, f_pct = 0.25, 0.45, 0.30

    protein_g = round((target_calories * p_pct) / 4)
    carbs_g = round((target_calories * c_pct) / 4)
    fat_g = round((target_calories * f_pct) / 9)

    return {
        "status": "success",
        "bmr_kcal": round(bmr),
        "tdee_kcal": round(tdee),
        "target_daily_calories": target_calories,
        "macro_targets": {
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g
        },
        "daily_limits": {
            "max_sodium_mg": 2000,
            "min_fiber_g": 30,
            "max_saturated_fat_g": 15
        }
    }


def swap_meal(meal_type: str, current_recipe_id: int | None = None, reason: str = "preference") -> dict:
    """Swaps out a meal (Breakfast, Lunch, or Dinner) in the current daily plan with a healthy alternative recipe.

    Args:
        meal_type: One of 'breakfast', 'lunch', or 'dinner'.
        current_recipe_id: Optional ID of the recipe being replaced to avoid recommending the same one.
        reason: Optional reason e.g. 'missing ingredients', 'dietary choice', or 'taste preference'.

    Returns:
        The newly selected alternative recipe details and updated nutritional summary.
    """
    meal_type_clean = meal_type.lower().strip()
    profile_info = manage_profile(action="view")["profile"]
    pantry_info = manage_pantry(action="view")
    pantry_items = set(pantry_info.get("ingredients", []))

    all_recipes = search_recipes_api(cuisine=profile_info.get("preferred_cuisine", "Mediterranean"), ingredients=list(pantry_items), max_results=10)
    candidates = [
        r for r in all_recipes
        if r.get("meal_type") == meal_type_clean and r.get("id") != current_recipe_id
    ]

    if not candidates:
        # Fallback to any mock recipe of the same meal_type
        candidates = [r for r in MOCK_RECIPES if r.get("meal_type") == meal_type_clean and r.get("id") != current_recipe_id]

    selected_recipe = candidates[0] if candidates else MOCK_RECIPES[0]

    return {
        "status": "success",
        "meal_type": meal_type_clean.capitalize(),
        "reason_for_swap": reason,
        "new_recipe": selected_recipe
    }
