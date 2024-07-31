# Install the systemd service
cp ./systemd/bme680-influxdb.service /etc/systemd/system
systemctl daemon-reload
systemctl start bme680-influxdb
systemctl enable bme680-influxdb