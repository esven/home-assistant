"""Dynamic entity add/remove test."""
from datetime import datetime

import pytest
from pymultimatic.model import Error

from homeassistant.components import vaillant
from homeassistant.components.vaillant import DOMAIN, HUB
from tests.components.vaillant import get_system, setup_vaillant, goto_future


@pytest.fixture(autouse=True)
def fixture_only_binary_sensor(mock_system_manager):
    """Mock vaillant to only handle binary_sensor."""
    orig_platforms = vaillant.PLATFORMS
    vaillant.PLATFORMS = ['binary_sensor']
    yield
    vaillant.PLATFORMS = orig_platforms


async def test_error(hass):
    """Test entity is created."""
    system = get_system()
    system.errors = [Error('device_name', 'title', 'F152', 'description',
                           datetime.now())]
    assert await setup_vaillant(hass, system=system)
    assert hass.data[DOMAIN][HUB]\
               .get_entity('binary_sensor.vaillant_error_f152') is not None


async def test_error_removed(hass):
    """Test entity is created and removed."""
    system = get_system()
    system.errors = [Error('device_name', 'title', 'F152', 'description',
                           datetime.now())]
    assert await setup_vaillant(hass, system=system)
    assert hass.data[DOMAIN][HUB]\
               .get_entity('binary_sensor.vaillant_error_f152') is not None
    assert 'binary_sensor.vaillant_error_f152' in hass.states.async_entity_ids()

    system.errors = []
    await goto_future(hass)

    assert hass.data[DOMAIN][HUB] \
               .get_entity('binary_sensor.vaillant_error_f152') is None
    assert 'binary_sensor.vaillant_error_f152' \
           not in hass.states.async_entity_ids()
