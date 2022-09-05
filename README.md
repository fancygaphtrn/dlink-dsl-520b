# dlink-dsl-520b
Home assistant custom component to pull stats from a Dlink DSL-520b

### Getting started

* Add sensor.py, __init__.py and manifest.json to the Home Assistant config\custom_components\dsl520b directory

#### Home Assistant Example

```
configuration.yaml

sensor:
  - platform: dsl520b
    host: <Hostname/IP address of DSL modem>
    port: 80
    username: PORTAL_LOGIN
    password: PORTAL_PASSWORD
    scan_interval: 300
```

```
Creates the following sensors in Home Assistant

sensor.dsl520b_download
sensor.dsl520b_upload
sensor.dsl520b_dsl_status
```
