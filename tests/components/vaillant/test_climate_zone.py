"""Tests for the vaillant zone climate."""

import pytest
from pymultimatic.model import (
    System,
    OperatingModes,
    QuickModes,
    Zone,
    SettingModes,
    QuickMode)

import homeassistant.components.vaillant as vaillant
from homeassistant.components.climate.const import (
    HVAC_MODE_AUTO,
    HVAC_MODE_OFF,
    HVAC_MODE_HEAT,
    HVAC_MODE_COOL,
    HVAC_MODE_FAN_ONLY,
    SUPPORT_TARGET_TEMPERATURE,
)
from homeassistant.components.vaillant.const import ATTR_VAILLANT_MODE
from tests.components.vaillant import SystemManagerMock, goto_future, \
    setup_vaillant, \
    call_service, get_system, active_holiday_mode, time_program, \
    assert_entities_count


@pytest.fixture(autouse=True)
def fixture_only_climate(mock_system_manager):
    """Mock vaillant to only handle sensor."""
    orig_platforms = vaillant.PLATFORMS
    vaillant.PLATFORMS = ["climate"]
    yield
    vaillant.PLATFORMS = orig_platforms


def _assert_zone_state(hass, mode, hvac, current_temp, target_temp=None):
    """Assert zone climate state."""
    state = hass.states.get("climate.vaillant_zone_1")

    assert hass.states.is_state("climate.vaillant_zone_1", hvac)
    assert state.attributes["current_temperature"] == current_temp
    assert state.attributes["max_temp"] == Zone.MAX_TARGET_TEMP
    assert state.attributes["min_temp"] == Zone.MIN_TARGET_TEMP
    assert state.attributes["temperature"] == target_temp
    assert set(state.attributes["hvac_modes"]) == {
        HVAC_MODE_OFF,
        HVAC_MODE_AUTO,
        HVAC_MODE_HEAT,
        HVAC_MODE_COOL
    }

    assert state.attributes["supported_features"] == SUPPORT_TARGET_TEMPERATURE

    assert state.attributes[ATTR_VAILLANT_MODE] == mode.name


async def test_valid_config(hass):
    """Test setup with valid config."""
    assert await setup_vaillant(hass)
    # one room, one zone
    assert_entities_count(hass, 2)
    zone = SystemManagerMock.system.zones[0]
    _assert_zone_state(hass, OperatingModes.AUTO, HVAC_MODE_AUTO,
                       zone.current_temperature,
                       zone.active_mode.target_temperature)


async def test_empty_system(hass):
    """Test setup with empty system."""
    assert await setup_vaillant(
        hass, system=System(None, None, None, None, None, None, None, None,
                            None, None, None))
    assert_entities_count(hass, 0)


async def _test_mode_hvac(hass, mode, hvac_mode, target_temp):
    system = get_system()

    if isinstance(mode, QuickMode):
        system.quick_mode = mode
    else:
        system.zones[0].operating_mode = mode

    assert await setup_vaillant(hass, system=system)
    zone = SystemManagerMock.system.zones[0]
    _assert_zone_state(hass, mode, hvac_mode,
                       zone.current_temperature, target_temp)


async def _test_set_hvac(hass, hvac, mode, current_temp, target_temp):
    assert await setup_vaillant(hass)

    await call_service(
        hass,
        "climate",
        "set_hvac_mode",
        {"entity_id": "climate.vaillant_zone_1", "hvac_mode": hvac},
    )

    _assert_zone_state(hass, mode, hvac, current_temp, target_temp)


async def test_day_mode_hvac_heat(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_mode_hvac(hass, OperatingModes.DAY, HVAC_MODE_HEAT,
                          zone.target_temperature)


async def test_night_mode_hvac_cool(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_mode_hvac(hass, OperatingModes.NIGHT, HVAC_MODE_COOL,
                          zone.target_min_temperature)


async def test_auto_mode_hvac_auto(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_mode_hvac(hass, OperatingModes.AUTO, HVAC_MODE_AUTO,
                          zone.active_mode.target_temperature)


async def test_off_mode_hvac_off(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    zone.mode = OperatingModes.OFF
    await _test_mode_hvac(hass, OperatingModes.OFF, HVAC_MODE_OFF,
                          Zone.MIN_TARGET_TEMP)


async def test_quickmode_system_off_mode_hvac_off(hass):
    """Test mode <> hvac."""
    await _test_mode_hvac(hass, QuickModes.SYSTEM_OFF, HVAC_MODE_OFF,
                          Zone.MIN_TARGET_TEMP)


async def test_quickmode_one_day_away_mode_hvac_off(hass):
    """Test mode <> hvac."""
    await _test_mode_hvac(hass, QuickModes.ONE_DAY_AWAY, HVAC_MODE_OFF,
                          Zone.MIN_TARGET_TEMP)


async def test_quickmode_party_mode_hvac_heat(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_mode_hvac(hass, QuickModes.PARTY, HVAC_MODE_HEAT,
                          zone.target_temperature)


async def test_quickmode_one_day_home_hvac_auto(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_mode_hvac(hass, QuickModes.ONE_DAY_AT_HOME, HVAC_MODE_AUTO,
                          zone.active_mode.target_temperature)


async def test_quickmode_ventilation_boost_hvac_fan(hass):
    """Test mode <> hvac."""
    await _test_mode_hvac(hass, QuickModes.VENTILATION_BOOST,
                          HVAC_MODE_FAN_ONLY,
                          Zone.MIN_TARGET_TEMP)


async def test_holiday_hvac_off(hass):
    """Test mode <> hvac."""
    system = get_system()
    system.holiday_mode = active_holiday_mode()

    assert await setup_vaillant(hass, system=system)
    _assert_zone_state(hass, QuickModes.HOLIDAY, HVAC_MODE_OFF,
                       system.zones[0].current_temperature, 15)


async def test_set_hvac_heat(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_set_hvac(hass, HVAC_MODE_HEAT, OperatingModes.DAY,
                         zone.current_temperature, zone.target_temperature)


async def test_set_hvac_auto(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_set_hvac(hass, HVAC_MODE_AUTO, OperatingModes.AUTO,
                         zone.current_temperature,
                         zone.active_mode.target_temperature)


async def test_set_hvac_cool(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_set_hvac(hass, HVAC_MODE_COOL, OperatingModes.NIGHT,
                         zone.current_temperature,
                         zone.target_min_temperature)


async def test_set_hvac_off(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    await _test_set_hvac(hass, HVAC_MODE_OFF, OperatingModes.OFF,
                         zone.current_temperature, Zone.MIN_TARGET_TEMP)


async def test_set_target_temp_cool(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    assert await setup_vaillant(hass)

    await call_service(
        hass,
        "climate",
        "set_temperature",
        {"entity_id": "climate.vaillant_zone_1", "temperature": 14},
    )

    _assert_zone_state(hass, OperatingModes.QUICK_VETO, HVAC_MODE_COOL,
                       zone.current_temperature, 14)
    SystemManagerMock.instance.set_zone_quick_veto.assert_called_once()


async def test_set_target_temp_heat(hass):
    """Test mode <> hvac."""
    zone = get_system().zones[0]
    assert await setup_vaillant(hass)

    await call_service(
        hass,
        "climate",
        "set_temperature",
        {"entity_id": "climate.vaillant_zone_1", "temperature": 30},
    )

    _assert_zone_state(hass, OperatingModes.QUICK_VETO, HVAC_MODE_HEAT,
                       zone.current_temperature, 30)
    SystemManagerMock.instance.set_zone_quick_veto.assert_called_once()


async def test_state_update_room(hass):
    """Test room climate is updated accordingly to data."""
    assert await setup_vaillant(hass)
    zone = SystemManagerMock.system.zones[0]
    _assert_zone_state(hass, OperatingModes.AUTO, HVAC_MODE_AUTO,
                       zone.current_temperature,
                       zone.active_mode.target_temperature)

    system = SystemManagerMock.system
    zone = system.zones[0]
    zone.current_temperature = 25
    zone.target_temperature = 30
    zone.time_program = time_program(SettingModes.ON, 30)
    await goto_future(hass)

    _assert_zone_state(hass, OperatingModes.AUTO, HVAC_MODE_AUTO, 25, 30)
