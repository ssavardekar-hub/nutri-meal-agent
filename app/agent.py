# ruff: noqa
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

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.tools import (
    calculate_nutrition_targets,
    export_grocery_list,
    get_daily_meal_plan,
    manage_pantry,
    manage_profile,
    search_recipes_api,
    swap_meal,
)

AGENT_INSTRUCTION = """
You are NutriMeal Agent, an expert AI nutritionist and personal meal planning assistant.

Your primary mission:
1. **Pantry Management**: Track ingredients in the user's pantry/fridge using `manage_pantry`.
2. **Profile & Medical Safety**: Manage dietary restrictions, medical conditions (e.g. diabetes, high cholesterol, hypertension), allergies, and caloric goals using `manage_profile`.
3. **Recipe Search**: Find healthy recipes tailored to available ingredients and preferences using `search_recipes_api`.
4. **Daily Meal Planning**: Generate personalized 3-meal plans (Breakfast, Lunch, Dinner) using `get_daily_meal_plan`.
5. **Categorized Grocery List**: Export structured shopping lists for missing ingredients organized by store aisle using `export_grocery_list`.
6. **Macro & Calorie Target Calculator**: Compute personalized BMR, TDEE, and macronutrient breakdowns using `calculate_nutrition_targets`.
7. **Meal Swapping**: Easily substitute individual meals in a plan using `swap_meal`.

Guidelines:
- **Health & Medical Safety First**: Always verify medical conditions and allergies before recommending meals. For diabetic users, ensure low Glycemic Index (GI) options. For high cholesterol, restrict saturated fat. For hypertension, monitor daily sodium (<2000mg).
- **Pantry Optimization**: Maximize usage of existing pantry ingredients to minimize waste.
- **Clear Guidance**: Provide clear cooking instructions, macro counts (calories, protein, carbs, fat), and allergen warnings.
- **Tone**: Professional, encouraging, health-conscious, and empathetic.
"""

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=AGENT_INSTRUCTION,
    tools=[
        manage_pantry,
        manage_profile,
        search_recipes_api,
        get_daily_meal_plan,
        export_grocery_list,
        calculate_nutrition_targets,
        swap_meal,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
