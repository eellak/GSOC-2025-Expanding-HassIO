import os
import sys
import time
import asyncio
from smauto.language import build_model
from smauto.lib.rest_runtime import start_rest_runtime, stop_rest_runtime, get_rest_value

async def main(model_path: str, duration: int = 30, interval: int = 5, threshold: float = 28.0):
    model = build_model(model_path)
    await start_rest_runtime(model)
    try:
        fan_on = False
        t0 = time.time()
        while time.time() - t0 < duration:
            for s in getattr(model, "restSources", []):
                fields = [m.name for m in getattr(s, "mappings", [])]
                values = {f: get_rest_value(s.name, f) for f in fields}
                print(f"[{s.name}] {values}")
                temp = values.get("temp")
                if temp is not None and temp > threshold and not fan_on:
                    fan_on = True
                    print(f"[Automation] HighTempFan TRIGGER: temp={temp} > {threshold} → fan.on=true")
                elif temp is not None and fan_on and temp <= threshold:
                    fan_on = False
                    print(f"[Automation] HighTempFan RESET: temp={temp} ≤ {threshold} → fan.on=false")
            await asyncio.sleep(interval)
    finally:
        await stop_rest_runtime()

if __name__ == "__main__":
    model_path = sys.argv[1] if len(sys.argv) > 1 else "examples/weather_rest.smauto"
    threshold = float(sys.argv[2]) if len(sys.argv) > 2 else float(os.getenv("SMAUTO_TEMP_THRESHOLD", "28"))
    asyncio.run(main(model_path, threshold=threshold))

