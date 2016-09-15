#!/usr/bin/python

# importing some stuff
# from urllib2 import Request, urlopen, URLError, HTTPError
# from socket import error as SocketError
import requests
import os, subprocess
import platform
# import urllib2
import calendar
import time


data = {}


with open('/proc/uptime', 'r') as f:
	data['uptime'] = f.readline().rstrip().split()[0]

data['number_of_logins'] = len(subprocess.check_output("who").rstrip().split("\n"))

# with threads , the number is lower by just getting the procs
data['number_of_processes'] = len(subprocess.Popen(['ps', 'ax'], stdout=subprocess.PIPE).communicate()[0].rstrip().split("\n"))

with open('/proc/loadavg', 'r') as f:
	data['load'] = f.readline().rstrip().split()

with open('/proc/meminfo', 'r') as f:
	meminfo = f.readlines()

for memi in meminfo:
	temp = memi.rstrip().split(': ')
	if (temp[0] == 'MemTotal'):
		data['memtotal'] = temp[1].strip()
	if (temp[0] == 'MemFree'):
		data['memfree'] = temp[1].strip()
	if (temp[0] == 'MemAvailable'):
		data['memavailable'] = temp[1].strip()
	if (temp[0] == 'Cached'):
		data['memcached'] = temp[1].strip()
	if (temp[0] == 'SwapTotal'):
		data['memswaptotal'] = temp[1].strip()
	if (temp[0] == 'SwapFree'):
		data['memswapfree'] = temp[1].strip()


connection_list = subprocess.Popen(['netstat', '-tun'], stdout=subprocess.PIPE).communicate()[0].rstrip()
data['connection_list'] = connection_list.split("\n",2)[2];

data['uname'] = platform.uname()

data['number_of_connections'] = len(connection_list.rstrip().split("\n"))
#TODO
#connection_stats ESTABLISHED, WAIT etc ..
#TODO
#if /var/log/nginx/aaccess.log | /usr/local/apache/logs/error_log | 

# file stuff
with open('/proc/sys/fs/file-nr', 'r') as f:
	o_files = f.readline().rstrip().split()

data['open_files'] = o_files[0]
data['open_files_limit'] = o_files[2]

data['cpu_model'] = ""
data['cpu_cores'] = 0
data['cpu_speed'] = 0

for line in open('/proc/cpuinfo'):
	if "model name" in line:
		data['cpu_model'] = line.rstrip().split(': ')[1]
	if "processor" in line:
		data['cpu_cores'] +=1
	if "cpu MHz" in line:
		data['cpu_speed'] = line.rstrip().split(': ')[1] + " MHz"

timenow = int(calendar.timegm(time.gmtime()))

with open('/proc/stat', 'r') as f:
	general_stats = f.readline().rstrip().split()

general_stats.pop(0)
general_stats = map(int, general_stats)

current_cpu = general_stats[0] + general_stats[1] + general_stats[2] + general_stats[3]   
current_io = general_stats[3] + general_stats[4]   
current_idle = general_stats[3]   

data['outer_nic'] = ""

route = "/proc/net/route"
with open(route) as f:
		for line in f.readlines():
				try:
						iface, dest, _, flags, _, _, _, _, _, _, _, =  line.strip().split()
						if dest != '00000000' or not int(flags, 16) & 2:
								continue
						data['outer_nic'] = iface
				except:
						continue

with open('/sys/class/net/'+ data['outer_nic'] + '/statistics/rx_bytes', 'r') as f:
	data['received_data'] = int(f.readline().rstrip())

with open('/sys/class/net/' + data['outer_nic'] + '/statistics/tx_bytes', 'r') as f:
	data['transmited_data'] = int(f.readline().rstrip())

f = os.popen('ifconfig ' + data['outer_nic'] + ' | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1')
data['ipv4'] = f.read().rstrip()

# try catch ktu + check non empty
if os.path.exists('/opt/data_collector/stats_data'):
	with open('/opt/data_collector/stats_data', 'r') as f:
		previous_stats = map(int, f.readline().rstrip().split())

	timethen = previous_stats[0]

	previous_cpu = previous_stats[1]
	previous_io = previous_stats[2]   
	previous_idle = previous_stats[3]
	previous_rx = previous_stats[4]
	previous_tx = previous_stats[5]

	interval = timenow - timethen

	cpu_diff = current_cpu - previous_cpu
	io_diff = current_io - previous_io
	idle_diff = current_idle - previous_idle

	if(cpu_diff > 0):
		data['cpu_load'] = (1000*(cpu_diff - idle_diff)/cpu_diff + 5)/10
		
	if(io_diff > 0):
		data['io_load'] = (1000*(io_diff - idle_diff)/io_diff + 5)/10

	if(data['received_data'] > previous_rx ):
		data['rx_diff'] = data['received_data'] - previous_rx

	if(data['transmited_data'] > previous_tx ):
		data['tx_diff'] = data['transmited_data'] - previous_tx


f = open('/opt/data_collector/stats_data','w')
f.write(str(timenow) + ' ' + str(current_cpu) + ' ' + str(current_io) + ' ' + str(current_idle) + ' ' + str(data['received_data']) + ' ' + str(data['transmited_data']) + "\n") 
f.close()

os.system('ps axc -o uname:10,pcpu,rss,cmd --sort=-pcpu,-rss --noheaders --width 140 | head -40 > /opt/data_collector/process_list')
data['process_list'] = open('/opt/data_collector/process_list', 'r').read()



def post_to_api(data):
	api_url = 'http://monx.me/api/test'
	post_data = {
			'cpu_load' 							: data['cpu_load'],
			'io_load' 							: data['io_load'],
			'process_list'					: data['process_list'],
			'received_data' 				: data['received_data'],
			'transmited_data' 			: data['transmited_data'],
			'rx_diff' 							: data['rx_diff'],
			'tx_diff' 							: data['tx_diff'],
			'cpu_cores' 						: data['cpu_cores'],
			'cpu_model' 	 					: data['cpu_model'],
			'cpu_speed'							: data['cpu_speed'],
			'load'									: data['load'],
			'uname'									: data['uname'],
			'uptime'								: data['uptime'],
			'outer_nic'							: data['outer_nic'],
			'open_files'						: data['open_files'],
			'ipv4'									: data['ipv4'],
			'open_files_limit'			:	data['open_files_limit'],
			'number_of_logins'			: data['number_of_logins'],
			'number_of_processes'		: data['number_of_processes'],
			'number_of_connections' :	data['number_of_connections'],
			'connection_list' 			: data['connection_list'],
			'memtotal'							: data['memtotal'],
			'memfree'								:	data['memfree'],
			'memavailable'					: data['memavailable'],
			'memcached' 						: data['memcached'],
			'memswaptotal' 					: data['memswaptotal'],
			'memswapfree' 					: data['memswapfree']
	}

	#req.add_header('Content-Type','application/json')
	# try:
	# 	r = requests.post(api_url, data=post_data)
	r = requests.post(api_url, data=post_data)
	# except HTTPError as e:
	# 	print 'HTTP Issue while posting to API ' + str(e)
	# except URLError as e:
	# 	print 'L4 Issue while posting to API ' + str(e)
	# except SocketError as e:
	# 	print 'Socket Issue while posting to API ' + str(e)
	# else:
	# 	print 'sikur u bo'


post_to_api(data)
