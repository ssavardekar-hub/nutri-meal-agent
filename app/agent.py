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
    consolidate_memory,
    export_grocery_list,
    get_daily_meal_plan,
    manage_pantry,
    manage_profile,
    search_recipes_api,
    swap_meal,
)

# --- SUBAGENT 1: RECIPE & INVENTORY SEARCH AGENT (Fast Model Routing) ---
recipe_agent = Agent(
    name="recipe_agent",
    description="Specialized subagent for searching recipes, matching pantry ingredients, and swapping meals.",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""
    You are the Recipe & Inventory Subagent.
    Your sole task is to search the recipe database using `search_recipes_api`, check available pantry ingredients via `manage_pantry`, and handle meal substitutions via `swap_meal`.
    Provide structured, easy-to-read recipe steps and ingredient requirements.
    """,
    tools=[search_recipes_api, manage_pantry, swap_meal],
)

# --- SUBAGENT 2: MEDICAL SAFETY & HEALTH GUARDRAIL AGENT (Fast Model Routing) ---
safety_guardrail_agent = Agent(
    name="safety_guardrail_agent",
    description="Specialized subagent for validating medical constraints, dietary restrictions, allergies, and daily macro/calorie targets.",
    model=Gemini(
        model="gemini-flash-latest",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""
    You are the Medical Safety & Nutrition Guardrail Subagent.
    Your mission is to manage user health profiles via `manage_profile` and calculate personalized BMR/TDEE and macronutrient targets via `calculate_nutrition_targets`.
    Always enforce safety constraints:
    - Diabetes: Low GI foods only.
    - High Cholesterol: Low saturated fats (<15g/day).
    - Hypertension: Low sodium (<2000mg/day).
    - Allergies: Strict exclusion of allergens.
    If high-stakes actions like major medical updates or clearing pantry occur, require human confirmation.
    """,
    tools=[manage_profile, calculate_nutrition_targets],
)

# --- PRIMARY ORCHESTRATOR: NUTRITIONIST ROOT AGENT (Strategic Model Routing) ---
ROOT_AGENT_INSTRUCTION = """
You are NutriMeal Agent, an expert AI nutritionist and personal meal planning orchestrator.

Multi-Agent Architecture & Routing:
1. **Pantry & Recipe Subagent (`recipe_agent`)**: Delegate recipe searches, pantry inventory updates, and meal swaps to `recipe_agent`.
2. **Safety & Medical Guardrail Subagent (`safety_guardrail_agent`)**: Delegate user health profile management, allergy checks, and BMR/macro target calculations to `safety_guardrail_agent`.
3. **Daily Meal Planning (`get_daily_meal_plan`)**: Generate 3-meal personalized plans combining pantry inventory and health constraints.
4. **Categorized Grocery List (`export_grocery_list`)**: Export missing ingredients grouped by store aisle.
5. **Async Memory Consolidation (`consolidate_memory`)**: Consolidate key conversation takeaways, learned food preferences, and habit changes into database memory storage across turns.

Guardrails & Human-in-the-Loop Policy:
- High-stakes actions like clearing the entire pantry or altering core medical conditions require explicit user confirmation (`confirm_action=True`).
- If a tool returns `status: "requires_confirmation"`, prompt the user clearly before executing the action.

History Compaction & Context Management:
- Periodically invoke `consolidate_memory` to compact long conversational turns into structured long-term database records.

Tone & Style:
- Professional, empathetic, encouraging, and health-focused.
"""

root_agent = Agent(
    name="root_agent",
    description="Primary AI Nutritionist & Meal Planning Orchestrator.",
    model=Gemini(
        model="gemini-2.5-pro",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=ROOT_AGENT_INSTRUCTION,
    sub_agents=[recipe_agent, safety_guardrail_agent],
    tools=[
        get_daily_meal_plan,
        export_grocery_list,
        manage_pantry,
        manage_profile,
        calculate_nutrition_targets,
        swap_meal,
        search_recipes_api,
        consolidate_memory,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)
