"""Utilities for HA."""
from datetime import datetime, timedelta

from pymultimatic.model import OperatingModes

from homeassistant.util import dt

from .const import (
    ATTR_QUICK_VETO_END,
    ATTR_VAILLANT_MODE,
    ATTR_VAILLANT_NEXT_SETTING,
    ATTR_VAILLANT_SETTING,
    ATTR_VAILLANT_SETTING_END,
)


def gen_state_attrs(component, active_mode):
    """Generate state_attrs."""
    attrs = {}
    attrs.update({ATTR_VAILLANT_MODE: active_mode.current_mode.name})

    if active_mode.current_mode == OperatingModes.QUICK_VETO:
        if component.quick_veto.remaining_duration:
            qveto_end = _get_quick_veto_end(component)
            if qveto_end:
                attrs.update({ATTR_QUICK_VETO_END: qveto_end.isoformat()})
    elif active_mode.current_mode == OperatingModes.AUTO:
        setting = _get_next_setting(component)
        value = setting.setting.name if setting.setting else setting.target_temperature
        attrs.update(
            {
                ATTR_VAILLANT_NEXT_SETTING: value,
                ATTR_VAILLANT_SETTING_END: setting.start.isoformat(),
            }
        )

        if active_mode.sub_mode is not None:
            attrs.update({ATTR_VAILLANT_SETTING: active_mode.sub_mode.name})

    return attrs


def _get_quick_veto_end(component):
    end_time = None
    # there is no remaining duration for zone
    if component.quick_veto.remaining_duration:
        millis = component.quick_veto.remaining_duration * 60 * 1000
        end_time = dt.as_local(datetime.now()) + timedelta(milliseconds=millis)
        end_time = end_time.replace(second=0, microsecond=0)
    return end_time


def _get_next_setting(component):
    now = datetime.now()
    setting = component.time_program.get_next(now)

    start = datetime.now().replace(
        hour=setting.hour, minute=setting.minute, second=0, microsecond=0
    )
    abs_min = now.hour * 60 + now.minute

    if setting.absolute_minutes < abs_min:
        start + timedelta(days=1)

    setting.start = dt.as_local(start)
    return setting
