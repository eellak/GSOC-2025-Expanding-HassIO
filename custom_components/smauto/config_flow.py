"""Config flow for SmAuto integration."""
import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_KEY, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default="http://localhost:8080"): str,
        vol.Required(CONF_API_KEY, default="API_KEY"): str,
    }
)

class InvalidAuth(Exception):
    """Raised when authentication fails."""

class SmAutoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for SmAuto."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the user step of config flow."""
        errors = {}
        if user_input:
            headers = {"X-API-Key": user_input[CONF_API_KEY]}
            session = async_get_clientsession(self.hass)
            api_url = f"{user_input[CONF_URL]}/generate/autos"

            try:
                # Try basic connection/auth test; 200 or 422 are both fine here
                async with session.post(api_url, headers=headers, timeout=10) as resp:
                    if resp.status not in (200, 422):
                        if resp.status in (401, 403):
                            raise InvalidAuth
                        raise ConnectionError(f"Status: {resp.status}")

                return self.async_create_entry(title="SmAuto Server", data=user_input)

            except InvalidAuth:
                errors["base"] = "invalid_auth"
                _LOGGER.warning("API key failed during config flow.")
            except ConnectionError as e:
                errors["base"] = "cannot_connect"
                _LOGGER.warning("Failed to connect to SmAuto: %s", e)
            except Exception:  # Catch unexpected exceptions with logging
                errors["base"] = "unknown"
                _LOGGER.exception("Unknown error during SmAuto config flow")

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
