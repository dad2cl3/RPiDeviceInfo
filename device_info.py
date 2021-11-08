from datetime import datetime
from math import floor

from gpiozero import DiskUsage, PingServer
from psutil import cpu_percent, net_if_addrs, sensors_temperatures, virtual_memory
import upnpy
from pytz import timezone
from socket import gethostname
from time import sleep, time
import json, paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import subprocess
import os, re, sys
from vcgencmd import Vcgencmd

sys.path.append('./')


# MQTT callbacks
def on_connect(client, userdata, flags, rc):
    print('MQTT broker connected...')
    topic = '{0}/{1}'.format(hostname, config['mqtt']['topic'])
    # client.subscribe(config['mqtt']['topic'], qos=config['mqtt']['qos'])
    client.subscribe(topic, qos=config['mqtt']['qos'])


def on_disconnect(client, userdata, rc):
    print('MQTT broker disconnected...')


def on_subscribe(client, userdata, mid, granted_qos):
    print('MQTT topic subscribed...')


def on_message(client, userdata, msg):
    print('Message recieved...')

    # expected message format
    # {
    #     "command": "reboot",
    #     "options": [
    #         "now"
    #     ]
    # }

    print(msg.payload.decode('utf-8'))
    cmd_array = ['sudo']
    cmd_array.extend(msg.payload.split())

    output = subprocess.run(cmd_array, capture_output=True)
    output_payload = output.stdout.decode('utf-8')
    print(output_payload)

    mqtt_publish_single('PiDesktop/remote/command/response', output_payload)

    # subprocess.run(['sudo', 'systemctl', 'restart', 'device-info'])


def network_status():
    ping = PingServer(config['ping_target'])
    return ping.value


def get_device_type():
    with open("/proc/device-tree/model") as device_file:
        device_type = device_file.read()

    return device_type


def get_uptime():
    with open('/proc/uptime', 'r') as uptime_file:
        uptime_seconds = float(uptime_file.readline().split()[0])

    day_seconds = 24 * 60 * 60
    hour_seconds = 60 * 60
    minute_seconds = 60
    # week_seconds = day_seconds * 7 # possible addition

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


def get_cpu_throttle():
    definitions = {
        '0': 'Under-voltage detected',
        '1': 'ARM frequency capped',
        '2': 'Currently throttled',
        '3': 'Soft temperature limit active',
        '16': 'Under-voltage has occurred',
        '17': 'ARM frequency capping has occurred',
        '18': 'Throttling has occurred',
        '19': 'Soft temperature limit has occurred'
    }

    vcgm = Vcgencmd()
    throttle_state = vcgm.get_throttled()
    throttle_states = []

    for bit in throttle_state['breakdown']:
        if throttle_state['breakdown'][bit]:
            throttle_states.append(definitions[bit])

    return throttle_states


def mqtt_publish_single(topic, message):

    try:
        publish.single(
            # topic='{0}/{1}/telemetry/'.format(config['mqtt']['topic_prefix'], hostname),
            topic=topic,
            payload=json.dumps(message),
            hostname=config['mqtt']['address'],
            port=config['mqtt']['port']
        )
    except ConnectionError as e:
        print(e)
    except OSError as oe:
        print(oe)


def get_external_ip():
    try:
        upnp = upnpy.UPnP()
        devices = upnp.discover()
        device = upnp.get_igd()

        service = device.WANIPConn1

        addr = service.GetExternalIPAddress()

        return addr['NewExternalIPAddress']
    except Exception as e:
        return


def get_service_status():
    status_array = []

    services = config['services']

    for service in services:
        cmd_array = ['sudo', 'systemctl', 'is-active', service]
        status = subprocess.run(cmd_array, capture_output=True)
        status_payload = status.stdout.decode('utf8')

        status_array.append({service: status_payload})

    return status_array


# load the config
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# set the timezone
tz = timezone(config['timezone'])
# set the date time format for telemetry readings
date_time_format = config['date_time_format']
# get the hostname for telemetry readings
hostname = gethostname()

# compile regex for ip address
regex = re.compile('\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}')

# setup the MQTT client
client = mqtt.Client(hostname + "Service")
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_subscribe = on_subscribe
client.on_message = on_message

client.connect(
    host=config['mqtt']['address'],
    port=config['mqtt']['port']
)
# start the MQTT client loop
client.loop_start()

try:
    # reset the Blynk reboot button following boot
    topic = '{0}/{1}/{2}'.format(hostname, config['mqtt']['topic'], 'reset')
    mqtt_publish_single(topic, 0)

    # create MQTT topic
    topic = '{0}/{1}/telemetry/'.format(config['mqtt']['topic_prefix'], hostname)

    while True:
        now = tz.localize(datetime.now())
        now_ts = now.strftime(date_time_format)

        device_type = get_device_type()

        uptime = get_uptime()

        sensors = sensors_temperatures()
        for name, entries in sensors.items():
            if name == 'cpu_thermal':
                temp = round(entries[0].current, 1)

        # get local network IP address
        addresses = net_if_addrs()
        for name, entries in addresses.items():
            ip_addr = entries[0].address

            if not ip_addr == '127.0.0.1':
                if re.match(regex, ip_addr) and name in ['eth0', 'wlan0']:
                    # print('{0} - {1}'.format(name, address))
                    address = ip_addr
            # if name == 'wlan0':
                # address = entries[0].address

        # get gateway IP address
        gateway_ip = get_external_ip()

        cpu_load = cpu_percent(interval=1)
        mem_load = virtual_memory().percent
        disk_usage = round(DiskUsage().usage, 1)

        # get CPU throttle status
        throttle_states = get_cpu_throttle()
        throttle_status = ''
        if len(throttle_states) > 0:
            for throttle_state in throttle_states:
                throttle_status += '[' + now_ts + '] ' + throttle_state + '\n'
        else:
            throttle_status = '[' + now_ts + '] ' + 'CPU not throttled'

        print('Device Type {0}'.format(device_type))
        print('CPU Temperature {0}'.format(temp))
        print('CPU Load Average {0}'.format(cpu_load))
        print('Memory Load Average {0}'.format(mem_load))
        print('Disk Usage {0}'.format(disk_usage))
        print('CPU Throttle {0}'.format(throttle_status))
        print('Uptime {0}'.format(uptime))
        print('IP Address {0}'.format(address))
        print('Gateway Address {0}'.format(gateway_ip))

        # get service status
        service_status = []

        if 'services' in config:
            if len(config['services']) > 0:
                service_status = get_service_status()

        print('Service status {0}'.format(service_status))

        if network_status():
            if gateway_ip:
                payload = {
                    'timestamp': now_ts,
                    'device_type': device_type,
                    'hostname': hostname,
                    'address': address,
                    'gateway': gateway_ip,
                    'uptime': uptime,
                    'temperature': temp,
                    'cpu_load': cpu_load,
                    'memory_load': mem_load,
                    'disk_usage': disk_usage,
                    'cpu_throttle': throttle_status,
                    'service_status': service_status
                }
            else:
                payload = {
                    'timestamp': now_ts,
                    'device_type': device_type,
                    'hostname': hostname,
                    'address': address,
                    'uptime': uptime,
                    'temperature': temp,
                    'cpu_load': cpu_load,
                    'memory_load': mem_load,
                    'disk_usage': disk_usage,
                    'cpu_throttle': throttle_status,
                    'service_status': service_status
                }

            mqtt_publish_single(topic, payload)

        sleep(60)
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()