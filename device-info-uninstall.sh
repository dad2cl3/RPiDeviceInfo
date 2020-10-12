# stop the linux service
sudo systemctl stop device-info.service

# disable the linux service
sudo systemctl disable device-info.service

# reload the systemd daemon
# NOTE: any change to the local project service file will require a reload
sudo systemctl daemon-reload

# remove the local files
sudo rm -rf /var/pyapps/device
