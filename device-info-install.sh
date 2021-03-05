# create symlink from local project service file to systemd
sudo ln -sf /var/pyapps/RPiDeviceInfo/device-info.service /etc/systemd/system/device-info.service

# reload the systemd daemon
# NOTE: any change to the local project service file will require a reload
sudo systemctl daemon-reload

# enable the linux service
sudo systemctl enable device-info.service

# start the linux service
sudo systemctl start device-info.service
