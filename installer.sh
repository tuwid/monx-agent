#!/bin/bash

# Check if we're root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

if [ $# -eq 0 ]
  then
    echo "No arguments supplied"
    exit 1
fi

MONX_API_KEY=$1
# Get script
mkdir -p /opt/data_collector/

cat >/opt/data_collector/default.conf <<EOF
[settings]
api_key = $MONX_API_KEY
api_url = http://api.monx.me/api/servers/$MONX_API_KEY/statistics

EOF

# Checking python, most system have it except for latest Ubuntu versions
version=$(python -V 2>&1 | grep -Po '(?<=Python )(.+)')
if [[ -z "$version" ]]
then
    echo "No Python! -- Installing minimal python"
    test -e /usr/bin/apt && (apt -y update && apt install -y python-minimal net-tools)
fi

wget --no-check-certificate https://raw.githubusercontent.com/tuwid/monx-agent/master/data_collector.py \
    -O /opt/data_collector/data_collector.py

chmod 755 /opt/data_collector/data_collector.py

# Adding to cron
crontab -l | grep -v "data_collector" > /tmp/cronlist
echo '* * * * *       /opt/data_collector/data_collector.py > /dev/null 2>&1' >> /tmp/cronlist
crontab < /tmp/cronlist
rm -rf /tmp/cronlist

echo 'Excellent'
echo 'Monx Agent installed! You should be able to see the data in the panel in a minute'
