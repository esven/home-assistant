"""Common entities."""
from abc import ABC, abstractmethod
import logging
from typing import Optional

from pymultimatic.model import BoilerStatus

from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class VaillantEntity(Entity, ABC):
    """Define base class for vaillant."""

    def __init__(self, domain, device_class, comp_id, comp_name, class_in_id=True):
        """Initialize entity."""
        self._device_class = device_class
        if device_class and class_in_id:
            id_format = domain + "." + DOMAIN + "_{}_" + device_class
        else:
            id_format = domain + "." + DOMAIN + "_{}"

        self.entity_id = id_format.format(slugify(comp_id)).lower()
        self._vaillant_name = comp_name
        self.hub = None

    @property
    def name(self) -> Optional[str]:
        """Return the name of the entity."""
        return self._vaillant_name

    async def async_update(self):
        """Update the entity."""
        _LOGGER.debug("Time to update %s", self.entity_id)
        if not self.hub:
            self.hub = self.hass.data[DOMAIN].api
        self.hub.update_system()

        await self.vaillant_update()

    @property
    def device_class(self):
        """Return the class of this device, from component DEVICE_CLASSES."""
        return self._device_class

    @abstractmethod
    async def vaillant_update(self):
        """Update specific for vaillant."""
        pass

    @property
    def listening(self):
        """Return whether this entity is listening for system changes or not.

        System changes are quick mode or holiday mode.
        """
        return False

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        self.hass.data[DOMAIN].entities.append(self)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self.hass.data[DOMAIN].entities.remove(self)


class VaillantBoilerDevice(Entity):
    """Base class for boiler device."""

    def __init__(self, boiler_status: BoilerStatus) -> None:
        """Initialize device."""
        self.boiler_status = boiler_status

    @property
    def device_info(self):
        """Return device specific attributes."""
        if self.boiler_status is not None:
            return {
                "identifiers": {(DOMAIN, slugify(self.boiler_status.device_name))},
                "name": self.boiler_status.device_name,
                "manufacturer": "Vaillant",
                "model": self.boiler_status.device_name,
            }
        return None
