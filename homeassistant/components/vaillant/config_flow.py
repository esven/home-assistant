"""Config flow for the Velbus platform."""

from homeassistant import config_entries

from .const import DOMAIN


@config_entries.HANDLERS.register(DOMAIN)
class VaillantConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    def __init__(self) -> None:
        """Initialize the vaillant config flow."""
        pass

    async def async_step_discovery(self, info):
        """Run vaillant discovered."""
        pass
