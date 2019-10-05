#!/bin/bash

openssl req -new -newkey rsa:4096 -x509 -sha256 -days 3650 -nodes -out SIP.crt -keyout SIP.key