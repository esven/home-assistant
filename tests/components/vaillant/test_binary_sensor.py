"""Tests for the vaillant sensor."""
import pytest
from pymultimatic.model import OperatingModes, Room, Device, Circulation, \
    System, SettingModes

import homeassistant.components.vaillant as vaillant
from tests.components.vaillant import SystemManagerMock, goto_future, \
    setup_vaillant, \
    assert_entities_count, time_program, active_holiday_mode


@pytest.fixture(autouse=True)
def fixture_only_binary_sensor(mock_system_manager):
    """Mock vaillant to only handle binary_sensor."""
    orig_platforms = vaillant.PLATFORMS
    vaillant.PLATFORMS = ['binary_sensor']
    yield
    vaillant.PLATFORMS = orig_platforms


async def test_valid_config(hass):
    """Test setup with valid config."""
    assert await setup_vaillant(hass)
    assert_entities_count(hass, 10)


async def test_empty_system(hass):
    """Test setup with empty system."""
    assert await setup_vaillant(hass, system=System(None, None, None, None,
                                                    None, None, None, None,
                                                    None, None, None))
    assert_entities_count(hass, 0)


async def test_state_update(hass):
    """Test all sensors are updated accordingly to data."""
    assert await setup_vaillant(hass)
    assert_entities_count(hass, 10)

    assert hass.states.is_state(
        'binary_sensor.vaillant_circulation', 'off')
    assert hass.states.is_state('binary_sensor.vaillant_room_1_window', 'off')
    assert hass.states.is_state('binary_sensor.vaillant_room_1_lock', 'on')
    assert hass.states.is_state(
        'binary_sensor.vaillant_123456789_battery', 'off')
    assert hass.states.is_state('binary_sensor.vaillant_boiler', 'off')
    assert hass.states.is_state(
        'binary_sensor.vaillant_123456789_connectivity', 'on')
    assert hass.states.is_state(
        'binary_sensor.vaillant_system_update', 'off')
    assert hass.states.is_state(
        'binary_sensor.vaillant_system_online', 'on')
    assert hass.states.is_state(
        'binary_sensor.vaillant_holiday', 'off')
    state = hass.states.get('binary_sensor.vaillant_holiday')
    assert state.attributes.get('start_date') is None
    assert state.attributes.get('end_date') is None
    assert state.attributes.get('temperature') is None
    assert hass.states.is_state(
        'binary_sensor.vaillant_quick_mode', 'off')

    system = SystemManagerMock.system
    system.circulation = Circulation(
        'circulation', 'Circulation',
        time_program(SettingModes.ON), OperatingModes.AUTO)

    room_device = Device('Device 1', '123456789', 'VALVE', True, True)
    system.set_room('1', Room('1', 'Room 1', time_program(),
                              22, 24, OperatingModes.AUTO, None, True, True,
                              [room_device]))

    system.boiler_status.status_code = 'F11'
    system.system_status.online_status = 'OFFLINE'
    system.system_status.update_status = 'UPDATE_PENDING'
    system.holiday_mode = active_holiday_mode()
    SystemManagerMock.system = system

    await goto_future(hass)

    assert_entities_count(hass, 10)
    assert hass.states.is_state(
        'binary_sensor.vaillant_circulation', 'on')
    assert hass.states.is_state('binary_sensor.vaillant_room_1_window', 'on')
    assert hass.states.is_state('binary_sensor.vaillant_room_1_lock', 'off')
    assert hass.states.is_state(
        'binary_sensor.vaillant_123456789_battery', 'on')
    assert hass.states.is_state('binary_sensor.vaillant_boiler', 'on')
    assert hass.states.is_state(
        'binary_sensor.vaillant_123456789_connectivity', 'off')
    assert hass.states.is_state(
        'binary_sensor.vaillant_system_update', 'on')
    assert hass.states.is_state(
        'binary_sensor.vaillant_system_online', 'off')
    assert hass.states.is_state(
        'binary_sensor.vaillant_holiday', 'on')
    state = hass.states.get('binary_sensor.vaillant_holiday')
    assert state.attributes['start_date'] == \
        system.holiday_mode.start_date.isoformat()
    assert state.attributes['end_date'] == \
        system.holiday_mode.end_date.isoformat()
    assert state.attributes['temperature'] == \
        system.holiday_mode.target_temperature
    assert hass.states.is_state(
        'binary_sensor.vaillant_quick_mode', 'off')
