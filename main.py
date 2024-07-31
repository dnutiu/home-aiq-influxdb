import logging
import os
import time

import bme680
from bme680.constants import (
    I2C_ADDR_PRIMARY,
    OS_2X,
    OS_4X,
    OS_8X,
    FILTER_SIZE_3,
    ENABLE_GAS_MEAS,
)
from influxdb_client.client.influxdb_client import InfluxDBClient
from influxdb_client.client.write.point import Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pms5003 import PMS5003


class Program:
    def __init__(self):
        # envs
        self._delay = int(os.getenv("DELAY", default="15"))
        self._influx_db_token = os.getenv("INFLUX_DB_TOKEN")
        self._influx_db_org = os.getenv("INFLUX_DB_ORGANIZATION", "NucuLabs")
        self._influx_db_url = os.getenv("INFLUX_DB_URL", "http://nas.nuculabs.com:8086")
        self._tag_location = os.getenv("TAG_LOCATION", "Terasa")
        self._bucket_name = os.getenv("BUCKET_NAME", "nuculabs")

        # init
        self._init_bme680()
        self._init_pms50003()

        self.influxdb_client = InfluxDBClient(
            url=self._influx_db_url,
            token=self._influx_db_token,
            org=self._influx_db_org,
        )
        self.influxdb_write_api = self.influxdb_client.write_api(
            write_options=SYNCHRONOUS
        )

    def run(self):
        while True:
            self._read_bme680()
            self._read_pms5003()
            time.sleep(self._delay)

    def _init_bme680(self):
        self.temperature_sensor = bme680.BME680(I2C_ADDR_PRIMARY)
        self.temperature_sensor.set_humidity_oversample(OS_2X)
        self.temperature_sensor.set_pressure_oversample(OS_4X)
        self.temperature_sensor.set_temperature_oversample(OS_8X)
        self.temperature_sensor.set_filter(FILTER_SIZE_3)
        self.temperature_sensor.set_gas_status(ENABLE_GAS_MEAS)
        self.temperature_sensor.set_gas_heater_temperature(320)
        self.temperature_sensor.set_gas_heater_duration(150)
        self.temperature_sensor.select_gas_heater_profile(0)

    def _init_pms50003(self):
        self.air_quality_sensor = PMS5003(
            device="/dev/ttyUSB0",
            baudrate="9600",
            pin_enable="GPIO22",
            pin_reset="GPIO22",
        )

    def _read_pms5003(self):
        try:
            data = self.air_quality_sensor.read()

            pms5003_pm_ug_per_m3_1 = data.pm_ug_per_m3(1.0)
            pms5003_pm_ug_per_m3_2 = data.pm_ug_per_m3(2.5)
            pms5003_pm_ug_per_m3_10 = data.pm_ug_per_m3(10)

            logging.info(
                f"AirQuality = 1mg: {pms5003_pm_ug_per_m3_1}; 2.5mg: {pms5003_pm_ug_per_m3_2}: 10mg: {pms5003_pm_ug_per_m3_10}"
            )
            point = (
                Point("pms5003-measurement")
                .tag("location", self._tag_location)
                .field("ug-per-m3-1", pms5003_pm_ug_per_m3_1)
                .field("ug-per-m3-2-5", pms5003_pm_ug_per_m3_2)
                .field("ug-per-m3-10", pms5003_pm_ug_per_m3_10)
            )
            self.influxdb_write_api.write(bucket=self._bucket_name, record=point)
        except Exception as e:
            logging.error(f"Failed to read data due to exception: {str(e)}")

    def _read_bme680(self):
        try:
            if self.temperature_sensor.get_sensor_data():
                temperature = self.temperature_sensor.data.temperature
                humidity = self.temperature_sensor.data.humidity
                pressure = self.temperature_sensor.data.pressure
                gas = self.temperature_sensor.data.gas_resistance

                logging.info(
                    f"BME680 = T: {temperature}; H: {humidity}: P: {pressure}; G: {gas}"
                )
                point = (
                    Point("bme680-measurement")
                    .tag("location", self._tag_location)
                    .field("temperature", temperature)
                    .field("humidity", humidity)
                    .field("pressure", pressure)
                    .field("gas", gas)
                )
                self.influxdb_write_api.write(bucket=self._bucket_name, record=point)
        except Exception as e:
            logging.error(f"Failed to read data due to exception: {str(e)}")


def main():
    logging.basicConfig(level="INFO")
    program = Program()
    program.run()


if __name__ == "__main__":
    main()
