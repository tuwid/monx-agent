#!/usr/bin/python

# importing some stuff
import os, subprocess
import platform
import urllib2
import calendar
import time

with open('/proc/uptime', 'r') as f:
	uptime = f.readline().rstrip().split()[0]

number_of_logins = len(subprocess.check_output("who").rstrip().split("\n"))

# with threads , the number is lower by just getting the procs
number_of_processes = len(subprocess.Popen(['ps', 'ax'], stdout=subprocess.PIPE).communicate()[0].rstrip().split("\n"))

with open('/proc/loadavg', 'r') as f:
	load = f.readline().rstrip().split()

with open('/proc/meminfo', 'r') as f:
	meminfo = f.readlines()

for memi in meminfo:
	temp = memi.rstrip().split(': ')
	if (temp[0] == 'MemTotal'):
		memtotal = temp[1].strip()
	if (temp[0] == 'MemFree'):
		memfree = temp[1].strip()
	if (temp[0] == 'MemAvailable'):
		memavailable = temp[1].strip()
	if (temp[0] == 'Cached'):
		memcached = temp[1].strip()
	if (temp[0] == 'SwapTotal'):
		memswaptotal = temp[1].strip()
	if (temp[0] == 'SwapFree'):
		memswapfree = temp[1].strip()


connection_list = subprocess.Popen(['netstat', '-tun'], stdout=subprocess.PIPE).communicate()[0].rstrip()
connection_list = connection_list.split("\n",2)[2];

uname = platform.uname()

number_of_connections = len(connection_list.rstrip().split("\n"))
#TODO
#connection_stats ESTABLISHED, WAIT etc ..
#TODO
#if /var/log/nginx/aaccess.log | /usr/local/apache/logs/error_log | 

# file stuff
with open('/proc/sys/fs/file-nr', 'r') as f:
	o_files = f.readline().rstrip().split()

open_files = o_files[0]
open_files_limit = o_files[2]

cpu_model = ""
cpu_cores = 0
cpu_speed = 0

for line in open('/proc/cpuinfo'):
	if "model name" in line:
		cpu_model = line.rstrip().split(': ')[1]
	if "processor" in line:
		cpu_cores+=1
	if "cpu MHz" in line:
		cpu_speed = line.rstrip().split(': ')[1] + " MHz"

timenow = int(calendar.timegm(time.gmtime()))

with open('/proc/stat', 'r') as f:
	general_stats = f.readline().rstrip().split()

general_stats.pop(0)
general_stats = map(int, general_stats)

current_cpu = general_stats[0] + general_stats[1] + general_stats[2] + general_stats[3]   
current_io = general_stats[3] + general_stats[4]   
current_idle = general_stats[3]   

outer_nic = ""

route = "/proc/net/route"
with open(route) as f:
		for line in f.readlines():
				try:
						iface, dest, _, flags, _, _, _, _, _, _, _, =  line.strip().split()
						if dest != '00000000' or not int(flags, 16) & 2:
								continue
						outer_nic = iface
				except:
						continue

with open('/sys/class/net/'+ outer_nic + '/statistics/rx_bytes', 'r') as f:
	received_data = int(f.readline().rstrip())

with open('/sys/class/net/' + outer_nic + '/statistics/tx_bytes', 'r') as f:
	transmited_data = int(f.readline().rstrip())

f = os.popen('ifconfig ' + outer_nic + ' | grep "inet\ addr" | cut -d: -f2 | cut -d" " -f1')
ipv4=f.read().rstrip()

# try catch ktu
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
		cpu_load = (1000*(cpu_diff - idle_diff)/cpu_diff + 5)/10
		
	if(io_diff > 0):
		io_load = (1000*(io_diff - idle_diff)/io_diff + 5)/10

	if(received_data > previous_rx ):
		rx_diff = received_data - previous_rx

	if(transmited_data > previous_tx ):
		tx_diff = transmited_data - previous_tx


f = open('/opt/data_collector/stats_data','w')
f.write(str(timenow) + ' ' + str(current_cpu) + ' ' + str(current_io) + ' ' + str(current_idle) + ' ' + str(received_data) + ' ' + str(transmited_data) + "\n") 
f.close()


# print cpu_load
# print io_load
# print received_data
# print transmited_data
# print rx_diff
# print tx_diff
# print cpu_cores
# print cpu_model
# print cpu_speed
# print load
# print uname
# print uptime
# print outer_nic
# print open_files
# print ipv4
# print open_files_limit
# print number_of_logins
# print number_of_processes
# print number_of_connections 
# print connection_list 

# print memtotal
# print memfree
# print memavailable
# print memcached
# print memswaptotal
# print memswapfree