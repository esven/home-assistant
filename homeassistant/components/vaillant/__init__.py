"""Vaillant component."""
from abc import ABC, abstractmethod
import logging
from typing import Optional

from pymultimatic.model import BoilerStatus
import voluptuous as vol

from homeassistant.const import (
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle, slugify

from .const import (
    CONF_QUICK_VETO_DURATION,
    CONF_SMARTPHONE_ID,
    DEFAULT_QUICK_VETO_DURATION,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SMART_PHONE_ID,
    DOMAIN,
    ENTITIES,
    HUB,
    MAX_QUICK_VETO_DURATION,
    MIN_QUICK_VETO_DURATION,
    MIN_SCAN_INTERVAL,
    PLATFORMS,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_USERNAME): cv.string,
                vol.Required(CONF_PASSWORD): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): (
                    vol.All(cv.time_period, vol.Clamp(min=MIN_SCAN_INTERVAL))
                ),
                vol.Optional(
                    CONF_SMARTPHONE_ID, default=DEFAULT_SMART_PHONE_ID
                ): cv.string,
                vol.Optional(
                    CONF_QUICK_VETO_DURATION, default=DEFAULT_QUICK_VETO_DURATION
                ): (
                    vol.All(
                        cv.positive_int,
                        vol.Clamp(
                            min=MIN_QUICK_VETO_DURATION, max=MAX_QUICK_VETO_DURATION
                        ),
                    )
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up vaillant component."""
    from .service import VaillantServiceHandler
    from .service import SERVICES

    hub = VaillantHub(hass, config[DOMAIN])

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][ENTITIES] = []
    hass.data[DOMAIN][HUB] = hub

    service_handler = VaillantServiceHandler(hub, hass)

    for platform in PLATFORMS:
        hass.async_create_task(
            discovery.async_load_platform(hass, platform, DOMAIN, {}, config)
        )

    for service in SERVICES:
        schema = SERVICES[service]["schema"]
        method = SERVICES[service]["method"]
        method = getattr(service_handler, method)
        hass.services.async_register(DOMAIN, service, method, schema=schema)

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, lambda event: hub.logout())

    _LOGGER.info("Successfully initialized")
    return True


#
# async def async_setup_entry(hass, entry):
#     """Set vaillant from a config entry."""
#     for platform in PLATFORMS:
#         hass.async_create_task(
#             hass.config_entries.async_forward_entry_setup(entry, platform)
#         )
#


class VaillantHub:
    """Vaillant entry point for home-assistant."""

    def __init__(self, hass, config):
        """Initialize hub."""
        from pymultimatic.model import System
        from pymultimatic.systemmanager import SystemManager

        self._manager = SystemManager(
            config[CONF_USERNAME], config[CONF_PASSWORD], config[CONF_SMARTPHONE_ID]
        )

        self.system: System = self._manager.get_system()
        self._quick_veto_duration = config[CONF_QUICK_VETO_DURATION]
        self.config = config
        self.update_system = Throttle(config[CONF_SCAN_INTERVAL])(self._update_system)
        self._hass = hass

    def _update_system(self):
        """Fetch vaillant system."""
        from pymultimatic.api import ApiError

        try:
            self._manager.request_hvac_update()
            self.system = self._manager.get_system()
            _LOGGER.debug("update_system successfully fetched")
        except ApiError:
            _LOGGER.exception("Enable to fetch data from vaillant API")
            # update_system can is called by all entities, if it fails for
            # one entity, it will certainly fail for others.
            # catching exception so the throttling is occurring

    def logout(self):
        """Logout from API."""
        from pymultimatic.api import ApiError

        try:
            self._manager.logout()
        except ApiError:
            _LOGGER.warning("Cannot logout from vaillant API", exc_info=True)
            return False
        return True

    def find_component(self, comp):
        """Find a component in the system with the given id, no IO is done."""
        from pymultimatic.model import Zone, Room, HotWater, Circulation

        if isinstance(comp, Zone):
            for zone in self.system.zones:
                if zone.id == comp.id:
                    return zone
        if isinstance(comp, Room):
            for room in self.system.rooms:
                if room.id == comp.id:
                    return room
        if isinstance(comp, HotWater):
            if self.system.hot_water and self.system.hot_water.id == comp.id:
                return self.system.hot_water
        if isinstance(comp, Circulation):
            if self.system.circulation and self.system.circulation.id == comp.id:
                return self.system.circulation

        return None

    def set_hot_water_target_temperature(self, entity, hot_water, target_temp):
        """Set hot water target temperature.

        * If there is a quick mode that impact dhw running on or holiday mode,
        remove it.

        * If dhw is ON or AUTO, modify the target temperature

        * If dhw is OFF, change to ON and set target temperature
        """
        from pymultimatic.model import OperatingModes

        touch_system = self._remove_quick_mode_or_holiday(entity)

        current_mode = self.system.get_active_mode_hot_water(hot_water).current_mode

        if current_mode == OperatingModes.OFF or touch_system:
            self._manager.set_hot_water_operating_mode(hot_water.id, OperatingModes.ON)
        self._manager.set_hot_water_setpoint_temperature(hot_water.id, target_temp)

        self.system.hot_water = hot_water
        self._refresh(touch_system, entity)

    def set_room_target_temperature(self, entity, room, target_temp):
        """Set target temperature for a room.

        * If there is a quick mode that impact room running on or holiday mode,
        remove it.

        * If the room is in MANUAL mode, simply modify the target temperature.

        * if the room is not in MANUAL mode, create à quick veto.
        """
        from pymultimatic.model import QuickVeto, OperatingModes

        touch_system = self._remove_quick_mode_or_holiday(entity)

        current_mode = self.system.get_active_mode_room(room).current_mode

        if current_mode == OperatingModes.MANUAL:
            self._manager.set_room_setpoint_temperature(room.id, target_temp)
            room.target_temperature = target_temp
        else:
            if current_mode == OperatingModes.QUICK_VETO:
                self._manager.remove_room_quick_veto(room.id)

            qveto = QuickVeto(self._quick_veto_duration, target_temp)
            self._manager.set_room_quick_veto(room.id, qveto)
            room.quick_veto = qveto
        self.system.set_room(room.id, room)

        self._refresh(touch_system, entity)

    def set_zone_target_temperature(self, entity, zone, target_temp):
        """Set target temperature for a zone.

        * If there is a quick mode related to zone running or holiday mode,
        remove it.

        * If quick veto running on, remove it and create a new one with the
            new target temp

        * If any other mode, create a quick veto
        """
        from pymultimatic.model import QuickVeto, OperatingModes

        touch_system = self._remove_quick_mode_or_holiday(entity)

        current_mode = self.system.get_active_mode_zone(zone).current_mode

        if current_mode == OperatingModes.QUICK_VETO:
            self._manager.remove_zone_quick_veto(zone.id)

        veto = QuickVeto(None, target_temp)
        self._manager.set_zone_quick_veto(zone.id, veto)
        zone.quick_veto = veto

        self.system.set_zone(zone.id, zone)
        self._refresh(touch_system, entity)

    def set_hot_water_operating_mode(self, entity, hot_water, mode):
        """Set hot water operation mode.

        If there is a quick mode that impact hot warter running on or holiday
        mode, remove it.
        """
        touch_system = self._remove_quick_mode_or_holiday(entity)

        self._manager.set_hot_water_operating_mode(hot_water.id, mode)
        hot_water.operating_mode = mode

        self.system.hot_water = hot_water
        self._refresh(touch_system, entity)

    def set_room_operating_mode(self, entity, room, mode):
        """Set room operation mode.

        If there is a quick mode that impact room running on or holiday mode,
        remove it.
        """
        touch_system = self._remove_quick_mode_or_holiday(entity)
        if room.quick_veto is not None:
            self._manager.remove_room_quick_veto(room.id)
            room.quick_veto = None

        self._manager.set_room_operating_mode(room.id, mode)
        room.operating_mode = mode

        self.system.set_room(room.id, room)
        self._refresh(touch_system, entity)

    def set_zone_operating_mode(self, entity, zone, mode):
        """Set zone operation mode.

        If there is a quick mode that impact zone running on or holiday mode,
        remove it.
        """
        touch_system = self._remove_quick_mode_or_holiday(entity)

        if zone.quick_veto is not None:
            self._manager.remove_zone_quick_veto(zone.id)
            zone.quick_veto = None

        self._manager.set_zone_operating_mode(zone.id, mode)
        zone.operating_mode = mode

        self.system.set_zone(zone.id, zone)
        self._refresh(touch_system, entity)

    def remove_quick_mode(self, entity=None):
        """Remove quick mode.

        If entity is not None, only remove if the quick mode applies to the
        given entity.
        """
        if self._remove_quick_mode_no_refresh(entity):
            self._refresh_entities()

    def remove_holiday_mode(self):
        """Remove holiday mode."""
        if self._remove_holiday_mode_no_refresh():
            self._refresh_entities()

    def set_holiday_mode(self, start_date, end_date, temperature):
        """Set holiday mode."""
        self._manager.set_holiday_mode(start_date, end_date, temperature)
        self._refresh_entities()

    def set_quick_mode(self, mode):
        """Set quick mode (remove previous one)."""
        from pymultimatic.model import QuickModes

        self._remove_quick_mode_no_refresh()
        self._manager.set_quick_mode(QuickModes.get(mode))
        self._refresh_entities()

    def set_quick_veto(self, entity, temperature, duration=None):
        """Set quick veto for the given entity."""
        from pymultimatic.model import QuickVeto, Zone

        comp = self.find_component(entity.component)

        q_duration = duration if duration else self._quick_veto_duration
        qveto = QuickVeto(q_duration, temperature)

        if isinstance(comp, Zone):
            if comp.quick_veto:
                self._manager.remove_zone_quick_veto(comp.id)
            self._manager.set_zone_quick_veto(comp.id, qveto)
        else:
            if comp.quick_veto:
                self._manager.remove_room_quick_veto(comp.id)
            self._manager.set_room_quick_veto(comp.id, qveto)
        comp.quick_veto = qveto
        self._refresh(False, entity)

    def remove_quick_veto(self, entity):
        """Remove quick veto for the given entity."""
        from pymultimatic.model import Zone

        comp = self.find_component(entity.component)

        if comp and comp.quick_veto:
            if isinstance(comp, Zone):
                self._manager.remove_zone_quick_veto(comp.id)
            else:
                self._manager.remove_room_quick_veto(comp.id)
            comp.quick_veto = None
            self._refresh(False, entity)

    def get_entity(self, entity_id):
        """Get entity owned by this component."""
        for entity in self._hass.data[DOMAIN][ENTITIES]:
            if entity.entity_id == entity_id:
                return entity
        return None

    def _remove_quick_mode_no_refresh(self, entity=None):
        from pymultimatic.model import Zone, Room, HotWater

        removed = False

        if self.system.quick_mode is not None:
            qmode = self.system.quick_mode

            if entity:
                if (
                    (isinstance(entity.component, Zone) and qmode.for_zone)
                    or (isinstance(entity.component, Room) and qmode.for_room)
                    or (isinstance(entity.component, HotWater) and qmode.for_dhw)
                ):
                    self._hard_remove_quick_mode()
                    removed = True
            else:
                self._hard_remove_quick_mode()
                removed = True
        return removed

    def _hard_remove_quick_mode(self):
        self._manager.remove_quick_mode()
        self.system.quick_mode = None

    def _remove_holiday_mode_no_refresh(self):
        from pymultimatic.model import HolidayMode

        removed = False

        if self.system.holiday_mode is not None and self.system.holiday_mode.is_active:
            removed = True
            self._manager.remove_holiday_mode()
            self.system.holiday_mode = HolidayMode(False)
        return removed

    def _remove_quick_mode_or_holiday(self, entity):
        return self._remove_holiday_mode_no_refresh() | self._remove_quick_mode_no_refresh(
            entity
        )

    def _refresh_entities(self):
        """Fetch vaillant data and force refresh of all listening entities."""
        self.update_system(no_throttle=True)
        for entity in self._hass[DOMAIN].entities:
            if entity.listening:
                entity.async_schedule_update_ha_state(True)

    def _refresh(self, touch_system, entity):
        if touch_system:
            self._refresh_entities()
        else:
            entity.async_schedule_update_ha_state(True)


class VaillantEntity(Entity, ABC):
    """Define base class for vaillant."""

    def __init__(self, domain, device_class, comp_id, comp_name, class_in_id=True):
        """Initialize entity."""
        self._device_class = device_class
        if device_class and class_in_id:
            id_format = domain + "." + DOMAIN + "_{}_" + device_class
        else:
            id_format = domain + "." + DOMAIN + "_{}"

        self.entity_id = id_format.format(slugify(comp_id)).replace(" ", "_").lower()
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
            self.hub = self.hass.data[DOMAIN][HUB]
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
        self.hass.data[DOMAIN][ENTITIES].append(self)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self.hass.data[DOMAIN][ENTITIES].remove(self)


class VaillantBoiler(Entity):
    """Base class for boiler device."""

    def __init__(self, boiler_status: BoilerStatus) -> None:
        """Initialize device."""
        self.boiler_status = boiler_status

    @property
    def device_info(self):
        """Return device specific attributes."""
        return {
            "identifiers": {(DOMAIN, self.boiler_status.device_name)},
            "name": self.boiler_status.device_name,
        }
