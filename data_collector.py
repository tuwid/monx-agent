#!/usr/bin/python

# importing some stuff
import ConfigParser
import calendar
import json
import os
import platform
import subprocess
import sys
import time
import urllib
from socket import error as SocketError
from urllib2 import Request, urlopen, URLError, HTTPError

debug = False
agent_version = '1.0.10'

data = {}


def check_for_root():
    if not os.geteuid() == 0:
        print('Script must be run as root')
        exit(1)
    else:
        print('Root check OK')


def check_last_installed():
    if os.path.exists('/var/log/yum.log'):
        return os.path.getmtime('/var/log/yum.log')
    elif os.path.exists('/var/log/dpkg.log'):
        return os.path.getmtime('/var/log/dpkg.log')
    elif os.path.exists('/var/log/YaST2/y2logRPM'):
        return os.path.getmtime('/var/log/YaST2/y2logRPM')
    else:
        return '-1'


def check_uptime():
    with open('/proc/uptime', 'r') as f:
        return f.readline().rstrip().split()[0]


def check_loadavg():
    with open('/proc/loadavg', 'r') as f:
        return f.readline().rstrip().split()


def check_connection_list():
    connection_list = subprocess.Popen(['netstat', '-tun'], stdout=subprocess.PIPE).communicate()[0].rstrip()
    return connection_list.split("\n")


def check_number_of_logins():
    return subprocess.Popen(['who'], stdout=subprocess.PIPE).communicate()[0].rstrip().split("\n")


def check_number_of_processes():
    return len(subprocess.Popen(['ps', 'ax'], stdout=subprocess.PIPE).communicate()[0].rstrip().split("\n"))


def check_number_of_connections():
    return len(subprocess.Popen(['netstat', '-tun'], stdout=subprocess.PIPE).communicate()[0].rstrip().split("\n"))


def check_process_list():
    ps = subprocess.Popen("ps axc -o uname:10,pcpu,rss,cmd --sort=-pcpu,-rss --noheaders --width 140 | head -40",
                          shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return ps.communicate()[0].split("\n")


def check_file_limits():
    with open('/proc/sys/fs/file-nr', 'r') as f:
        o_files = f.readline().rstrip().split()
        return o_files[0], o_files[2]


def check_update():
    urllib.urlretrieve('https://raw.githubusercontent.com/tuwid/monx-agent/master/data_collector.py',
                       "/opt/data_collector/data_collector.py")
    subprocess.call(['chmod', '0755', '/opt/data_collector/data_collector.py'])
    exit(1)


def check_cpu_info():
    cpu_model = ""
    cpu_cores = 0
    cpu_speed = 0
    for line in open('/proc/cpuinfo'):
        if "model name" in line:
            cpu_model = line.rstrip().split(': ')[1]
        if "processor" in line:
            cpu_cores += 1
        if "cpu MHz" in line:
            cpu_speed = line.rstrip().split(': ')[1] + " MHz"
    cpu_info = subprocess.Popen("lscpu | egrep '^Thread|^Core|^Socket|^CPU\('", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    cpu_thread_data = cpu_info.communicate()[0]

    return cpu_model, cpu_cores, cpu_speed, cpu_thread_data


def check_memory():
    with open('/proc/meminfo', 'r') as f:
        meminfo = f.readlines()

    for memi in meminfo:
        temp = memi.rstrip().split(': ')
        if temp[0] == 'MemTotal':
            memtotal = temp[1].strip()
        if temp[0] == 'MemFree':
            memfree = temp[1].strip()
        if temp[0] == 'Buffers':
            membuffers = temp[1].strip()
        if temp[0] == 'Cached':
            memcached = temp[1].strip()
        if temp[0] == 'SwapTotal':
            memswaptotal = temp[1].strip()
        if temp[0] == 'SwapFree':
            memswapfree = temp[1].strip()
    return memtotal, membuffers, memfree, memcached, memswaptotal, memswapfree


def check_disks():
    root_d = subprocess.Popen("df -k | grep '^/' | awk '{ print $1 \" \" $2 \" \" $3 }'", shell=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    all_d = subprocess.Popen("df -k | awk '{ print $1 \" \" $2 \" \" $3 }'", shell=True,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # all_inodes = subprocess.Popen("df -i | awk '{ print $1 \" \" $2 \" \" $3 }'", shell=True,
    #                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    root_disk = root_d.communicate()[0].split("\n")
    all_disks = all_d.communicate()[0].split("\n")

    return root_disk, all_disks


# possible bug on virtualized
# default dev venet0  scope link
def check_outer_nic():
    with open('/proc/net/route') as f:
        for line in f.readlines():
            try:
                iface, dest, _, flags, _, _, _, _, _, _, _, = line.strip().split()
                if dest != '00000000' or not int(flags, 16) & 2:
                    continue
                return iface
            except:
                continue


# return subprocess.Popen("/sbin/ip route | grep '^default' |  awk '{ print $5 }'",shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).communicate()[0].rstrip()

def post_to_api(data):
    post_data = {
        'agent_version'			    : data['agent_version'],
        'cpu_load' 					: data['cpu_load'],
        'io_load' 					: data['io_load'],
        'process_list'				: data['process_list'],
        'received_data' 			: data['received_data'],
        'transmited_data' 			: data['transmited_data'],
        'rx_diff' 					: data['rx_diff'],
        'tx_diff' 					: data['tx_diff'],
        'cpu_cores' 				: data['cpu_cores'],
        'cpu_model' 	 			: data['cpu_model'],
        'cpu_speed'					: data['cpu_speed'],
        'cpu_thread_data'           : data['cpu_thread_data'],
        'load_proc'					: data['load'],
        'disks'						: data['disks'],
        'all_disks'					: data['all_disks'],
        'uname'						: data['uname'],
        'uptime'					: data['uptime'],
        'outer_nic'					: data['outer_nic'],
        'open_files'				: data['open_files'],
        'ips'                       : data['ips'],
        'last_installed'            : data['last_installed'],
        'open_files_limit'			: data['open_files_limit'],
        'number_of_logins'			: data['number_of_logins'],
        'number_of_processes'		: data['number_of_processes'],
        'number_of_connections'     : data['number_of_connections'],
        'connection_list' 			: data['connection_list'],
        'memtotal'				    : data['memtotal'],
        'membuffers'				: data['membuffers'],
        'memfree'					: data['memfree'],
        'memcached' 				: data['memcached'],
        'memswaptotal' 				: data['memswaptotal'],
        'memswapfree' 				: data['memswapfree']
    }

    config = ConfigParser.ConfigParser()
    config.read('/opt/data_collector/default.conf')

    api_key = config.get('settings', 'API_KEY' )
    api_url = config.get('settings', 'API_URL' )
    api_url = api_url + api_key

    req = Request(api_url)
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-Merhaba-From', 'x-monx-api')
    try:
        response = urlopen(req,json.dumps(post_data))
        print response.read()
    except HTTPError as e:
        print 'HTTP Issue while posting to API ' + str(e)
    except URLError as e:
        print 'L4 Issue while posting to API ' + str(e)
    except SocketError as e:
        print 'Socket Issue while posting to API ' + str(e)
    print response.code

check_for_root()

if len(sys.argv) > 1 and sys.argv[1] == '-u':
    check_update()

data['load'] = check_loadavg()
data['uptime'] = check_uptime()
data['uname'] = platform.uname()
data['outer_nic'] = check_outer_nic()
data['agent_version'] = agent_version
data['process_list'] = check_process_list()
data['last_installed'] = check_last_installed()
data['disks'], data['all_disks'] = check_disks()
data['connection_list'] = check_connection_list()
data['number_of_logins'] = check_number_of_logins()
data['number_of_processes'] = check_number_of_processes()
data['number_of_connections'] = check_number_of_connections()
data['open_files'], data['open_files_limit'] = check_file_limits()
data['cpu_model'], data['cpu_cores'], data['cpu_speed'], data['cpu_thread_data'] = check_cpu_info()
data['memtotal'], data['membuffers'], data['memfree'], data['memcached'], data['memswaptotal'], data['memswapfree'] = check_memory()

# TODO
# connection_stats ESTABLISHED, WAIT etc ..
# TODO
# if /var/log/nginx/access.log || /usr/local/apache/logs/error_log |

timenow = int(calendar.timegm(time.gmtime()))

with open('/proc/stat', 'r') as f:
    general_stats = f.readline().rstrip().split()

general_stats.pop(0)
general_stats = map(int, general_stats)

current_cpu = general_stats[0] + general_stats[1] + general_stats[2] + general_stats[3]
current_io = general_stats[3] + general_stats[4]
current_idle = general_stats[3]


with open('/sys/class/net/'+ data['outer_nic'] + '/statistics/rx_bytes', 'r') as f:
    data['received_data'] = int(f.readline().rstrip())

with open('/sys/class/net/' + data['outer_nic'] + '/statistics/tx_bytes', 'r') as f:
    data['transmited_data'] = int(f.readline().rstrip())

# TODO: /sbin/ip addr show br0 | grep inet | awk '{print $2}' 
f = os.popen('/sbin/ip addr | grep inet | awk \'{print $2}\'')
data['ips'] = f.read()
f.close()

# TODO: try catch ktu + check non empty
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

    if cpu_diff > 0: data[ 'cpu_load'] = (1000*(cpu_diff - idle_diff) / cpu_diff + 5)/10

    if io_diff > 0:
        data[ 'io_load'] = (1000*(io_diff - idle_diff)/io_diff + 5)/10

    if data['received_data'] > previous_rx:
        data['rx_diff'] = data['received_data'] - previous_rx

    if data['transmited_data'] > previous_tx:
        data['tx_diff'] = data['transmited_data'] - previous_tx
else:
    data['cpu_load'] = -1
    data['io_load'] = -1
    data['rx_diff'] = -1
    data['tx_diff'] = -1

stats_file = open('/opt/data_collector/stats_data', 'w')
stats_file.write(str(timenow) + ' ' + str(current_cpu) + ' ' + str(current_io) + ' ' + str(current_idle) + ' ' + str(data['received_data']) + ' ' + str(data['transmited_data']) + "\n")
stats_file.close()

# print data
if data['cpu_load'] != '-1':
    post_to_api(data)
    if (debug):
        print(data)
