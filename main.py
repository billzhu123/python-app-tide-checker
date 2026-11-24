#!/usr/bin/env python3
"""
🌊 NOAA Tide Checker
Fetches tide predictions from the NOAA Tides and Currents API.
Default station: Pillar Point Harbor / Half Moon Bay, CA (9414131)
"""

import sys
import urllib.request
import urllib.parse
import json
from datetime import date, datetime

# ─── Constants ────────────────────────────────────────────────────────────────
DEFAULT_STATION_ID   = "9414131"
DEFAULT_STATION_NAME = "Pillar Point Harbor / Half Moon Bay, CA"
NOAA_API_BASE        = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

# ─── Helpers ──────────────────────────────────────────────────────────────────

def fetch_tide_predictions(station_id: str, target_date: date) -> list[dict]:
    """Call the NOAA API and return a list of High/Low tide dicts."""
    date_str = target_date.strftime("%Y%m%d")
    params = {
        "begin_date": date_str,
        "end_date":   date_str,
        "station":    station_id,
        "product":    "predictions",
        "datum":      "MLLW",
        "time_zone":  "lst_ldt",   # local standard / local daylight time
        "interval":   "hilo",      # High / Low only
        "units":      "english",   # feet
        "application":"tide_checker",
        "format":     "json",
    }
    url = NOAA_API_BASE + "?" + urllib.parse.urlencode(params)

    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"\n❌  Network error: {exc}")
        sys.exit(1)

    if "error" in data:
        msg = data["error"].get("message", "Unknown NOAA error")
        print(f"\n❌  NOAA API error: {msg}")
        sys.exit(1)

    return data.get("predictions", [])


def parse_predictions(raw: list[dict]) -> list[dict]:
    """Convert raw NOAA predictions to cleaner dicts."""
    tides = []
    for item in raw:
        t = datetime.strptime(item["t"], "%Y-%m-%d %H:%M")
        tides.append({
            "datetime": t,
            "time_str": t.strftime("%I:%M %p"),   # e.g. 06:34 AM
            "type":     item["type"],              # "H" or "L"
            "height":   float(item["v"]),          # feet
        })
    return tides


def tide_label(tide_type: str) -> str:
    return "🔼 High Tide" if tide_type == "H" else "🔽 Low  Tide"


def build_summary(tides: list[dict], target_date: date) -> str:
    """Generate a short human-friendly summary for the day."""
    if not tides:
        return "No tide data available for this date."

    highs = [t for t in tides if t["type"] == "H"]
    lows  = [t for t in tides if t["type"] == "L"]

    lines = []

    # Number of cycles
    num_cycles = max(len(highs), len(lows))
    lines.append(f"📊  {len(tides)} tide event(s) today "
                 f"({len(highs)} high, {len(lows)} low).")

    # Highest / lowest
    if highs:
        h = max(highs, key=lambda x: x["height"])
        lines.append(f"🌊  Highest tide: {h['height']:.2f} ft at {h['time_str']}.")
    if lows:
        l = min(lows, key=lambda x: x["height"])
        lines.append(f"⬇️   Lowest tide:  {l['height']:.2f} ft at {l['time_str']}.")

        # Best low-tide window (±2 hrs around the lowest low)
        low_dt = l["datetime"]
        window_start = low_dt.replace(hour=max(0,  low_dt.hour - 2),
                                      minute=low_dt.minute)
        window_end   = low_dt.replace(hour=min(23, low_dt.hour + 2),
                                      minute=low_dt.minute)
        lines.append(
            f"🦀  Best low-tide window: "
            f"{window_start.strftime('%I:%M %p')} – {window_end.strftime('%I:%M %p')} "
            f"(great for tidepooling & clamming!)"
        )

    # Tidal range
    if highs and lows:
        h_max = max(t["height"] for t in highs)
        l_min = min(t["height"] for t in lows)
        tidal_range = h_max - l_min
        if tidal_range >= 4.5:
            character = "large"
        elif tidal_range >= 2.5:
            character = "moderate"
        else:
            character = "small"
        lines.append(
            f"📐  Tidal range: {tidal_range:.2f} ft ({character} range day)."
        )

    return "\n   ".join(lines)


# ─── Prompts ──────────────────────────────────────────────────────────────────

def prompt_date() -> date:
    """Ask the user for a date; default to today."""
    today_str = date.today().strftime("%Y-%m-%d")
    raw = input(f"\n📅  Enter date (YYYY-MM-DD) or press Enter for today [{today_str}]: ").strip()
    if not raw:
        return date.today()
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        print("❌  Invalid date format. Please use YYYY-MM-DD.")
        sys.exit(1)


def prompt_station() -> tuple[str, str]:
    """Ask for an optional station ID; default to Pillar Point Harbor."""
    print(f"\n🚢  Default station: {DEFAULT_STATION_NAME} (ID: {DEFAULT_STATION_ID})")
    raw = input("   Enter a different NOAA station ID, or press Enter to use the default: ").strip()
    if not raw:
        return DEFAULT_STATION_ID, DEFAULT_STATION_NAME
    return raw, f"Station {raw}"


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("          🌊  NOAA Tide Checker  🌊")
    print("=" * 60)

    target_date          = prompt_date()
    station_id, station_name = prompt_station()

    print(f"\n⏳  Fetching tide predictions for {target_date.strftime('%A, %B %d, %Y')} …")

    raw    = fetch_tide_predictions(station_id, target_date)
    tides  = parse_predictions(raw)

    if not tides:
        print("\n⚠️   No predictions returned. The station may not have data for this date.")
        sys.exit(0)

    # ── Display ──────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print(f"  📍 {station_name}")
    print(f"  📅 {target_date.strftime('%A, %B %d, %Y')}")
    print("=" * 60)
    print(f"  {'TIME':<12}  {'TYPE':<14}  {'HEIGHT':>9}")
    print(f"  {'-'*12}  {'-'*14}  {'-'*9}")

    for t in tides:
        label  = tide_label(t["type"])
        height = f"{t['height']:+.2f} ft"
        print(f"  {t['time_str']:<12}  {label:<14}  {height:>9}")

    print("=" * 60)
    print("\n📋  Summary:")
    print(f"   {build_summary(tides, target_date)}")
    print()


if __name__ == "__main__":
    main()
