"""Interfaces with Vaillant climate."""

import abc
import logging
from datetime import timedelta, datetime
from typing import Optional, List, Dict, Any

from pymultimatic.model import (
    System,
    Room,
    Component,
    Zone,
    OperatingModes,
    QuickModes,
    Mode,
)

from homeassistant.components.climate import ClimateDevice
from homeassistant.components.climate.const import (
    SUPPORT_TARGET_TEMPERATURE,
    DOMAIN,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_AUTO,
    HVAC_MODE_FAN_ONLY,
    HVAC_MODE_COOL,
)
from homeassistant.const import TEMP_CELSIUS, ATTR_TEMPERATURE
from homeassistant.util import dt as dt_util
from . import VaillantEntity
from .const import (HUB, DOMAIN as VAILLANT,
                    ATTR_VAILLANT_MODE, ATTR_QUICK_VETO_END,
                    ATTR_VAILLANT_SETTING, ATTR_VAILLANT_NEXT_SETTING,
                    ATTR_VAILLANT_SETTING_END, ATTR_VAILLANT_SETTING_END_TS,
                    ATTR_QUICK_VETO_END_TS)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Vaillant climate platform."""
    pass
    # climates = []
    # hub = hass.data[DOMAIN][HUB]
    #
    # if hub.system:
    #     if hub.system.zones:
    #         for zone in hub.system.zones:
    #             if not zone.rbr:
    #                 entity = ZoneClimate(hub.system, zone)
    #                 climates.append(entity)
    #
    #     if hub.system.rooms:
    #         for room in hub.system.rooms:
    #             entity = RoomClimate(hub.system, room)
    #             climates.append(entity)
    #
    # _LOGGER.info("Adding %s climate entities", len(climates))
    #
    # async_add_entities(climates, True)
    # return True


async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up the Vaillant climate platform."""
    climates = []
    hub = hass.data[VAILLANT][HUB]

    if hub.system:
        if hub.system.zones:
            for zone in hub.system.zones:
                if not zone.rbr:
                    entity = ZoneClimate(hub.system, zone)
                    climates.append(entity)

        if hub.system.rooms:
            for room in hub.system.rooms:
                entity = RoomClimate(hub.system, room)
                climates.append(entity)

    _LOGGER.info("Adding %s climate entities", len(climates))

    async_add_entities(climates, True)
    return True


class VaillantClimate(VaillantEntity, ClimateDevice, abc.ABC):
    """Base class for climate."""

    def __init__(self, system: System, comp_name, comp_id, component: Component):
        """Initialize entity."""
        super().__init__(DOMAIN, None, comp_name, comp_id)
        self._system = None
        self.component = None
        self._active_mode = None
        self._refresh(system, component)

    @property
    def listening(self):
        """Return whether this entity is listening for system changes or not."""
        return True

    @property
    def available(self):
        """Return True if entity is available."""
        return self.component is not None

    @property
    def temperature_unit(self):
        """Return the unit of measurement used by the platform."""
        return TEMP_CELSIUS

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        _LOGGER.debug("Target temp is %s", self._active_mode.target_temperature)
        return self._active_mode.target_temperature

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.component.current_temperature

    @property
    def is_aux_heat(self) -> Optional[bool]:
        """Return true if aux heater."""
        return False

    @property
    def state_attributes(self) -> Dict[str, Any]:
        """Return the optional state attributes."""
        attributes = super().state_attributes
        self._active_mode = self.get_active_mode()
        attributes.update({
            ATTR_VAILLANT_MODE: self._active_mode.current_mode.name
        })

        if self._active_mode.current_mode == OperatingModes.QUICK_VETO:
            if self.component.quick_veto.remaining_duration:
                qveto_millis = self.component.quick_veto.remaining_duration \
                    * 60 * 1000
                end_time = dt_util.as_local(datetime.now()) +\
                    timedelta(milliseconds=qveto_millis)
                attributes.update({
                    ATTR_QUICK_VETO_END: end_time.isoformat(),
                    ATTR_QUICK_VETO_END_TS: end_time.timestamp()
                })
        elif self._active_mode.current_mode == OperatingModes.AUTO:
            now = dt_util.as_local(datetime.now())
            abs_min = now.hour * 60 + now.minute
            next_setting = self.component.time_program.get_next(now)

            next_start = now
            # it means, next setting is tomorrow
            if next_setting.absolute_minutes < abs_min:
                next_start = next_start + timedelta(days=1)
            next_start = next_start.replace(
                hour=next_setting.hour,
                minute=next_setting.minute,
                second=0,
                microsecond=0,
            )
            # next_start_date = dt_util.as_utc(next_start)
            next_start_ts = dt_util.as_timestamp(next_start)

            attributes.update(
                {
                    ATTR_VAILLANT_NEXT_SETTING: next_setting.setting.name
                    if next_setting.setting
                    else next_setting.target_temperature,
                    ATTR_VAILLANT_SETTING_END: next_start.isoformat(),
                    ATTR_VAILLANT_SETTING_END_TS: next_start_ts,
                }
            )

            if self._active_mode.sub_mode is not None:
                attributes.update(
                    {ATTR_VAILLANT_SETTING: self._active_mode.sub_mode.name}
                )

        return attributes

    @property
    def fan_mode(self) -> Optional[str]:
        """Return the fan setting."""
        return None

    @property
    def fan_modes(self) -> Optional[List[str]]:
        """Return the list of available fan modes."""
        return None

    @property
    def swing_mode(self) -> Optional[str]:
        """Return the swing setting."""
        return None

    @property
    def swing_modes(self) -> Optional[List[str]]:
        """Return the list of available swing modes."""
        return None

    def set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        pass

    def set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        pass

    def set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        pass

    def turn_aux_heat_on(self) -> None:
        """Turn auxiliary heater on."""
        pass

    def turn_aux_heat_off(self) -> None:
        """Turn auxiliary heater off."""
        pass

    @property
    def target_temperature_high(self) -> Optional[float]:
        """Return the highbound target temperature we try to reach."""
        return None

    @property
    def target_temperature_low(self) -> Optional[float]:
        """Return the lowbound target temperature we try to reach."""
        return None

    @property
    def hvac_mode(self) -> str:
        """Return hvac operation ie. heat, cool mode."""

        hvac_mode = self.mode_to_hvac(self._active_mode.current_mode)

        if hvac_mode is None:
            if self._active_mode.current_mode in [OperatingModes.QUICK_VETO,
                                                  OperatingModes.MANUAL]:
                if self._is_heating():
                    hvac_mode = HVAC_MODE_HEAT
                else:
                    hvac_mode = HVAC_MODE_COOL
            else:
                _LOGGER.warning("Unknown mode %s, will return None",
                                self._active_mode.current_mode)
        return hvac_mode

    async def vaillant_update(self):
        """Update specific for vaillant."""
        self._refresh(self.hub.system, self.hub.find_component(self.component))

    def _refresh(self, system, component):
        """Refresh the entity."""
        self._system = system
        self.component = component
        self._active_mode = self.get_active_mode()

    def _is_heating(self):
        return self._active_mode.target_temperature > \
            self.component.current_temperature

    @abc.abstractmethod
    def get_active_mode(self):
        """Get active mode of the climate."""
        pass

    @abc.abstractmethod
    def mode_to_hvac(self, mode):
        """Get the hvac mode based on vaillant mode."""
        pass


class RoomClimate(VaillantClimate):
    """Climate for a room."""

    _MODE_TO_HVAC: Dict[Mode, str] = {
        OperatingModes.AUTO: HVAC_MODE_AUTO,
        OperatingModes.OFF: HVAC_MODE_OFF,
        QuickModes.HOLIDAY: HVAC_MODE_OFF,
        QuickModes.SYSTEM_OFF: HVAC_MODE_OFF,
    }

    _HVAC_TO_MODE: Dict[str, Mode] = {
        HVAC_MODE_AUTO: OperatingModes.AUTO,
        HVAC_MODE_OFF: OperatingModes.OFF,
    }

    _SUPPORTED_HVAC_MODE = list(set(_MODE_TO_HVAC.values()))

    def __init__(self, system: System, room: Room):
        """Initialize entity."""
        super().__init__(system, room.name, room.name, room)

    def mode_to_hvac(self, mode):
        """Get the hvac mode based on vaillant mode."""
        return self._MODE_TO_HVAC.get(mode, None)

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return self._SUPPORTED_HVAC_MODE

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return None

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        return None

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return Room.MIN_TARGET_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return Room.MAX_TARGET_TEMP

    def get_active_mode(self):
        """Get active mode of the climate."""
        return self._system.get_active_mode_room(self.component)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        self.hub.set_room_target_temperature(
            self, self.component, float(kwargs.get(ATTR_TEMPERATURE))
        )

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""

    def set_hvac_mode(self, hvac_mode: str) -> None:
        """Set new target hvac mode."""
        mode = self._HVAC_TO_MODE[hvac_mode]
        self.hub.set_room_operating_mode(self, self.component, mode)


class ZoneClimate(VaillantClimate):
    """Climate for a zone."""

    _MODE_TO_HVAC: Dict[Mode, str] = {
        OperatingModes.DAY: HVAC_MODE_HEAT,
        QuickModes.PARTY: HVAC_MODE_HEAT,
        OperatingModes.NIGHT: HVAC_MODE_COOL,
        OperatingModes.AUTO: HVAC_MODE_AUTO,
        QuickModes.ONE_DAY_AT_HOME: HVAC_MODE_AUTO,
        OperatingModes.OFF: HVAC_MODE_OFF,
        QuickModes.ONE_DAY_AWAY: HVAC_MODE_OFF,
        QuickModes.HOLIDAY: HVAC_MODE_OFF,
        QuickModes.SYSTEM_OFF: HVAC_MODE_OFF,
        QuickModes.VENTILATION_BOOST: HVAC_MODE_FAN_ONLY,
    }

    _HVAC_TO_MODE: Dict[str, Mode] = {
        HVAC_MODE_AUTO: OperatingModes.AUTO,
        HVAC_MODE_OFF: OperatingModes.OFF,
        HVAC_MODE_HEAT: OperatingModes.DAY,
        HVAC_MODE_COOL: OperatingModes.NIGHT,
    }

    _SUPPORTED_HVAC_MODE = list(set(_HVAC_TO_MODE.keys()))

    def __init__(self, system: System, zone: Zone):
        """Initialize entity."""
        super().__init__(system, zone.id, zone.name, zone)

    def mode_to_hvac(self, mode):
        """Get the hvac mode based on vaillant mode."""
        return self._MODE_TO_HVAC.get(mode, None)

    @property
    def hvac_modes(self) -> List[str]:
        """Return the list of available hvac operation modes."""
        return self._SUPPORTED_HVAC_MODE

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode, e.g., home, away, temp."""
        return None

    @property
    def preset_modes(self) -> Optional[List[str]]:
        """Return a list of available preset modes."""
        return None

    def set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_TARGET_TEMPERATURE

    @property
    def min_temp(self):
        """Return the minimum temperature."""
        return Zone.MIN_TARGET_TEMP

    @property
    def max_temp(self):
        """Return the maximum temperature."""
        return Zone.MAX_TARGET_TEMP

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._active_mode.target_temperature

    def get_active_mode(self):
        """Get active mode of the climate."""
        return self._system.get_active_mode_zone(self.component)

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temp = kwargs.get(ATTR_TEMPERATURE)

        if temp and temp != self._active_mode.target_temperature:
            _LOGGER.debug("Setting target temp to %s", temp)
            self.hub.set_zone_target_temperature(self, self.component, temp)
        else:
            _LOGGER.debug("Nothing to do")

    def set_hvac_mode(self, hvac_mode):
        """Set new target hvac mode."""
        mode = self._HVAC_TO_MODE[hvac_mode]
        self.hub.set_zone_operating_mode(self, self.component, mode)
