from __future__ import annotations

import json
import re
import traceback
import logging
from difflib import SequenceMatcher, get_close_matches
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("app.ai_agent")

from exceptions.service import AIServiceException
from repositories.meal_repository import load_master_meals
from repositories.chat_repository import load_preferences, save_preferences
from services.planner_service import fetch_daily_targets_service, get_meal_swap_options_service

from config.constants import (
    VALID_GOALS,
    VALID_ACTIVITY,
    VALID_DIET,
    VALID_CUISINES,
    VALID_GENDER,
    FIELD_ALIASES,
    FIELD_VALIDATORS,
)

SYSTEM_PROMPT = """You are {agent_name}, an intelligent diet companion and agent 🥦.
You have full context of the user's current profile, plan, and application state.
If the user asks questions about their plan (e.g., "why was this meal chosen?"), use their profile (especially their Goal and Diet Type) and the meal's ingredients/macros to explain why it's a good fit.

Profile: {profile_summary}
Plan Generated: {plan_status}
User prefs - Likes: {likes}, Dislikes: {dislikes}, Allergies: {allergies}.

Context meals: {rag_context}
Current plan: {plan_summary}

You can PERFORM ACTIONS on behalf of the user by appending an <ACTION> block to the END of your reply.
Valid views: inputs (page 1), chooseMeals (page 2), selectedMeals (page 3), plans (page 4).
Valid goals: {valid_goals}. Valid diet: {valid_diet}. Valid activity: {valid_activity}. Valid cuisine: {valid_cuisines}.

CRITICAL RULE FOR TYPOS/ACTIONS:
If the user makes a typo for an action (e.g., "take me to pagr 2", "change my heaight to 198", "change my dinner"), YOU MUST ASK FOR VERIFICATION.
Output your verification question AND the <ACTION> block together! The system will automatically hide the action and ask the user for confirmation.
Also output <QUICK_REPLIES>yes|no</QUICK_REPLIES>.

Action Examples:
- Navigate: <ACTION>{{"type":"SET_VIEW","view":"chooseMeals"}}</ACTION>
- Update profile: <ACTION>{{"type":"UPDATE_PROFILE","updates":{{"weightKg":"90"}}}}</ACTION>
- Open Swap Menu: <ACTION>{{"type":"OPEN_SWAP","dayIndex":0,"mealTime":"dinner"}}</ACTION>

Example Flow:
User: "take me to pagr 3"
Assistant: "It looks like you want to navigate to the Selected Meals page. Is that correct? <QUICK_REPLIES>yes|no</QUICK_REPLIES> <ACTION>{{"type":"SET_VIEW","view":"selectedMeals"}}</ACTION>"
"""

OLLAMA_MODEL = "gemma3:4b"

def _call_ollama(messages: List[dict]) -> str:
    try:
        import ollama
    except ImportError as e:
        raise AIServiceException("Local Ollama library is not installed or available") from e

    try:
        r = ollama.chat(model=OLLAMA_MODEL, messages=messages, options={"num_predict": 350, "temperature": 0.7})
        content = r["message"]["content"].strip()
        if not content:
            raise AIServiceException("Received empty response from Ollama AI model")
        return content
    except Exception as e:
        raise AIServiceException(f"Ollama AI model communication failed: {str(e)}") from e

def _search_meals(query: str, cuisine: str, top_k: int = 5) -> List[dict]:
    meals = load_master_meals(cuisine)
    if not meals:
        return []
    q = query.lower()
    scored = []
    for meal in meals:
        name = str(meal.get("meal_name") or meal.get("Name") or "")
        text = f"{name} {meal.get('description','')} {meal.get('ingredients','')} {meal.get('meal_time','')}".lower()
        score = sum(1.0 for w in q.split() if w in text) + SequenceMatcher(None, q, name.lower()).ratio() * 2
        if score > 0.3:
            scored.append((score, meal))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored[:top_k]]

def _format_meal_context(meals: List[dict]) -> str:
    if not meals:
        return "No relevant meals."
    lines = []
    for i, m in enumerate(meals, 1):
        name = m.get('meal_name') or m.get('Name', '?')
        ing = m.get('ingredients', '')
        goal = m.get('goal', '')
        diet = m.get('diet_type', '')
        lines.append(f"{i}. {name} (Goal: {goal}, Diet: {diet}). Ingredients: {ing[:200]}")
    return "\n".join(lines)

def _format_plan_summary(ctx: dict) -> str:
    if not ctx:
        return "No plan yet."
    pd = ctx.get("planSummary")
    if not pd:
        return "No plan yet."
    if isinstance(pd, list):
        return "\n".join(f"Day {d.get('day','?')}: " + ", ".join(f"{mt}:{n.get('name', n) if isinstance(n, dict) else n}" for mt,n in d.get("meals",{}).items()) for d in pd)
    return "Plan data available."

def _get_target_macros(ctx: dict, profile: dict, meal_time: str) -> dict:
    dist = {"early_morning": 0.05, "breakfast": 0.3, "mid_morning": 0.1, "lunch": 0.25, "evening": 0.1, "dinner": 0.15, "bedtime": 0.05}
    active_times = ctx.get("activeMealTimes", [])
    if not active_times:
        active_times = profile.get("mealTimes", [])
    selected = [t for t in active_times if t in dist]
    total_w = sum(dist[t] for t in selected)
    w = dist[meal_time] / total_w if total_w > 0 else dist.get(meal_time, 0)
    
    targets = fetch_daily_targets_service(profile)
    return {
        "caloriesKcal": targets.get("dailyCalories", 0) * w,
        "proteinG": targets.get("proteinG", 0) * w,
        "carbsG": targets.get("carbsG", 0) * w,
        "fatG": targets.get("fatG", 0) * w,
        "fiberG": targets.get("fiberG", 0) * w
    }

def _get_real_swap_options(profile_dict: dict, meal_time: str, current_meal_id: str, allowed_meal_ids: list = None, top_n: int = 5, target_macros: dict = None) -> list:
    try:
        cuisine = profile_dict.get("cuisineType") or "north_indian"
        result = get_meal_swap_options_service(
            profile=profile_dict,
            meal_time=meal_time,
            current_meal_id=current_meal_id or "",
            target_macros=target_macros,
            exclude_meal_ids=[],
            allowed_meal_ids=allowed_meal_ids or [],
            top_n=top_n,
            cuisine=cuisine
        )
        return result.get("options", [])
    except Exception as e:
        logger.error(f"[Chat Swap] Error: {e}", exc_info=True)
        return []

def _extract_preferences(message: str, prefs: dict) -> dict:
    msg = message.lower()
    for pat in [r"i (?:really )?love (.+?)(?:\.|!|$)", r"i (?:really )?like (.+?)(?:\.|!|$)"]:
        m = re.search(pat, msg)
        if m:
            food = m.group(1).strip().title()
            if food and food not in prefs["likes"]: prefs["likes"].append(food)
    for pat in [r"i (?:don'?t|do not) like (.+?)(?:\.|!|$)", r"i hate (.+?)(?:\.|!|$)"]:
        m = re.search(pat, msg)
        if m:
            food = m.group(1).strip().title()
            if food and food not in prefs["dislikes"]: prefs["dislikes"].append(food)
    for pat in [r"(?:allergic|allergy)\s*(?:to|from)\s+(.+?)(?:\.|!|$)", r"i have (?:a )?(.+?) allergy"]:
        m = re.search(pat, msg)
        if m:
            a = m.group(1).strip().title()
            if a and a not in prefs["allergies"]: prefs["allergies"].append(a)
    return prefs

def _fuzzy_match_field(raw_field: str) -> Optional[str]:
    raw = raw_field.lower().strip()
    if raw in FIELD_ALIASES: return FIELD_ALIASES[raw]
    matches = get_close_matches(raw, FIELD_ALIASES.keys(), n=1, cutoff=0.6)
    if matches: return FIELD_ALIASES[matches[0]]
    return None

def _fuzzy_match_value(field: str, raw_value: str) -> Tuple[str, bool]:
    if field not in FIELD_VALIDATORS: return raw_value, True
    valid = FIELD_VALIDATORS[field]
    raw = raw_value.lower().strip().replace(" ", "_").replace("-", "_")
    if raw in valid: return raw, True
    matches = get_close_matches(raw, valid.keys(), n=1, cutoff=0.5)
    if matches: return matches[0], True
    label_map = {v.lower().replace(" ", "_"): k for k, v in valid.items()}
    matches = get_close_matches(raw, label_map.keys(), n=1, cutoff=0.5)
    if matches: return label_map[matches[0]], True
    return raw_value, False

def _detect_intent(msg: str, ctx: dict) -> Tuple[Optional[str], Optional[dict], Any]:
    m = msg.lower().strip()
    nav_map = {
        "inputs": [r"(?:page|screen|step)\s*1\b", r"\binput", r"start\s*over", r"begin", r"first\s*(?:page|screen|step)"],
        "chooseMeals": [r"(?:page|screen|step)\s*2\b", r"choose\s*meal", r"select\s*meal", r"pick\s*meal", r"second\s*(?:page|screen|step)", r"meal\s*select"],
        "selectedMeals": [r"(?:page|screen|step)\s*3\b", r"arrange", r"third\s*(?:page|screen|step)", r"assign\s*day"],
        "plans": [r"(?:page|screen|step)\s*4\b", r"\bplan\b", r"fourth\s*(?:page|screen|step)", r"result", r"final"],
    }
    for view, patterns in nav_map.items():
        for pat in patterns:
            if re.search(pat, m): return "navigate", {"view": view}, None

    why_match = re.search(r"why (?:was|is) (?:this|the)?\s*([a-z0-9_\-\s]+?)\s*(?:chosen|selected|suggested)?", m)
    if why_match:
        meal_q = why_match.group(1).strip()
        return "explain_meal", {"query": meal_q}, None

    profile_pat = re.search(r"(?:change|set|update|make|switch)\s+(?:my\s+)?([a-z\s]{3,20}?)\s*(?:=|to|is|as)\s+[\"']?([a-z0-9_.\-]+)[\"']?", m)
    if profile_pat:
        field = _fuzzy_match_field(profile_pat.group(1).strip())
        if field:
            raw_val = profile_pat.group(2).strip()
            if field in ("weightKg", "heightCm", "age"):
                num = re.search(r"(\d+\.?\d*)", raw_val)
                if num: return "update_profile", {field: num.group(1)}, None
            matched_val, is_valid = _fuzzy_match_value(field, raw_val)
            if is_valid: return "update_profile", {field: matched_val}, None
            return "invalid_option", {field: {"requested": raw_val, "valid": FIELD_VALIDATORS.get(field, {})}}, None

    num_shortcut = re.search(r"^([a-z]{2,10})\s*(?:=|-|:|to|is|as)?\s*(\d+\.?\d*)\b", m)
    if num_shortcut:
        field = _fuzzy_match_field(num_shortcut.group(1).strip())
        if field in ("weightKg", "heightCm", "age"):
            return "update_profile", {field: num_shortcut.group(2)}, None

    swap_match = re.search(r"^(?:can you )?swap\s+(?:my\s+)?(?:day\s*(\d+)\s+)?([a-z0-9_-]+)", m)
    if swap_match:
        day = int(swap_match.group(1) or 1) - 1
        mt_raw = swap_match.group(2).replace(" ", "_").replace("-", "_")
        mt_map = {"breakfast": "breakfast", "lunch": "lunch", "dinner": "dinner", "evening": "evening", "bedtime": "bedtime", "mid_morning": "mid_morning", "early_morning": "early_morning"}
        matches = get_close_matches(mt_raw, mt_map.keys(), n=1, cutoff=0.5)
        if matches: return "swap_meal", {"dayIndex": max(0, day), "mealTime": mt_map[matches[0]]}, None

    al = re.search(r"(?:allergic|allergy)\s*(?:to|from)\s+([\w\s]+?)(?:\.|!|,|$)", m)
    if al: return "allergy", {"allergen": al.group(1).strip()}, None
    ce = re.search(r"(?:can'?t|cannot|don'?t)\s+eat\s+([\w\s]+?)(?:\.|!|,|$)", m)
    if ce: return "allergy", {"allergen": ce.group(1).strip()}, None

    return None, None, None

def _build_intent_response(intent: str, data: dict, ctx: dict, prefs: dict, agent_name: str) -> Optional[dict]:
    if intent == "navigate":
        return {"reply": f"Taking you to **{data['view']}**! 📍", "action": {"type": "SET_VIEW", "view": data["view"]}}

    if intent == "explain_meal":
        query = data["query"]
        profile = ctx.get("profile", {})
        plan_summary = ctx.get("planSummary") or []
        found_meal = None
        for d in plan_summary:
            for mt, m_data in d.get("meals", {}).items():
                name = m_data.get("name", "") if isinstance(m_data, dict) else m_data
                if query in mt.lower() or query in name.lower():
                    found_meal = name
                    break
        if not found_meal: found_meal = query.title()
        
        goal = profile.get("goal", "nutrition")
        diet = profile.get("dietType", "your diet")
        return {
            "reply": f"**{found_meal}** was carefully selected for you because it aligns perfectly with your **{goal.replace('_',' ').title()}** goal and **{diet.title()}** preferences. It contains the right balance of proteins and nutrients to keep you energized! 🥦"
        }

    if intent == "update_profile":
        parts = [f"**{k}** → {v}" for k, v in data.items()]
        action_payload = json.dumps({"type": "UPDATE_PROFILE", "updates": data})
        return {
            "reply": f"You want to update: {', '.join(parts)}. Is that correct?",
            "quickReplies": [
                {"label": "Yes", "value": f"__CONFIRM_ACTION__|{action_payload}"},
                {"label": "No", "value": "no"}
            ]
        }

    if intent == "invalid_option":
        lines = []
        qr = []
        for field, info in data.items():
            lines.append(f"Sorry, **\"{info['requested']}\"** is not available. Try one of these:")
            for val, label in info["valid"].items():
                qr.append({"label": f"{label}", "value": f"set {field} to {val}"})
        return {"reply": "\n".join(lines), "quickReplies": qr}

    if intent == "swap_meal":
        mt = data["mealTime"]
        day = data["dayIndex"]
        profile = ctx.get("profile", {})
        plan_summary = (ctx or {}).get("planSummary")
        current_meal_id = ""
        if plan_summary and len(plan_summary) > day:
            meal_data = plan_summary[day].get("meals", {}).get(mt, {})
            if isinstance(meal_data, dict):
                current_meal_id = meal_data.get("id", "")
                
        target_macros = _get_target_macros(ctx, profile, mt)
        allowed_ids = []
        pool_ids = (ctx or {}).get("selectedPoolIds", {})
        if isinstance(pool_ids, dict): allowed_ids = pool_ids.get(mt, [])

        options = _get_real_swap_options(profile, mt, current_meal_id, allowed_meal_ids=allowed_ids, top_n=5, target_macros=target_macros)
        qr = []
        lines = [f"Here are swap options for **Day {day+1} {mt}** 🔄:"]
        for i, opt in enumerate(options, 1):
            meal_obj = opt.get("meal", {})
            name = meal_obj.get("meal_name") or opt.get("mealId") or "Unknown"
            mid = opt.get("mealId") or ""
            macros = meal_obj.get("macros") or meal_obj.get("_macros") or {}
            kcal = f" ({int(macros.get('caloriesKcal', 0))} kcal)" if macros.get('caloriesKcal') else ""
            lines.append(f"  {i}. {name}{kcal}")
            qr.append({"label": f"🍽️ {name}", "value": f"__SWAP_APPLY__|{day}|{mt}|{mid}|{name}"})
        if not qr: return {"reply": f"No swap options found for {mt}. Try selecting more meals in step 2 first!"}
        return {"reply": "\n".join(lines), "quickReplies": qr}

    if intent == "allergy":
        allergen = data["allergen"]
        action_payload = json.dumps({"type": "REMOVE_ALLERGEN", "allergen": allergen})
        return {
            "reply": f"It looks like you want to add **{allergen}** to your allergies. Is that correct?",
            "quickReplies": [
                {"label": "Yes", "value": f"__CONFIRM_ACTION__|{action_payload}"},
                {"label": "No", "value": "no"}
            ]
        }
    return None

def process_chat_message(message: str, history: list, agent_name: str, context: dict) -> dict:
    prefs = load_preferences()
    prefs = _extract_preferences(message, prefs)
    save_preferences(prefs)
    ctx = context or {}

    # 1. Handle confirmed shortcuts
    if message.startswith("__SWAP_APPLY__"):
        parts = message.split("|")
        if len(parts) >= 5:
            return {
                "reply": f"Swapping to **{parts[4]}**! 🔄",
                "action": {"type": "APPLY_SWAP", "dayIndex": int(parts[1]), "mealTime": parts[2], "mealId": parts[3], "mealName": parts[4]},
                "preferences": prefs,
            }
    if message.startswith("__CONFIRM_ACTION__|"):
        json_str = message.split("|", 1)[1]
        try:
            action_dict = json.loads(json_str)
            action_type = action_dict.get("type", "")
            reply_msg = "Done! ✅"
            if action_type == "SET_VIEW":
                reply_msg = f"Navigated! 📍"
            elif action_type == "UPDATE_PROFILE":
                reply_msg = f"Profile updated! ✏️"
            elif action_type == "OPEN_SWAP":
                reply_msg = f"Opening swap menu... 🔄"
            elif action_type == "REMOVE_ALLERGEN":
                reply_msg = f"Noted! 🚫 Removed affected meals."
            return {"reply": reply_msg, "action": action_dict, "preferences": prefs}
        except Exception:
            pass

    # 2. Intent parsing
    intent, data, _ = _detect_intent(message, ctx)
    if intent:
        result = _build_intent_response(intent, data, ctx, prefs, agent_name)
        if result:
            return {
                "reply": result.get("reply", ""),
                "quickReplies": result.get("quickReplies"),
                "action": result.get("action"),
                "preferences": prefs,
            }

    # 3. LLM Completion fallback
    profile = ctx.get("profile", {})
    cuisine = profile.get("cuisineType") or "north_indian"
    relevant = _search_meals(message, cuisine, top_k=5)
    system = SYSTEM_PROMPT.format(
        agent_name=agent_name,
        likes=", ".join(prefs["likes"]) or "None",
        dislikes=", ".join(prefs["dislikes"]) or "None",
        allergies=", ".join(prefs["allergies"]) or "None",
        rag_context=_format_meal_context(relevant),
        profile_summary=f"Age:{profile.get('age','?')}, Goal:{profile.get('goal','?')}, Diet:{profile.get('dietType','?')}, Cuisine:{profile.get('cuisineType','?')}",
        plan_status="Yes" if ctx.get("isPlanGenerated") else "No",
        plan_summary=_format_plan_summary(ctx),
        valid_goals=", ".join(f"{v}({k})" for k,v in VALID_GOALS.items()),
        valid_diet=", ".join(f"{v}({k})" for k,v in VALID_DIET.items()),
        valid_activity=", ".join(f"{v}({k})" for k,v in VALID_ACTIVITY.items()),
        valid_cuisines=", ".join(f"{v}({k})" for k,v in VALID_CUISINES.items()),
    )
    messages = [{"role": "system", "content": system}]
    for msg in history[-10:]:
        role = "user" if msg.role == "user" else "assistant"
        messages.append({"role": role, "content": msg.text})
    messages.append({"role": "user", "content": message})

    reply = _call_ollama(messages)
    if not reply:
        reply = f"I can help with: meal swaps, profile changes, navigation, nutrition! Try: 'swap my breakfast', 'weight to 70', 'page 2' 🌿"

    reply_text = reply or ""
    action = None
    quick_replies = None

    am = re.search(r"<ACTION>([\s\S]*?)</ACTION>", reply_text)
    action_payload = ""
    if am:
        try:
            json.loads(am.group(1))
            action_payload = f"__CONFIRM_ACTION__|{am.group(1)}"
        except json.JSONDecodeError as e:
            raise AIServiceException("AI agent returned malformed JSON action block") from e

    qrm = re.search(r"<QUICK_REPLIES>([\s\S]*?)</QUICK_REPLIES>", reply_text, flags=re.IGNORECASE)
    is_verifying = qrm or re.search(r"\b(correct|right|proceed|want to)\b\s*\?", reply_text, re.IGNORECASE)

    if is_verifying:
        reply_text = re.sub(r"<ACTION>[\s\S]*?</ACTION>", "", reply_text).strip()
        if qrm:
            try:
                labels = qrm.group(1).split("|")
                quick_replies = []
                for label in labels:
                    l = label.strip()
                    if l.lower() == "yes" and action_payload:
                        quick_replies.append({"label": l, "value": action_payload})
                    else:
                        quick_replies.append({"label": l, "value": l.lower()})
                reply_text = re.sub(r"<QUICK_REPLIES>[\s\S]*?</QUICK_REPLIES>", "", reply_text, flags=re.IGNORECASE).strip()
            except Exception:
                pass
        else:
            quick_replies = [
                {"label": "Yes", "value": action_payload if action_payload else "yes"}, 
                {"label": "No", "value": "no"}
            ]
    else:
        if am:
            try:
                action = json.loads(am.group(1))
                reply_text = re.sub(r"<ACTION>[\s\S]*?</ACTION>", "", reply_text).strip()
            except json.JSONDecodeError as e:
                raise AIServiceException("AI agent returned malformed JSON action block") from e

    return {
        "reply": reply_text,
        "preferences": prefs,
        "action": action,
        "quickReplies": quick_replies
    }
