#!/usr/bin/python

import os, subprocess, urllib, sys, ConfigParser

Config = ConfigParser.ConfigParser()

if(len(sys.argv) == 1):
	print 'No API key specified'
	exit(1)
else:
	print 'API Key set '+ str(sys.argv[1])
	api_key = str(sys.argv[1])	

collector_directory = '/opt/data_collector/'

if not os.geteuid() == 0:
	print 'Script must be run as root'
	exit(1)
else:
	print 'Root check OK'

if not os.path.exists(collector_directory):
	os.makedirs(collector_directory)

cfgfile = open(collector_directory + 'default.conf','w')

Config.add_section('settings')
Config.set('settings','API_KEY',api_key)
Config.set('settings','API_URL','http://monx.me/api/v1/store-data/')
Config.write(cfgfile)

cfgfile.close()

data_collector_file = collector_directory + 'data_collector.py'
print 'Setting' + data_collector_file

urllib.urlretrieve ('https://raw.githubusercontent.com/tuwid/monx-agent/master/data_collector.py', data_collector_file)

os.chmod(data_collector_file, 0744)

# adding to cron
os.system('crontab -l > /tmp/cronlist')
os.system("echo '*/2 * * * *	" + data_collector_file + " > /dev/null 2>&1' >> /tmp/cronlist")
os.system('crontab < /tmp/cronlist')
os.system('rm /tmp/cronlist')

print "\n Excellent"
print 'Monx Agent installed! You should be albe to see the data in the panel in a minute or so'