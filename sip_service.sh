#! /bin/bash
###
#install sip.sevice for systemd
###

install_location=$(pwd)

echo ===== Creating and installing SystemD service =====
cat << EOF > /tmp/sip.service
#Service for SIP running on a SystemD service
#
[Unit]
Description=SIP for Python3
After=syslog.target network.target

[Service]
ExecStart=/usr/bin/python3 -u ${install_location}/sip.py
Restart=on-abort
WorkingDirectory=${install_location}
SyslogIdentifier=sip

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/sip.service /etc/systemd/system/
sudo systemctl enable sip.service