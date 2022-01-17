#!/usr/bin/env python3
"""
Sensor component Afvalwijzer
Author: Bram van Dartel - xirixiz
"""
import logging

from afvalwijzer.common.day_sensor_data import DaySensorData
from afvalwijzer.common.next_sensor_data import NextSensorData
from afvalwijzer.const.const import (
    CONF_DEFAULT_LABEL,
    CONF_EXCLUDE_LIST,
    CONF_ID,
    CONF_EXCLUDE_PICKUP_TODAY,
    CONF_POSTAL_CODE,
    CONF_COLLECTOR,
    CONF_STREET_NUMBER,
    CONF_SUFFIX,
    MIN_TIME_BETWEEN_UPDATES,
    PARALLEL_UPDATES,
    SCAN_INTERVAL,
    STARTUP_MESSAGE,
)
from afvalwijzer.collector.afvalwijzer import AfvalWijzer
from afvalwijzer.sensor_custom import CustomSensor
from afvalwijzer.sensor_provider import ProviderSensor

# import afvalwijzer.const.const as const


_LOGGER = logging.getLogger(__name__)

from functools import partial

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.helpers.config_validation as cv
from homeassistant.util import Throttle
import voluptuous as vol

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_collector.strip().lower(), default="mijnafvalwijzer"): cv.string,
        vol.Required(CONF_POSTAL_CODE.strip(), default="1234AB"): cv.string,
        vol.Required(CONF_STREET_NUMBER.strip(), default="5"): cv.string,
        vol.Optional(CONF_SUFFIX.strip(), default=""): cv.string,
        vol.Optional(CONF_EXCLUDE_PICKUP_TODAY.strip(), default="false"): cv.string,
        vol.Optional(CONF_DEFAULT_LABEL.strip(), default="Geen"): cv.string,
        vol.Optional(CONF_ID.strip().lower(), default=""): cv.string,
        vol.Optional(CONF_EXCLUDE_LIST.strip().lower(), default=""): cv.string,
    }
)

_LOGGER.info(STARTUP_MESSAGE)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    provider = config.get(CONF_COLLECTOR)
    postal_code = config.get(CONF_POSTAL_CODE)
    street_number = config.get(CONF_STREET_NUMBER)
    suffix = config.get(CONF_SUFFIX)
    exclude_pickup_today = config.get(CONF_EXCLUDE_PICKUP_TODAY)
    default_label = config.get(CONF_DEFAULT_LABEL)
    exclude_list = config.get(CONF_EXCLUDE_LIST)

    _LOGGER.debug("Afvalwijzer provider = %s", provider)
    _LOGGER.debug("Afvalwijzer zipcode = %s", postal_code)
    _LOGGER.debug("Afvalwijzer street_number = %s", street_number)

    try:
        afvalwijzer = await hass.async_add_executor_job(
            partial(
                AfvalWijzer,
                provider,
                postal_code,
                street_number,
                suffix,
                exclude_pickup_today,
                default_label,
                exclude_list,
            )
        )
    except ValueError as err:
        _LOGGER.error("Check afvalwijzer platform settings %s", err.args)
        raise

    fetch_afvalwijzer_data = AfvalwijzerData(config)

    waste_types_provider = afvalwijzer.waste_types_provider
    _LOGGER.debug("Generating waste_types_provider list = %s", waste_types_provider)
    waste_types_custom = afvalwijzer.waste_types_custom
    _LOGGER.debug("Generating waste_types_custom list = %s", waste_types_custom)

    entities = list()

    for waste_type in waste_types_provider:
        _LOGGER.debug("Adding sensor provider: %s", waste_type)
        entities.append(ProviderSensor(hass, waste_type, fetch_afvalwijzer_data, config))
    for waste_type in waste_types_custom:
        _LOGGER.debug("Adding sensor custom: %s", waste_type)
        entities.append(CustomSensor(hass, waste_type, fetch_afvalwijzer_data, config))

    _LOGGER.debug("Entities appended = %s", entities)
    async_add_entities(entities)


class AfvalwijzerData(object):
    def __init__(self, config):
        self.config = config

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        provider = self.config.get(CONF_COLLECTOR)
        postal_code = self.config.get(CONF_POSTAL_CODE)
        street_number = self.config.get(CONF_STREET_NUMBER)
        suffix = self.config.get(CONF_SUFFIX)
        exclude_pickup_today = self.config.get(CONF_EXCLUDE_PICKUP_TODAY)
        default_label = self.config.get(CONF_DEFAULT_LABEL)
        exclude_list = self.config.get(CONF_EXCLUDE_LIST)

        try:
            afvalwijzer = AfvalWijzer(
                provider,
                postal_code,
                street_number,
                suffix,
                exclude_pickup_today,
                default_label,
                exclude_list,
            )
        except ValueError as err:
            _LOGGER.error("Check afvalwijzer platform settings %s", err.args)
            raise

        # waste data provider update - with today
        try:
            self.waste_data_with_today = afvalwijzer.waste_data_with_today
        except ValueError as err:
            _LOGGER.error("Check waste_data_provider %s", err.args)
            self.waste_data_with_today = default_label
            raise

        # waste data provider update - without today
        try:
            self.waste_data_without_today = afvalwijzer.waste_data_without_today
        except ValueError as err:
            _LOGGER.error("Check waste_data_provider %s", err.args)
            self.waste_data_without_today = default_label
            raise

        # waste data custom update
        try:
            self.waste_data_custom = afvalwijzer.waste_data_custom
        except ValueError as err:
            _LOGGER.error("Check waste_data_custom %s", err.args)
            self.waste_data_custom = default_label
            raise
