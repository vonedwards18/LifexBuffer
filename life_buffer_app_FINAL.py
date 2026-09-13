"""
LIFE BUFFER - Streamlit Web App v0.1
A visual front-end for the LifeBufferEngine prototype.
"""

import streamlit as st
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time as dtime
from typing import List, Optional


# ---------------------------------------------------------------------------
# DATA MODELS
# ---------------------------------------------------------------------------

@dataclass
class Event:
    title: str
    mode: str
    start_time: datetime
    location: str
    drive_minutes: int
    checklist: List[str] = field(default_factory=list)

@dataclass
class UserContext:
    current_time: datetime
    battery_pct: int
    weather: str
    weekly_budget_remaining: float
    energy_level: str
    last_meal_hours_ago: float
    home_essentials: List[str] = field(default_factory=lambda: ["keys", "wallet", "phone", "charger"])

@dataclass
class Recommendation:
    headline: str
    leave_by: Optional[str]
    checklist: List[str]
    warnings: List[str]
    money_note: Optional[str]
    energy_note: Optional[str]
    suggested_message: Optional[str] = None


MODE_CHECKLISTS = {
    "session": ["laptop/session drive", "audio interface", "headphones", "session notes",
                "charger", "invoice template"],
    "gym": ["gym clothes", "water bottle", "headphones", "gym shoes"],
    "travel": ["ID/passport", "charger", "packed bag", "boarding pass/tickets"],
    "social": ["wallet", "phone", "charger"],
    "errand": ["reusable bags", "shopping list", "wallet"],
}

WEATHER_ADDONS = {
    "rain": ["umbrella", "waterproof bag cover"],
    "storm": ["umbrella", "leave extra early (storm delays likely)"],
    "cold": ["jacket"],
    "clear": [],
}

MODE_MESSAGE_TEMPLATES = {
    "session": "Confirming our session at {time}. Please bring consolidated WAV stems at 48kHz if applicable.",
    "social": "On my way, should be there by {time}.",
    "travel": None,
    "gym": None,
    "errand": None,
}


# ---------------------------------------------------------------------------
# CORE ENGINE
# ---------------------------------------------------------------------------

class LifeBufferEngine:
    def __init__(self, context: UserContext):
        self.context = context

    def minutes_until(self, event: Event) -> int:
        delta = event.start_time - self.context.current_time
        return int(delta.total_seconds() // 60)

    def required_leave_time(self, event: Event) -> datetime:
        buffer_min = 10
        return event.start_time - timedelta(minutes=event.drive_minutes + buffer_min)

    def build_checklist(self, event: Event) -> List[str]:
        base = list(self.context.home_essentials)
        base += MODE_CHECKLISTS.get(event.mode, [])
        base += WEATHER_ADDONS.get(self.context.weather, [])
        base += event.checklist
        seen = set()
        result = []
        for item in base:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    def money_check(self, estimated_spend: float) -> Optional[str]:
        remaining = self.context.weekly_budget_remaining
        if estimated_spend <= 0:
            return None
        after = remaining - estimated_spend
        if after < 0:
            return (f"Warning: this would put you ${abs(after):.2f} over your "
                     f"weekly discretionary budget (${remaining:.2f} remaining).")
        elif after < remaining * 0.15:
            return (f"Caution: this spend leaves only ${after:.2f} of your "
                     f"weekly budget remaining.")
        return f"Safe to spend. ${after:.2f} would remain this week."

    def energy_check(self, event: Event) -> Optional[str]:
        notes = []
        if self.context.energy_level == "low" and event.mode == "gym":
            notes.append("Energy is low — consider a shortened 20-25 min session instead of a full workout.")
        if self.context.last_meal_hours_ago >= 5:
            notes.append(f"You haven't eaten in {self.context.last_meal_hours_ago:.0f}+ hours — grab something quick before heading out.")
        if self.context.battery_pct < 25:
            notes.append(f"Phone battery at {self.context.battery_pct}% — bring your charger.")
        return "; ".join(notes) if notes else None

    def suggested_message(self, event: Event) -> Optional[str]:
        template = MODE_MESSAGE_TEMPLATES.get(event.mode)
        if template:
            return template.format(time=event.start_time.strftime("%I:%M %p").lstrip("0"))
        return None

    def evaluate(self, event: Event, estimated_spend: float = 0.0) -> Recommendation:
        mins_left = self.minutes_until(event)
        leave_time = self.required_leave_time(event)
        checklist = self.build_checklist(event)
        money_note = self.money_check(estimated_spend)
        energy_note = self.energy_check(event)
        msg = self.suggested_message(event)

        warnings = []
        buffer_minutes = int((leave_time - self.context.current_time).total_seconds() // 60)
        if buffer_minutes < 0:
            warnings.append("You are already behind schedule for this event.")
        elif buffer_minutes < 15:
            warnings.append(f"Tight window — only {buffer_minutes} min before you must leave.")

        if self.context.weather in ("rain", "storm"):
            warnings.append(f"Weather is {self.context.weather} — expect slower travel.")

        if mins_left <= 0:
            headline = f"{event.title} is starting now."
        else:
            headline = f"Leave by {leave_time.strftime('%I:%M %p').lstrip('0')} for {event.title} ({event.location})."

        return Recommendation(
            headline=headline,
            leave_by=leave_time.strftime("%I:%M %p").lstrip("0"),
            checklist=checklist,
            warnings=warnings,
            money_note=money_note,
            energy_note=energy_note,
            suggested_message=msg,
        )


# ---------------------------------------------------------------------------
# STREAMLIT UI
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Life Buffer", page_icon="🧭", layout="centered")

st.title("🧭 Life Buffer")
st.caption("A context-aware readiness engine — turns your schedule, weather, energy, and budget into one clear next move.")

st.divider()

st.sidebar.header("Your Current Context")

sidebar_date = st.sidebar.date_input("Today's date", value=date(2026, 9, 13))
sidebar_time = st.sidebar.time_input("Current time", value=dtime(17, 28))
current_dt = datetime.combine(sidebar_date, sidebar_time)

battery_pct = st.sidebar.slider("Phone battery (%)", 0, 100, 18)
weather = st.sidebar.selectbox("Weather", ["clear", "rain", "storm", "cold"], index=1)
budget_remaining = st.sidebar.number_input("Weekly budget remaining ($)", value=52.00, step=5.0)
energy_level = st.sidebar.selectbox("Energy level", ["low", "medium", "high"], index=1)
last_meal_hours = st.sidebar.slider("Hours since last meal", 0.0, 12.0, 5.5, step=0.5)

context = UserContext(
    current_time=current_dt,
    battery_pct=battery_pct,
    weather=weather,
    weekly_budget_remaining=budget_remaining,
    energy_level=energy_level,
    last_meal_hours_ago=last_meal_hours,
)

engine = LifeBufferEngine(context)

st.subheader("Your Next Event")

col1, col2 = st.columns(2)
with col1:
    event_title = st.text_input("Event title", value="Mixing session with client")
    mode = st.selectbox("Mode", list(MODE_CHECKLISTS.keys()), index=0)
    location = st.text_input("Location", value="The High Caliber Suite")
with col2:
    event_date = st.date_input("Event date", value=date(2026, 9, 13), key="event_date")
    event_time = st.time_input("Event time", value=dtime(18, 30), key="event_time")
    drive_minutes = st.number_input("Drive time (minutes)", value=20, step=5)

extra_items_raw = st.text_input("Extra checklist items (comma-separated)", value="external hard drive, session template loaded")
extra_items = [i.strip() for i in extra_items_raw.split(",") if i.strip()]

estimated_spend = st.number_input("Estimated spend for this trip ($)", value=18.00, step=1.0)

event = Event(
    title=event_title,
    mode=mode,
    start_time=datetime.combine(event_date, event_time),
    location=location,
    drive_minutes=int(drive_minutes),
    checklist=extra_items,
)

st.divider()

if st.button("🔍 Generate Recommendation", type="primary", use_container_width=True):
    rec = engine.evaluate(event, estimated_spend=estimated_spend)

    st.markdown(f"### {rec.headline}")

    if rec.warnings:
        for w in rec.warnings:
            st.warning(w)

    st.markdown(f"**Leave by:** {rec.leave_by}")

    st.markdown("**Checklist:**")
    for item in rec.checklist:
        st.checkbox(item, key=f"chk_{item}")

    if rec.money_note:
        st.info(f"💰 {rec.money_note}")

    if rec.energy_note:
        st.info(f"⚡ {rec.energy_note}")

    if rec.suggested_message:
        st.markdown("**Suggested message to send:**")
        st.code(rec.suggested_message, language=None)

st.divider()
st.caption("Prototype v0.1 — logic layer only. Connect a real calendar, weather API, and HealthKit data to make this fully automatic.")
