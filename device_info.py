from datetime import datetime
from gpiozero import DiskUsage, PingServer
from psutil import cpu_percent, sensors_temperatures, virtual_memory
from pytz import timezone
from socket import gethostname
from time import sleep
import json, paho.mqtt.publish as publish


def network_status():
    ping = PingServer(config['ping_target'])
    return ping.value


def mqtt_publish_single(message):

    publish.single(
        topic='{0}/telemetry/'.format(hostname),
        payload=json.dumps(message),
        hostname=config['mqtt']['address'],
        port=config['mqtt']['port']
    )


# load the config
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# set the timezone
tz = timezone(config['timezone'])
# set the date time format for telemetry readings
date_time_format = config['date_time_format']
# get the hostname for telemetry readings
hostname = gethostname()

while True:
    now = tz.localize(datetime.now())
    now_ts = now.strftime(date_time_format)

    sensors = sensors_temperatures()
    for name, entries in sensors.items():
        if name == 'cpu_thermal':
            temp = entries[0].current

    cpu_load = cpu_percent(interval=1)
    mem_load = virtual_memory().percent
    disk_usage = DiskUsage().usage

    print('CPU Temperature {0}'.format(temp))
    print('CPU Load Average {0}'.format(cpu_load))
    print('Memory Load Average {0}'.format(mem_load))
    print('Disk Usage {0}'.format(disk_usage))

    if network_status():
        mqtt_publish_single({
            'timestamp': now_ts,
            'hostname': hostname,
            'temperature': temp,
            'cpu_load': cpu_load,
            'memory_load': mem_load,
            'disk_usage': disk_usage
        })

    sleep(60)
