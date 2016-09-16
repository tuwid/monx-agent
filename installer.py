#!/usr/bin/python

# importing some stuff
import os, subprocess

collector_directory = '/opt/data_collector/'
devnull = open(os.devnull,"w")


if not os.geteuid() == 0:
	print 'Script must be run as root'
	exit(1)
else:
	print "Root check OK"


packages_debian = ['cron', 'python']

# check packages if installed and running
for pack in packages_debian:
	retval = subprocess.call(["dpkg","-s",pack],stdout=devnull,stderr=subprocess.STDOUT)
	if retval != 0:
		print 'Package ' + pack + ' is not installed!'
		print 'Please install cron'
		exit(1)
	else:
		print 'Package ' + pack + ' is installed!'
		try:
			if len( os.popen("ps -aef | grep -i 'cron' | grep -v 'grep' | awk '{ print $3 }'" ).read().strip().split( '\n' ) ) >= 1:
				print 'Cron process seem running'
		except Exception, e:
			print 'Cron installed but not running apparently'
			print 'Proceeding anyway'
devnull.close()

# setting the environment
if not os.path.exists(collector_directory):
	os.makedirs(collector_directory)

data_collector_file = collector_directory + "data_collector.py"
print data_collector_file


os.system("cp data_collector.py " + data_collector_file)

os.chmod(data_collector_file, 0744)



# adding to cron
os.system("crontab -l > /tmp/cronlist")
os.system("echo '*/2 * * * *	" + data_collector_file + "' >> /tmp/cronlist")
os.system("crontab < /tmp/cronlist")
os.system("rm /tmp/cronlist")

print "\n Excellent"
print 'Data collector installed! You should be albe to see the data in the pannel in a minute or so'