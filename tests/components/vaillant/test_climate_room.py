"""Tests for the vaillant sensor."""

import pytest
from pymultimatic.model import (
    System,
    OperatingModes,
    QuickModes,
    Room,
    SettingModes,
    QuickMode)

import homeassistant.components.vaillant as vaillant
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
)
from homeassistant.components.vaillant import ATTR_VAILLANT_MODE
from tests.components.vaillant import SystemManagerMock, goto_future, \
    setup_vaillant, \
    call_service, assert_entities_count, get_system, time_program, \
    active_holiday_mode


def _assert_room_state(hass, mode, hvac, current_temp, temp):
    """Assert room climate state."""
    state = hass.states.get("climate.vaillant_room_1")

    assert hass.states.is_state("climate.vaillant_room_1", hvac)
    assert state.attributes["current_temperature"] == current_temp
    assert state.attributes["max_temp"] == Room.MAX_TARGET_TEMP
    assert state.attributes["min_temp"] == Room.MIN_TARGET_TEMP

    assert state.attributes["temperature"] == temp

    assert set(state.attributes["hvac_modes"]) == {
        HVAC_MODE_AUTO,
        HVAC_MODE_OFF,
    }

    assert state.attributes[ATTR_VAILLANT_MODE] == mode.name


@pytest.fixture(autouse=True)
def fixture_only_climate(mock_system_manager):
    """Mock vaillant to only handle sensor."""
    orig_platforms = vaillant.PLATFORMS
    vaillant.PLATFORMS = ["climate"]
    yield
    vaillant.PLATFORMS = orig_platforms


async def test_valid_config(hass):
    """Test setup with valid config."""
    assert await setup_vaillant(hass)
    assert_entities_count(hass, 2)
    _assert_room_state(hass, OperatingModes.AUTO, HVAC_MODE_AUTO, 22, 20)


async def test_empty_system(hass):
    """Test setup with empty system."""
    assert await setup_vaillant(hass,
                                system=System(None, None, None, None, None,
                                              None,
                                              None, None, None, None, None)
                                )
    assert_entities_count(hass, 0)


async def test_state_update_room(hass):
    """Test room climate is updated accordingly to data."""
    assert await setup_vaillant(hass)
    _assert_room_state(hass, OperatingModes.AUTO, HVAC_MODE_AUTO, 22, 20)

    system = SystemManagerMock.system
    room = system.rooms[0]
    room.current_temperature = 25
    room.target_temperature = 30
    room.time_program = time_program(SettingModes.ON, 30)
    await goto_future(hass)

    _assert_room_state(hass, OperatingModes.AUTO, HVAC_MODE_AUTO, 25, 30)


async def _test_mode_hvac(hass, mode, hvac_mode, target_temp):
    system = get_system()

    if isinstance(mode, QuickMode):
        system.quick_mode = mode
    else:
        system.rooms[0].operating_mode = mode

    assert await setup_vaillant(hass, system=system)
    room = SystemManagerMock.system.rooms[0]
    _assert_room_state(hass, mode, hvac_mode, room.current_temperature,
                       target_temp)


async def test_auto_mode_hvac_auto(hass):
    """Test with auto mode."""
    room = get_system().rooms[0]
    await _test_mode_hvac(hass, OperatingModes.AUTO, HVAC_MODE_AUTO,
                          room.active_mode.target_temperature)


async def test_off_mode_hvac_off(hass):
    """Test with off mode."""
    await _test_mode_hvac(hass, OperatingModes.OFF, HVAC_MODE_OFF,
                          Room.MIN_TARGET_TEMP)


async def test_quickmode_system_off_mode_hvac_off(hass):
    """Test with quick mode off."""
    await _test_mode_hvac(hass, QuickModes.SYSTEM_OFF, HVAC_MODE_OFF,
                          Room.MIN_TARGET_TEMP)


async def test_holiday_mode(hass):
    """Test with holiday mode."""
    system = get_system()
    system.holiday_mode = active_holiday_mode()

    assert await setup_vaillant(hass, system=system)

    _assert_room_state(hass, QuickModes.HOLIDAY, HVAC_MODE_OFF,
                       system.rooms[0].current_temperature, 15)


async def test_set_target_temp_cool(hass):
    """Test hvac is cool with lower target temp."""
    room = get_system().rooms[0]
    assert await setup_vaillant(hass)

    await call_service(
        hass,
        "climate",
        "set_temperature",
        {"entity_id": "climate.vaillant_room_1", "temperature": 14},
    )

    _assert_room_state(hass, OperatingModes.QUICK_VETO, HVAC_MODE_COOL,
                       room.current_temperature, 14)
    SystemManagerMock.instance.set_room_quick_veto.assert_called_once()


async def test_set_target_temp_heat(hass):
    """Test hvac is heat with higher target temp."""
    room = get_system().rooms[0]
    assert await setup_vaillant(hass)

    await call_service(
        hass,
        "climate",
        "set_temperature",
        {"entity_id": "climate.vaillant_room_1", "temperature": 30},
    )

    _assert_room_state(hass, OperatingModes.QUICK_VETO, HVAC_MODE_HEAT,
                       room.current_temperature, 30)
    SystemManagerMock.instance.set_room_quick_veto.assert_called_once()


async def test_room_heating_manual(hass):
    """Test hvac is heating with higher target temp."""
    system = get_system()
    room = system.rooms[0]
    room.operating_mode = OperatingModes.MANUAL
    room.current_temperature = 15
    room.target_temperature = 25

    assert await setup_vaillant(hass, system=system)
    _assert_room_state(hass, OperatingModes.MANUAL, HVAC_MODE_HEAT, 15, 25)


async def test_room_cooling_manual(hass):
    """Test hvac is cool with lower target temp."""
    system = get_system()
    room = system.rooms[0]
    room.operating_mode = OperatingModes.MANUAL
    room.current_temperature = 25
    room.target_temperature = 15

    assert await setup_vaillant(hass, system=system)
    _assert_room_state(hass, OperatingModes.MANUAL, HVAC_MODE_COOL, 25, 15)
