# -*- coding: utf-8 -*-
"""Phase 5 Physis verification: 1-year (360 days = 8640 ticks) climate check."""
import sys
sys.path.insert(0, '.')
from physis import ClimateEngine, NovaPlanet

planet = NovaPlanet()
engine = ClimateEngine()

print("=== 1-Year Climate Verification (360 days) ===\n")

# Sample every 30 days at noon
print(f"{'Day':>4s} {'Season':>8s} | {'Claude':>8s} {'Codex':>8s} {'Gemini':>8s} | "
      f"{'C-rain':>6s} {'X-rain':>6s} {'G-rain':>6s} | "
      f"{'C-tag':>20s}")
print("-" * 110)

for day in range(0, 360, 15):
    weather = engine.tick(day, 12)  # noon
    c = weather["claude"]
    x = weather["codex"]
    g = weather["gemini"]
    season = planet.season_name(day)
    print(f"{day:4d} {season:>8s} | "
          f"{c['temperature_c']:7.1f}C {x['temperature_c']:7.1f}C {g['temperature_c']:7.1f}C | "
          f"{c['precipitation_mm']:5.1f}mm {x['precipitation_mm']:5.1f}mm {g['precipitation_mm']:5.1f}mm | "
          f"{c['narrative_tag']:>20s}")

# Verify key properties
print("\n=== Verification Checks ===")

# 1. Claude winter should be coldest
winter_days = range(270, 360)
claude_winter_temps = [engine._compute_region_weather(engine.regions["claude"], d, 12)["temperature_c"] for d in winter_days]
claude_winter_avg = sum(claude_winter_temps) / len(claude_winter_temps)
print(f"[{'PASS' if claude_winter_avg < 0 else 'FAIL'}] Claude winter avg: {claude_winter_avg:.1f}C (should be < 0)")

# 2. Gemini should be warmest year-round
gemini_temps = [engine._compute_region_weather(engine.regions["gemini"], d, 12)["temperature_c"] for d in range(0, 360, 30)]
gemini_avg = sum(gemini_temps) / len(gemini_temps)
print(f"[{'PASS' if gemini_avg > 25 else 'FAIL'}] Gemini annual avg: {gemini_avg:.1f}C (should be > 25)")

# 3. Codex should have most rain
codex_rain = sum(engine._compute_region_weather(engine.regions["codex"], d, 12)["precipitation_mm"] for d in range(0, 360, 1))
claude_rain = sum(engine._compute_region_weather(engine.regions["claude"], d, 12)["precipitation_mm"] for d in range(0, 360, 1))
print(f"[{'PASS' if codex_rain > claude_rain else 'FAIL'}] Codex rain > Claude: {codex_rain:.0f}mm vs {claude_rain:.0f}mm")

# 4. Season names correct
print(f"[{'PASS' if planet.season_name(0)=='spring' else 'FAIL'}] Day 0 = {planet.season_name(0)}")
print(f"[{'PASS' if planet.season_name(90)=='summer' else 'FAIL'}] Day 90 = {planet.season_name(90)}")
print(f"[{'PASS' if planet.season_name(180)=='autumn' else 'FAIL'}] Day 180 = {planet.season_name(180)}")
print(f"[{'PASS' if planet.season_name(270)=='winter' else 'FAIL'}] Day 270 = {planet.season_name(270)}")

# 5. Day length varies by latitude
summer_dl_claude = planet.day_length_hours(45, 90)
summer_dl_gemini = planet.day_length_hours(-5, 90)
print(f"[{'PASS' if summer_dl_claude > summer_dl_gemini else 'FAIL'}] Summer day length: Claude({summer_dl_claude:.1f}h) > Gemini({summer_dl_gemini:.1f}h)")

# 6. Now test with MultiTickEngine
print("\n=== MultiTickEngine Integration ===")
from core.multi_tick_engine import MultiTickEngine
import time

mte = MultiTickEngine()
t0 = time.time()
log = mte.run(n_ticks=100, verbose=False)
dt = time.time() - t0
print(f"100 ticks in {dt:.1f}s ({dt/100*1000:.1f}ms/tick)")

# Check weather varies
weathers = [e.get("weather", {}).get("claude", {}).get("temperature_c", 0) for e in log[:24]]
temp_range = max(weathers) - min(weathers) if weathers else 0
print(f"[{'PASS' if temp_range > 3 else 'FAIL'}] Claude 24h temp range: {temp_range:.1f}C (diurnal > 3C)")
print(f"Season at tick 100: {log[-1].get('season', '?')}")
