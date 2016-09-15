#!/usr/bin/python

# importing some stuff
import os, subprocess
import calendar
import urllib2
import time

collector_directory = '/opt/data_collector/'
devnull = open(os.devnull,"w")

timenow = calendar.timegm(time.gmtime())

if not os.geteuid() == 0:
	print 'Script must be run as root'
	exit(1)
else:
	print "Root check OK"


packages_debian = ['cron']

# check packages if installed and running
for pack in packages_debian:
	retval = subprocess.call(["dpkg","-s",pack],stdout=devnull,stderr=subprocess.STDOUT)
	devnull.close()
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

# setting the environment
if not os.path.exists(collector_directory):
	os.makedirs(collector_directory)



# # getting data collector from the webz
# url = "https://raw.github.com/nodequery/nq-agent/master/nq-agent.sh"

# data_collector_file = collector_directory + url.split('/')[-1]
data_collector_file = '/home/tarak/Dropbox/data_collector/monx-agent/data_collector.py'
# # TODO: skip certificate 
# u = urllib2.urlopen(url)
# f = open(data_collector_file, 'wb')
# meta = u.info()
# file_size = int(meta.getheaders("Content-Length")[0])
# print "Downloading: %s Bytes: %s" % (data_collector_file, file_size)

# file_size_dl = 0
# block_sz = 8192
# while True:
#     buffer = u.read(block_sz)
#     if not buffer:
#         break

#     file_size_dl += len(buffer)
#     f.write(buffer)
#     status = r"%10d  [%3.2f%%]" % (file_size_dl, file_size_dl * 100. / file_size)
#     status = status + chr(8)*(len(status)+1)
#     print status,

# f.close()

# setting the good stuff
os.chmod(data_collector_file, 0744)


# adding to cron
os.system("crontab -l > /tmp/cronlist")
os.system("echo '*/2 * * * *	" + data_collector_file + "' >> /tmp/cronlist")
os.system("crontab < /tmp/cronlist")
os.system("rm /tmp/cronlist")

print "\n Excellent"
print 'Data collector installed! You should be albe to see the data in the pannel in a minute or so'