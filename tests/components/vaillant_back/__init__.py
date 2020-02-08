"""The tests for vaillant platforms."""
import datetime

import mock
from pymultimatic.model import (
    BoilerInfo,
    BoilerStatus,
    Circulation,
    Device,
    HolidayMode,
    HotWater,
    OperatingModes,
    Room,
    SettingModes,
    System,
    SystemStatus,
    TimePeriodSetting,
    TimeProgram,
    TimeProgramDay,
    Zone,
)
from pymultimatic.systemmanager import SystemManager

from homeassistant.components.vaillant import DOMAIN, ENTITIES
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.setup import async_setup_component
from homeassistant.util import utcnow

from tests.common import async_fire_time_changed

VALID_MINIMAL_CONFIG = {DOMAIN: {CONF_USERNAME: "test", CONF_PASSWORD: "test"}}


class SystemManagerMock(SystemManager):
    """Mock implementation of SystemManager."""

    instance = None
    system = None
    _methods = [f for f in dir(SystemManager) if not f.startswith("_")]

    @classmethod
    def reset_mock(cls):
        """Reset mock, clearing instance and system."""
        cls.instance = None
        cls.system = None

    def __init__(self, user, password, smart_phone_id, file_path=None):
        """Mock the constructor."""
        self.system = self.__class__.system
        self._init()
        self.__class__.instance = self

    def _init(self):
        for method in self.__class__._methods:
            setattr(self, method, mock.MagicMock())

        setattr(self, "get_system", mock.MagicMock(return_value=self.system))

        get_zone = mock.MagicMock(
            return_value=lambda: self.system.zones[0]
            if self.system and self.system.zones
            else None
        )
        get_room = mock.MagicMock(
            return_value=lambda: self.system.rooms[0]
            if self.system and self.system.rooms
            else None
        )
        setattr(self, "get_zone", get_zone)
        setattr(self, "get_room", get_room)


def get_system():
    """Return default system."""
    holiday_mode = None
    boiler_status = BoilerStatus(
        "boiler",
        "short description",
        "S.31",
        "Long description",
        datetime.datetime.now(),
        "hint",
    )

    boiler_info = BoilerInfo(1.4, 20)

    system_status = SystemStatus("ONLINE", "UPDATE_NOT_PENDING")

    zone = Zone(
        "zone_1",
        "Zone 1",
        time_program(temp=27),
        25,
        30,
        OperatingModes.AUTO,
        None,
        22,
        "heating",
        False,
    )

    room_device = Device("Device 1", "123456789", "VALVE", False, False)
    room = Room(
        "1",
        "Room 1",
        time_program(),
        22,
        24,
        OperatingModes.AUTO,
        None,
        False,
        False,
        [room_device],
    )

    hot_water = HotWater(
        "hot_water", "Hot water", time_program(temp=None), 45, 40, OperatingModes.AUTO,
    )

    circulation = Circulation(
        "circulation", "Circulation", time_program(), OperatingModes.AUTO
    )

    outdoor_temp = 18
    quick_mode = None

    return System(
        holiday_mode,
        system_status,
        boiler_status,
        [zone],
        [room],
        hot_water,
        circulation,
        outdoor_temp,
        quick_mode,
        [],
        boiler_info,
    )


def active_holiday_mode():
    """Return a active holiday mode."""
    start = datetime.date.today() - datetime.timedelta(days=1)
    end = datetime.date.today() + datetime.timedelta(days=1)
    return HolidayMode(True, start, end, 15)


def time_program(heating_mode=SettingModes.OFF, temp=20):
    """Create a default time program."""
    tp_day_setting = TimePeriodSetting("00:00", temp, heating_mode)
    tp_day = TimeProgramDay([tp_day_setting])
    tp_days = {
        "monday": tp_day,
        "tuesday": tp_day,
        "wednesday": tp_day,
        "thursday": tp_day,
        "friday": tp_day,
        "saturday": tp_day,
        "sunday": tp_day,
    }
    return TimeProgram(tp_days)


async def goto_future(hass, future=None):
    """Move to future."""
    if not future:
        future = utcnow() + datetime.timedelta(minutes=5)
    with mock.patch("homeassistant.util.utcnow", return_value=future):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()


async def setup_vaillant(hass, config=None, system=None):
    """Set up vaillant component."""
    if not config:
        config = VALID_MINIMAL_CONFIG
    if not system:
        system = get_system()
    SystemManagerMock.system = system
    is_setup = await async_setup_component(hass, DOMAIN, config)
    await hass.async_block_till_done()
    return is_setup


async def call_service(hass, domain, service, data):
    """Call hass service."""
    await hass.services.async_call(domain, service, data)
    await hass.async_block_till_done()


def assert_entities_count(hass, count):
    """Count entities owned by the component."""
    assert (
        len(hass.states.async_entity_ids()) == len(hass.data[DOMAIN][ENTITIES]) == count
    )
