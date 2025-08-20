import sys
import time
import asyncio
from smauto.language import build_model
from smauto.lib.rest_runtime import start_rest_runtime, stop_rest_runtime, get_rest_value


async def main(model_path: str, duration: int = 20, interval: int = 5):
    model = build_model(model_path)
    await start_rest_runtime(model)
    try:
        t0 = time.time()
        while time.time() - t0 < duration:
            for s in getattr(model, "restSources", []):
                fields = [m.name for m in getattr(s, "mappings", [])]
                values = {f: get_rest_value(s.name, f) for f in fields}
                print(f"[{s.name}] {values}")
            await asyncio.sleep(interval)
    finally:
        await stop_rest_runtime()


if __name__ == "__main__":
    model_path = sys.argv[1] if len(sys.argv) > 1 else "examples/weather_rest.smauto"
    asyncio.run(main(model_path))
