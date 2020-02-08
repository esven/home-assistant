"""Interfaces with Vaillant sensors."""
from abc import ABC
import logging

from pymultimatic.model import BoilerInfo

from homeassistant.components.sensor import (
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DOMAIN,
)
from homeassistant.const import TEMP_CELSIUS

from . import DOMAIN as VAILLANT, HUB, VaillantEntity

PRESSURE_BAR = "bar"

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Vaillant sensor platform."""
    pass
    # sensors = []
    # hub = hass.data[VAILLANT][HUB]
    #
    # if hub.system:
    #     if hub.system.outdoor_temperature:
    #         sensors.append(
    #             OutdoorTemperatureSensor(hub.system.outdoor_temperature))
    #
    #     if hub.system.boiler_status:
    #         sensors.append(BoilerTemperatureSensor(hub.system.boiler_status))
    #         sensors.append(BoilerWaterPressureSensor(hub.system.boiler_status))
    #
    # _LOGGER.info("Adding %s sensor entities", len(sensors))
    #
    # async_add_entities(sensors)
    # return True


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Vaillant sensor platform."""
    sensors = []
    hub = hass.data[VAILLANT][HUB]

    if hub.system:
        if hub.system.outdoor_temperature:
            sensors.append(OutdoorTemperatureSensor(hub.system.outdoor_temperature))

        if hub.system.boiler_info:
            sensors.append(BoilerTemperatureSensor(hub.system.boiler_info))
            sensors.append(BoilerWaterPressureSensor(hub.system.boiler_info))

    _LOGGER.info("Adding %s sensor entities", len(sensors))

    async_add_entities(sensors)
    return True


class BaseVaillantTemperatureSensor(VaillantEntity, ABC):
    """Base temperature sensor class."""

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return TEMP_CELSIUS


class OutdoorTemperatureSensor(BaseVaillantTemperatureSensor):
    """Outdoor temperature sensor."""

    def __init__(self, outdoor_temp):
        """Initialize entity."""
        super().__init__(DOMAIN, DEVICE_CLASS_TEMPERATURE, "outdoor", "Outdoor")
        self._outdoor_temp = outdoor_temp

    @property
    def state(self):
        """Return the state of the entity."""
        return self._outdoor_temp

    @property
    def available(self):
        """Return True if entity is available."""
        return self._outdoor_temp is not None

    async def vaillant_update(self):
        """Update specific for vaillant."""
        _LOGGER.debug(
            "New / old temperature: %s / %s",
            self.hub.system.outdoor_temperature,
            self._outdoor_temp,
        )
        self._outdoor_temp = self.hub.system.outdoor_temperature


class BoilerWaterPressureSensor(VaillantEntity):
    """Water pressure inside the boiler."""

    def __init__(self, boiler_info: BoilerInfo):
        """Initialize entity."""
        VaillantEntity.__init__(self, DOMAIN, DEVICE_CLASS_PRESSURE, "boiler", "boiler")
        self.boiler_info = boiler_info

    @property
    def state(self):
        """Return the state of the entity."""
        return self.boiler_info.water_pressure

    @property
    def available(self):
        """Return True if entity is available."""
        return self.boiler_info is not None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return PRESSURE_BAR

    async def vaillant_update(self):
        """Update specific for vaillant."""
        self.boiler_info = self.hub.system.boiler_info


class BoilerTemperatureSensor(BaseVaillantTemperatureSensor):
    """Water temperature inside the boiler."""

    def __init__(self, boiler_info: BoilerInfo):
        """Initialize entity."""
        BaseVaillantTemperatureSensor.__init__(
            self, DOMAIN, DEVICE_CLASS_TEMPERATURE, "boiler", "boiler"
        )
        self.boiler_info = boiler_info

    @property
    def state(self):
        """Return the state of the entity."""
        return self.boiler_info.current_temperature

    @property
    def available(self):
        """Return True if entity is available."""
        return self.boiler_info is not None

    async def vaillant_update(self):
        """Update specific for vaillant."""
        self.boiler_info = self.hub.system.boiler_info
