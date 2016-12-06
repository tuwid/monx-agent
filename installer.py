#!/usr/bin/python

# importing some stuff
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
	print "Root check OK"

if len( os.popen("ps -aef | grep -i ' cron' | grep -v 'grep' | awk '{ print $3 }' | head -1" ).read().strip().split( '\n' ) ) >= 1:
	print 'Cron process seem running'
else:
	print 'Unable to find cron, please install cron first'
	exit(1)

if os.popen("python -V" ).read().strip().find("Python 2") == -1:
	print 'Python is installed'
else:
	print 'Unable to find python 2.6/2.7, please install python 2.6/2.7 first'
	exit(1)

# setting the environment
if not os.path.exists(collector_directory):
	os.makedirs(collector_directory)

cfgfile = open(collector_directory + 'default.conf','w')

Config.add_section('default')
Config.set('default','API_KEY',api_key)
Config.set('default','API_URL','http://monx.me/api/v1/store-data/')
Config.write(cfgfile)

cfgfile.close()

data_collector_file = collector_directory + "data_collector.py"
print data_collector_file

urllib.urlretrieve ("https://raw.githubusercontent.com/tuwid/monx-agent/master/data_collector.py", data_collector_file)

os.chmod(data_collector_file, 0744)

# adding to cron
os.system("crontab -l > /tmp/cronlist")
os.system("echo '*/2 * * * *	" + data_collector_file + "' >> /tmp/cronlist")
os.system("crontab < /tmp/cronlist")
os.system("rm /tmp/cronlist")

print "\n Excellent"
print 'Data collector installed! You should be albe to see the data in the pannel in a minute or so'