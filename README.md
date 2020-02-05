# vaillant-component

**Please note that this component is still in beta test, so I may do (unwanted) breaking changes.**

For the sake of (my) simplicity, this is a complete fork of the HA repository since the end goal is to have the component merged into HA repository.

Please download the vaillant folder [here](https://minhaskamal.github.io/DownGit/#/home?url=https://github.com/thomasgermain/home-assistant/tree/vaillant/homeassistant/components/vaillant)

There is still some work to do. I'm still thinking on what HA should do when changing temperature, hvac mode, etc. What to do in case of quick mode, quick_veto, etc. I try to reflect to behavior of the android application (except when it sounds stupid) as most as possible.
Ideas are welcome ! Don't hesitate to create issue to suggest something, it will be really appreciated.

and add this to your `configuration.yaml`

```yaml
vaillant:
  username: username
  password: password
```

You can also configure:
- `smartphoneid`, by default this `homeassistant`. The `smartphoneid` is used during the authentication process
- `quick_veto_duration` in some case, HA will create for you a quick veto, you can specify here the default duration in hours, default is 3 hours (like when you set a temperature on a room valve). It can be set from 0.5 to 24. **Please note de quick veto duration for a zone is configurable, it's 6 hours**
- `scan_interval`, by default this is 5 minutes

## Provided entities
- 1 water_heater entity, if any water heater: `water_heater.vaillant_<water heater id>`, basically `water_heater.vaillant_control_dhw`
- 1 climate entity per zone (expect if the zone is controlled by room) `climate.vaillant_<zone id>`
- 1 climate entity per room `climate.vaillant_<room name>`
- 1 binary_sensor entity `binary_sensor.vaillant_circulation` reflecting if the circulation is on or off
- 1 binary_sensor entity `climate.vaillant_<room name>_window` per room reflecting the state of the "open window" in a room (this is a feature of the vaillant API, if the temperature is going down pretty fast, the API assumes there is an open window and heating stops)
- 1 binary_sensor entity `climate.vaillant_<room name>_lock`per room reflecting if valves are "child locked" or not
- 1 binary_sensor entity `binary_sensor.vaillant_<sgtin>>_battery` reflecting battery level for each device (VR50, VR51) in the system
- 1 binary_sensor entity `binary_sensor.vaillant_<sgtin>>_battery` reflecting connectivity for each device (VR50, VR51) in the system
- 1 binary_sensor entity `binary_sensor.vaillant_system_update`to know if there is an update pending
- 1 binary_sensor entity `binary_sensor.vaillant_system_online` to know if the vr900/920 is connected to the internet
- 1 binary_sensor entity `binary_sensor.vaillant_<boiler model>` to know if there is an error at the boiler. **Some boiler does not provide this information, so entity won't be available.**
- 1 temperature sensor `sensor.vaillant_outdoor_temperature` for outdoor temperature
- 1 sensor for water `sensor.vaillant_boiler_pressure` pressure in boiler
- 1 temperature sensor ` sensor.vaillant_boiler_temperature` for water temperature in boiler
- 1 binary sensor `binary_sensor.vaillant_quick_mode` to know a quick mode is running on
- 1 binary sensor ` binary_sensor.vaillant_holiday` to know the holiday mode is on/off
- dynamic binary sensors if there are extra errors coming from the api (**not yet tested**) 


For the climate and water heater entities, you can also found 
- the 'real vaillant mode' running on (AUTO, MANUAL, DAY, etc)
- the next setting (DAY, NIGHT for a zone) or next target temperature for a room (when auto)
- when the current setting ends (when auto)

For the boiler error entity, you can also found 
- the last update (this is not the last HA update, this is the last time vaillant checks the boiler)
- the status code (these can be found in your documentation)
- the title (human readable description of the status code)

For the `binary_sensor.vaillant_quick_mode`, when on, you have the current quick mode name is available
For the `binary_sensor.vaillant_holiday`, when on, you have the start date, end date and temperature

## Provided services
- `vaillant.set_holiday_mode` to set the holiday mode (see services in HA ui to get the params)
- `vaillant.remove_holiday_mode` .. I guess you get it
- `vaillant.set_quick_mode` to set a quick mode
- `vaillant.remove_quick_mode` don't tell me you don't get it 
- `vaillant.set_quick_veto` to set a quick veto for a climate entity
- `vaillant.remove_quick_veto` to remove a quick veto for a climate entity

This will allow you to create some buttons in UI to activate/deactive quick mode or holiday mode with a single click


## Expected behavior

On **room** climate:
- Changing temperature while on MANUAL mode will simply change the target temperature
- Changing temperature while on other modes (included quick veto) will create a a quick veto with the selected temperature and configured `quick_veto_duration`
- Changing hvac mode to AUTO will set vaillant mode to AUTO (so it will follow the time program)
- Changing hvac mode to OFF will set vaillant mode to OFF
- if there is a quick mode (or holiday mode) impacting room, it will be removed upon change
- QM_SYSTEM_OFF and holiday mode will lead to hvac OFF

On **zone** climate:
- Changing temperature will lead to a quick veto with selected temperature for 6 hours (quick veto duration is not configurable for a zone)
- Changing hvac mode to AUTO will set vaillant mode to AUTO (so it will follow the time program)
- Changing hvac mode to OFF will set vaillant mode to OFF
- Changing hvac mode to HEAT will set vaillant mode to DAY
- Changing hvac mode to COOL will set vaillant mode to NIGHT
- if there is a quick mode (or holiday mode) impacting zone, it will be removed upon change
- QM_SYSTEM_OFF and holiday mode will lead to hvac OFF
- QM_ONE_DAY_AT_HOME will lead to hvac AUTO (but with the time program of the sunday)
- QM_PARTY -> HVAC_MODE_HEAT
- QM_VENTILATION_BOOST -> HVAC_MODE_FAN_ONLY
- ONE_DAY_AWAY -> hvac OFF 

## Todo's
- test from dynamic entity when there are errors coming from the API