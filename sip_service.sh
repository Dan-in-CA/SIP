#! /bin/bash
###
#install sip.sevice for systemd
###

install_location=$(pwd)
python3 -m venv --system-site-packages ${install_location}/.venv

echo ===== Creating and installing SystemD service =====
cat << EOF > /tmp/sip.service
#Service for SIP running on a SystemD service
#
[Unit]
Description=SIP for Python3
After=syslog.target network.target network-online.target
Wants=network-online.target

[Service]
Environment="PATH=/${install_location}/.venv/bin:${PATH}"
ExecStart=/${install_location}/.venv/bin/python3 -u ${install_location}/sip.py
Restart=on-abort
WorkingDirectory=${install_location}
SyslogIdentifier=sip

[Install]
WantedBy=multi-user.target
EOF

sudo cp /tmp/sip.service /etc/systemd/system/
sudo systemctl enable sip.service
sudo git config --system --add safe.directory ${install_location}
