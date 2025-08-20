"""SmAuto Home Assistant Integration."""
import asyncio
import json
import logging
import re
import subprocess
import sys
import tempfile

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

RUNNING_PROCESSES = {}


async def _log_process_output(name, proc):
    """Log the stdout of a subprocess."""
    while True:
        if proc.stdout:
            line = await asyncio.to_thread(proc.stdout.readline)
            if line:
                _LOGGER.info("[SmAuto %s] %s", name, line.decode().strip())
            else:
                break
        await asyncio.sleep(0.1)
    _LOGGER.info("Done logging for '%s'", name)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the SmAuto integration from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    async def run_model(call: ServiceCall) -> None:
        """Handle the service call to run a SmAuto model."""
        fname = call.data.get('filename')
        if not fname:
            _LOGGER.error("No filename for 'run_model'")
            return

        model_txt = ''
        try:
            path = hass.config.path(fname)
            with open(path, encoding="utf-8") as f:
                model_txt = f.read()
        except FileNotFoundError as ex:
            _LOGGER.error("File not found: %s", ex)
            return
        except OSError as ex:
            _LOGGER.error("OS error reading file: %s", ex)
            return
        except Exception as ex:  # noqa: BLE001
            _LOGGER.error("Unexpected error reading model: %s", ex)
            return

        match = re.search(r"Metadata\s*\{\s*name:\s*(\w+)", model_txt, re.DOTALL)
        process_name = call.data.get("process_name") or (match.group(1) if match else "sm_auto_proc")

        if process_name in RUNNING_PROCESSES:
            _LOGGER.error("Process '%s' running already", process_name)
            return

        server_cfg = hass.data[DOMAIN][entry.entry_id]
        url = server_cfg[CONF_URL]
        api_key = server_cfg.get(CONF_API_KEY)
        headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
        session = async_get_clientsession(hass)

        try:
            resp = await session.post(
                f"{url}/generate/autos",
                data=json.dumps({"model": model_txt}),
                headers=headers,
                timeout=20
            )
            if resp.status != 200:
                _LOGGER.error("SmAuto server error %s: %s", resp.status, await resp.text())
                return
            resp_json = await resp.json()
            code = resp_json.get("code")
            if not code:
                _LOGGER.error("No 'code' in response: %s", resp_json)
                return

            # Patch main block so it doesn't quit instantly
            patched = re.sub(
                r"if __name__ == '__main__':.*",
                """if __name__ == '__main__':
    executor = Executor()
    executor.start_entities()
    executor.start_automations()
    import time
    while True:
        time.sleep(10)
""",
                code,
                flags=re.DOTALL
            )
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".py", delete=False, encoding="utf-8") as tmp:
                tmp.write(patched)
                script_path = tmp.name

            proc = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            RUNNING_PROCESSES[process_name] = proc

            log_task = hass.async_create_task(_log_process_output(process_name, proc))
            hass.data[DOMAIN][f"log_task_{process_name}"] = log_task
            _LOGGER.info("Started '%s' (PID %s)", process_name, proc.pid)

        except Exception as exc:  # noqa: BLE001  # We want to log all unexpected issues
            _LOGGER.error("Error running SmAuto model: %s", exc)

    async def stop_model(call: ServiceCall) -> None:
        """Handle the service call to stop a running SmAuto model."""
        pname = call.data.get("process_name")
        if not pname:
            _LOGGER.error("No process name for stop_model")
            return
        proc = RUNNING_PROCESSES.pop(pname, None)
        if proc:
            proc.terminate()
            log_task = hass.data[DOMAIN].pop(f"log_task_{pname}", None)
            if log_task:
                log_task.cancel()
            _LOGGER.info("Terminated '%s' (PID %s)", pname, proc.pid)
        else:
            _LOGGER.warning("Process '%s' not found", pname)

    hass.services.async_register(DOMAIN, "run_model", run_model)
    hass.services.async_register(DOMAIN, "stop_model", stop_model)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the SmAuto config entry and stop any running processes."""
    for pname, proc in list(RUNNING_PROCESSES.items()):
        _LOGGER.info("Unloading: stopping '%s'", pname)
        proc.terminate()
        log_task = hass.data[DOMAIN].pop(f"log_task_{pname}", None)
        if log_task:
            log_task.cancel()
    hass.services.async_remove(DOMAIN, "run_model")
    hass.services.async_remove(DOMAIN, "stop_model")
    hass.data.pop(DOMAIN, None)
    return True
