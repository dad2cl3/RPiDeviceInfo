# RPiDeviceInfo
Basic Linux service to monitor and publish basic Raspberry Pi device telemetry via MQTT.

### How It Works
The Python script runs as a systemd service and utilizes the [psutil](https://psutil.readthedocs.io/en/latest/) Python library to collect device data from the Raspberry Pi including CPU temperature, CPU load, and memory utilization. Telemetry data is published to an MQTT server utilizing the [Eclipse Paho MQTT](http://www.eclipse.org/paho/) Python library.

**Please note:** The script does assume an MQTT server is listening at the specified address and port in the function *mqtt_publish_single*. [Eclipse Mosquitto](https://mosquitto.org/) runs really well on Raspberry Pi if you are in need of setting up your own.

### Installation
The repository includes an installation script that assumes several steps have been completed:

1. The Raspberry Pi has python3 and pip3 pre-installed and the superuser has installed virtualenv.
    1. sudo pip3 install virtualenv --upgrade
2. The pi user has created the directories necessary to support the path /var/pyapps/device
    1. mkdir /var/pyapps
    2. mkdir /var/pyapps/device 
3. The pi user has cloned the repository to the folder /var/pyapps/device
    1. git clone https://github.com/dad2cl3/RPiDeviceInfo.git .
4. The pi user has created a virtual environment titled "venv" at the path /var/pyapps/device/venv
    1. cd /var/pyapps/device
    2. virtualenv venv
5. The pi user has activated the virtual environment created in step 4.
    1. cd /var/pyapps/device
    2. source venv/bin/activate
6. The pi user has installed the necessary dependencies utilizing pip
    1. pip3 install -r requirements.txt --upgrade
7. The pi user has made the Korn shell script executable after cloning
    1. chmod +x device-info-install.sh

Once those steps are complete, it's as simple as executing the Korn shell script:

`(venv) pi@PiDesktop:/var/pyapps/device $ ./device-info-install.sh`

The Korn shell script does the following:
1. Creates symlink /etc/systemd/system/device-info.service to the local service file /var/pyapps/device/device-info.service
2. Reloads the systemd daemon in order to recognize the new service file
3. Enables the new service within systemd
4. Starts the new service within systemd

### Testing
The easiest way to test the service is to install an MQTT client of your choice. The Raspberry Pi package mosquitto-clients can be installed as follows:
`pi@PiDesktop:~ $ sudo apt install mosquitto-clients -y`

Should you choose to utilize the mosquitto-clients package on a Raspberry Pi, the command to listen to messages from the service is as follows:

`pi@PiDesktop:~ $ mosquitto_sub -h localhost -t PiDesktop/# -q 1`

where the `-h` switch is followed by the address of your MQTT server and the `-t` switch is followed by the hostname of the Raspberry Pi where the service is running.

The messages published by the service are in JSON format:
```
{
    "timestamp": "2020-10-12 16-38-14 -0400",
    "hostname": "PiDesktop",
    "temperature": 53.556,
    "cpu_load": 4.0,
    "memory_load": 15.3
}
```

### Removal
The Korn shell script, *device-info-uninstall.sh*, will remove the service and code from your Raspberry Pi. It assumes the following:
1. The pi user has made the Korn shell script executable after cloning
    1.     1. chmod +x device-info-uninstall.sh

Once those steps are complete, it's as simple as executing the Korn shell script:

`(venv) pi@PiDesktop:/var/pyapps/device $ ./device-info-uninstall.sh`