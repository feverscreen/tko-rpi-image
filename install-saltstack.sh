#!/bin/bash

if [[ $EUID -ne 0 ]]; then
    echo "Please run as root."
    exit 1
fi

# Wait for internet connection to come up
echo "waiting for internet connection..."
for attempt in `seq 10`; do
    ping -q -w 5 -c 1 1.1.1.1 > /dev/null && break
    sleep 1
done
echo "internet connection available"

set -e -x

# Install Salt minion software
wget -O - https://repo.saltstack.com/py3/debian/10/armhf/3001/SALTSTACK-GPG-KEY.pub | sudo apt-key add -
echo "deb http://repo.saltstack.com/py3/debian/10/armhf/3001 buster main" > /etc/apt/sources.list.d/saltstack.list
apt-get update
apt-get install -y salt-minion
systemctl stop salt-minion
