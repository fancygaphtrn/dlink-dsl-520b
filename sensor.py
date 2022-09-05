"""
Support for reading Dlink dsl-520b DSL modem data/

configuration.yaml

sensor:
  - platform: dsl520b
    host: 192.168.1.1
    port: 80
    username: USERID
    password: PASSWORD
    scan_interval: 3000
"""
import logging
import requests
import base64
import re
from datetime import timedelta
import homeassistant.util.dt as dt_util
import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA, ENTITY_ID_FORMAT
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
        CONF_USERNAME, CONF_PASSWORD, CONF_HOST, CONF_PORT,
        CONF_RESOURCES
    )
from homeassistant.util import Throttle
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

BASE_URL = 'http://{0}:{1}{2}'
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=10)

SENSOR_PREFIX = 'dsl520b'
SENSOR_TYPES = {
    'upload': ['Upload', 'kbps', 'mdi:arrow-up'],
    'download': ['Download', 'kbps', 'mdi:arrow-down'],
    'dsl_status': ['DSL Status', None, 'mdi:check']
}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_HOST): cv.string,
    vol.Required(CONF_USERNAME): cv.string,
    vol.Required(CONF_PASSWORD): cv.string,
    vol.Required(CONF_RESOURCES, default=[]):
    vol.All(cv.ensure_list, [vol.In(SENSOR_TYPES)]),
    vol.Optional(CONF_PORT, default=80): cv.positive_int,
})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Setup the dsl520b sensors."""
    _LOGGER.info("DSL-520b starting...")

    host = config.get(CONF_HOST)
    port = config.get(CONF_PORT)
    username = config.get(CONF_USERNAME)
    password = config.get(CONF_PASSWORD)

    try:
        data = dsl520bData(host, port, username, password)
    except RunTimeError:
        _LOGGER.error("dsl520b: Unable to connect fetch data from dsl520b %s:%s",
                      host, port)
        return False

    entities = []

    for resource in SENSOR_TYPES:
        sensor_type = resource.lower()

        entities.append(dsl520bSensor(data, sensor_type))
    
    _LOGGER.debug("dsl520b: entities = %s", entities)
    add_entities(entities)


# pylint: disable=abstract-method
class dsl520bData(object):
    """Representation of a dsl520b."""

    def __init__(self, host, port, username, password):
        """Initialize the dsl520b."""
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self.data = None
        self.auth = self.get_base64_cookie_string()
        self.referer = 'http://{}'.format(self._host)
        self.dataurl = BASE_URL.format(
                    self._host, self._port,
                    '/statsadsl.html'
        )
        
    def get_base64_cookie_string(self):
        username_password = '{}:{}'.format(self._username, self._password)
        b64_encoded_username_password = base64.b64encode(
            username_password.encode('ascii')
        ).decode('ascii')
        return 'Basic {}'.format(b64_encoded_username_password)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """Update the data from the dsl520b."""

        try:
            _LOGGER.debug("dsl520b: update start %s", self.dataurl)
        
            resp = requests.get(
                self.dataurl,
                headers={'referer': self.referer, 'Authorization': self.auth},
                timeout=4)

            if resp.status_code == 200:
                self.data = resp.text
                _LOGGER.debug("dsl520b  data success: Data = %s", self.data)

            else:
                _LOGGER.debug("dsl520b: data failed  Status %i", resp.status_code)
                self.data = ""

        except requests.exceptions.Timeout as e:
            _LOGGER.error("dsl520b: timeout %s", e)
            self.data = ""

        except requests.exceptions.ConnectionError as e:
            _LOGGER.error("dsl520b: No route to device %s %s", dataurl, e)
            self.data = ""

class dsl520bSensor(Entity):
    """Representation of a dsl520b sensor from the dsl520b."""

    def __init__(self, data, sensor_type):
        """Initialize the sensor."""
        self.data = data
        self.type = sensor_type
        self.entity_id = ENTITY_ID_FORMAT.format(SENSOR_PREFIX + "_" + sensor_type)
        self._name = SENSOR_TYPES[self.type][0]
        self._unit_of_measurement = SENSOR_TYPES[self.type][1]
        self._icon = SENSOR_TYPES[self.type][2]
        self._state = None
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        if self._unit_of_measurement == None:
            return
        return self._unit_of_measurement

    def update(self):
        """Get the latest data and use it to update our sensor state."""
        self.data.update()
        _LOGGER.debug("dsl520b: type = %s", self.type)

        """['CONNECTED', '', 'IPoE via DHCP', '', 'N/A', '', 'N/A', 'N/A', 'N/A', '10M:40S', '', '15354', '15595', '', '26M:54S', '', '1500', '', '1460', '', '71.219.123.120', '', '205.171.2.65', '', '205.171.3.65', '', '71.219.123.254', '', '25M:42S', '', 'CONNECTED', '', '0.604', '', '1.792', '', '255.255.255.0', '', 'Disabled', '', 'N/A', '', 'N/A', '', 'N/A', '', '64', '', 'N/A', '', '', '', '', '', 'N/A\r\n']"""
        if self.data.data != None:
            
            if self.type == 'upload':
                pattern = re.compile('<td class=\'hd\'>Rate \(Kbps\):</td>\n                  <td>(\d+)&nbsp;</td>\n                  <td>(\d+)&nbsp;</td>')
                upload = pattern.search(self.data.data)
                if upload == None:
                    self._state = '0'
                else:
                    self._state = upload.group(2)
            if self.type == 'download':
                pattern = re.compile('<td class=\'hd\'>Rate \(Kbps\):</td>\n                  <td>(\d+)&nbsp;</td>\n                  <td>(\d+)&nbsp;</td>')
                download = pattern.search(self.data.data)
                if download == None:
                    self._state = '0'
                else:
                    self._state = download.group(1)
            if self.type == 'dsl_status':
                pattern = re.compile('<td colspan=\"2\" class=\'hd\'>Status:</td>\n                  <td>(.+)&nbsp;</td>')
                dsl_status = pattern.search(self.data.data)
                if dsl_status == None:
                    self._state = 'N/A'
                else:
                    self._state = dsl_status.group(1)
