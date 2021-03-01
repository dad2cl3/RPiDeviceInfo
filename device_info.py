from datetime import datetime
from math import floor

from gpiozero import DiskUsage, PingServer
from psutil import cpu_percent, net_if_addrs, sensors_temperatures, virtual_memory
from pytz import timezone
from socket import gethostname
from time import sleep, time
import json, paho.mqtt.publish as publish


def network_status():
    ping = PingServer(config['ping_target'])
    return ping.value


def get_uptime():
    with open('/proc/uptime', 'r') as uptime_file:
        uptime_seconds = float(uptime_file.readline().split()[0])

    day_seconds = 24 * 60 * 60
    hour_seconds = 60 * 60
    minute_seconds = 60
<<<<<<< HEAD
    # week_seconds = day_seconds * 7 # possible addition
=======
>>>>>>> e94a5ca9609000be63375b99e107969d49d6627e

    if uptime_seconds > day_seconds:
        days = floor(uptime_seconds/day_seconds)
        uptime_seconds -= days * day_seconds
    else:
        days = 0

    if uptime_seconds > hour_seconds:
        # hours = floor((uptime_seconds - (days * day_seconds))/hour_seconds)
        hours = floor(uptime_seconds/hour_seconds)
        uptime_seconds -= hours * hour_seconds
    else:
        hours = 0

    if uptime_seconds > minute_seconds:
        minutes = floor(uptime_seconds/minute_seconds)
        uptime_seconds -= minutes * minute_seconds
    else:
        minutes = 0

    uptime = {
        'days': days,
        'hours': hours,
        'minutes': minutes,
        'seconds': round(uptime_seconds, 2)
    }

    return uptime


def mqtt_publish_single(message):

    try:
        publish.single(
            topic='{0}/{1}/telemetry/'.format(config['mqtt']['topic_prefix'], hostname),
            payload=json.dumps(message),
            hostname=config['mqtt']['address'],
            port=config['mqtt']['port']
        )
    except ConnectionError as e:
        print(e)


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

    uptime = get_uptime()

    sensors = sensors_temperatures()
    for name, entries in sensors.items():
        if name == 'cpu_thermal':
            temp = round(entries[0].current, 1)

    addresses = net_if_addrs()
    for name, entries in addresses.items():
        if name == 'wlan0':
            address = entries[0].address

    cpu_load = cpu_percent(interval=1)
    mem_load = virtual_memory().percent
    disk_usage = round(DiskUsage().usage, 1)

    print('CPU Temperature {0}'.format(temp))
    print('CPU Load Average {0}'.format(cpu_load))
    print('Memory Load Average {0}'.format(mem_load))
    print('Disk Usage {0}'.format(disk_usage))
    print('Uptime {0}'.format(uptime))

    if network_status():
        mqtt_publish_single({
            'timestamp': now_ts,
            'hostname': hostname,
            'address': address,
            'uptime': uptime,
            'temperature': temp,
            'cpu_load': cpu_load,
            'memory_load': mem_load,
            'disk_usage': disk_usage
        })

    sleep(60)
