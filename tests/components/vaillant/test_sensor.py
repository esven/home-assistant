"""Tests for the vaillant sensor."""

from pymultimatic.model import System
import pytest

import homeassistant.components.vaillant as vaillant

from tests.components.vaillant import (
    SystemManagerMock,
    assert_entities_count,
    goto_future,
    setup_vaillant,
)


@pytest.fixture(autouse=True)
def fixture_only_sensor(mock_system_manager):
    """Mock vaillant to only handle sensor."""
    orig_platforms = vaillant.PLATFORMS
    vaillant.PLATFORMS = ["sensor"]
    yield
    vaillant.PLATFORMS = orig_platforms


async def test_valid_config(hass):
    """Test setup with valid config."""
    assert await setup_vaillant(hass)
    assert_entities_count(hass, 3)


async def test_empty_system(hass):
    """Test setup with empty system."""
    assert await setup_vaillant(
        hass,
        system=System(
            None, None, None, None, None, None, None, None, None, None, None, None
        ),
    )
    assert_entities_count(hass, 0)


async def test_state_update(hass):
    """Test all sensors are updated accordingly to data."""
    assert await setup_vaillant(hass)
    assert_entities_count(hass, 3)

    assert hass.states.is_state("sensor.vaillant_boiler_pressure", "1.4")
    assert hass.states.is_state("sensor.vaillant_boiler_temperature", "20")
    assert hass.states.is_state("sensor.vaillant_outdoor_temperature", "18")

    system = SystemManagerMock.system
    system.outdoor_temperature = 21
    system.boiler_info.water_pressure = 1.6
    system.boiler_info.current_temperature = 32
    SystemManagerMock.system = system

    await goto_future(hass)

    assert hass.states.is_state("sensor.vaillant_boiler_pressure", "1.6")
    assert hass.states.is_state("sensor.vaillant_boiler_temperature", "32")
    assert hass.states.is_state("sensor.vaillant_outdoor_temperature", "21")
