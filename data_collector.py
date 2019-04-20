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
import logging
import re
from socket import error as SocketError
from urllib2 import Request, urlopen, URLError, HTTPError

debug = False
data = {}


class _sensor:
    def __init__(self):
        logging.debug("Composing object sensor")
        self._uname = platform.uname()
        self._number_of_logins = ''
        self._disks = self._all_disks = ''
        self._cpu_speed = self._cpu_cores = self._cpu_model = self._cpu_thread_data = ''
        self._open_files_limit = 0
        self._outer_nic = ''
        self._agent_version = '1.0.14'
        self._rx_diff = 0
        self._tx_diff = 0
        self._ips = ''
        self._last_installed = 0
        self._transmitted_data = 0
        self._received_data = 0
        self._load_proc = 0
        self._open_files = 0
        self._usr_cpu = self._sys_cpu = self._nic_cpu = self._idl_cpu = self._io_wait = self._hw_irq = self._sf_irq = self._st_time = 0
        self._total_tsk = self._running_tsk = self._sleep_tsk = self._stopped_tsk = self._zombie_tsk = 0
        self._memtotal = self._memfree = self._memswaptotal = self._memswapfree = self._memcached = self._membuffers = 0
        self._uptime = ''
        self._process_list = ''
        self._number_of_processes = ''
        self._connection_list = ''
        self._number_of_connections = 0
        self.post_data = {}

    def collect(self):
        if not os.geteuid() == 0:
            print('Script must be run as root')
            exit(1)
        else:
            print('Root check OK')

        if os.path.exists('/var/log/yum.log'):
            self._last_installed = os.path.getmtime('/var/log/yum.log')
        elif os.path.exists('/var/log/dpkg.log'):
            self._last_installed = os.path.getmtime('/var/log/dpkg.log')
        elif os.path.exists('/var/log/YaST2/y2logRPM'):
            self._last_installed = os.path.getmtime('/var/log/YaST2/y2logRPM')
        else:
            self._last_installed = -1

        with open('/proc/uptime', 'r') as f:
            self._uptime = float(f.readline().rstrip().split()[0])

        with open('/proc/loadavg', 'r') as f:
            self._load_proc = float(f.readline().rstrip().split()[0])

        connection_list = subprocess.Popen(
            ['netstat', '-tun'], stdout=subprocess.PIPE).communicate()[0].rstrip()
        self._connection_list = connection_list.split("\n")
        self._number_of_logins = subprocess.Popen(
            ['who'], stdout=subprocess.PIPE).communicate()[0].rstrip().split("\n")
        self._number_of_processes = len(subprocess.Popen(
            ['ps', 'ax'], stdout=subprocess.PIPE).communicate()[0].rstrip().split("\n"))
        self._number_of_connections = len(connection_list.split("\n"))

        with open('/proc/sys/fs/file-nr', 'r') as f:
            o_files = f.readline().rstrip().split()
            self._open_files, self._open_files_limit = int(o_files[0]), int(o_files[2])

        #     ps = subprocess.Popen("ps axc -o uname:10,pcpu,rss,cmd --sort=-pcpu,-rss --noheaders --width 140 | head -40",
        #                           shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #     return ps.communicate()[0].split("\n")

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

        cpu_info = subprocess.Popen("lscpu | egrep '^Thread|^Core|^Socket|^CPU\('",
                                    shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        cpu_thread_data = cpu_info.communicate()[0]
        self._cpu_model, self._cpu_cores, self._cpu_speed, self._cpu_thread_data = (
            cpu_model, cpu_cores, cpu_speed, cpu_thread_data)

        root_d = subprocess.Popen("df -k | grep '^/' | awk '{ print $1 \" \" $2 \" \" $3 }'", shell=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        all_d = subprocess.Popen("df -k | awk '{ print $1 \" \" $2 \" \" $3 }' | grep -v 'loop' | grep -v '^shm' | grep -v '^overlay' ", shell=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        all_inodes = subprocess.Popen("df -i |  grep '^/' | awk '{ print $1 \" \" $2 \" \" $3 }'", shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        self._disks = root_d.communicate()[0].split("\n")
        self._all_disks = all_d.communicate()[0].split("\n")
        self._all_inodes = all_inodes.communicate()[0].split("\n")

        # possible bug on virtualized
        # default dev venet0  scope link
        with open('/proc/net/route') as f:
            for line in f.readlines():
                try:
                    iface, dest, _, flags, _, _, _, _, _, _, _, = line.strip().split()
                    if dest != '00000000' or not int(flags, 16) & 2:
                        continue
                    self._outer_nic = iface
                except:
                    continue

        load_core = subprocess.Popen(
            "top -n1 -b ", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        top_data = load_core.communicate()[0].split("\n")

        # load_filter = r"top - (.*)(\d+) user,\s+load average: (\d+.\d+), (\d+.\d+), (\d+.\d+)"
        task_filter = r"Tasks: (\d+) total,\s+(\d+) running,\s+(\d+) sleeping,\s+(\d+) stopped,\s+(\d+) zombie"
        res_filter = r"\%?Cpu\(s\):\s+(\d+.\d+)\%?\s?us,\s+(\d+.\d+)\%?\s?sy,\s+(\d+.\d+)\%?\s?ni,\s+(\d+.\d+)\%?\s?id,\s+(\d+.\d+)\%?\s?wa,\s+(\d+.\d+)\%?\s?hi,\s+(\d+.\d+)\%?\s?si(,\s+(\d+.\d+)\%?\s?st)?"
        # mem_filter = r"KiB\s?Mem:\s+(\d+)k total,\s+(\d+)k used,\s+(\d+)k free,\s+(\d+)k buffers"
        # swp_filter = r"KiB\s?Swap:\s+(\d+)k total,\s+(\d+)k used,\s+(\d+)k free,\s+(\d+)k cached"

        self._total_tsk, self._running_tsk, self._sleep_tsk, self._stopped_tsk, self._zombie_tsk = re.match(
            task_filter, top_data[1]).groups()
        resources = re.match(res_filter, top_data[2])
        self._usr_cpu, self._sys_cpu, self._nic_cpu, self._idl_cpu, self._io_wait, self._hw_irq, self._sf_irq = resources.group(
            1), resources.group(2), resources.group(3), resources.group(4), resources.group(5), resources.group(6), resources.group(7)

        with open('/proc/meminfo', 'r') as f:
            meminfo = f.readlines()
            for memi in meminfo:
                temp = memi.rstrip().split(': ')
                if temp[0] == 'MemTotal':
                    self._memtotal = int((temp[1].strip()).replace(" kB", ""))
                if temp[0] == 'MemFree':
                    self._memfree = int((temp[1].strip()).replace(" kB", ""))
                if temp[0] == 'Buffers':
                    self._membuffers = int((temp[1].strip()).replace(" kB", ""))
                if temp[0] == 'Cached':
                    self._memcached = int((temp[1].strip()).replace(" kB", ""))
                if temp[0] == 'SwapTotal':
                    self._memswaptotal = int(
                        (temp[1].strip()).replace(" kB", ""))
                if temp[0] == 'SwapFree':
                    self._memswapfree = int(
                        (temp[1].strip()).replace(" kB", ""))

        if(resources.group(9)):
            self._st_time = resources.group(9)
        else:
            self._st_time = 0

        with open('/sys/class/net/' + self._outer_nic + '/statistics/rx_bytes', 'r') as f:
            self._received_data = int(f.readline().rstrip())

        with open('/sys/class/net/' + self._outer_nic + '/statistics/tx_bytes', 'r') as f:
            self._transmitted_data = int(f.readline().rstrip())

        # TODO: /sbin/ip addr show br0 | grep inet | awk '{print $2}'
        f = os.popen('/sbin/ip addr | grep inet| grep -v "^fe80" | grep -v "^fd" | awk \'{print $2}\' ')
        self._ips = f.read().replace('\n', ', ')
        f.close()

    def check_update(self):
        urllib.urlretrieve('https://raw.githubusercontent.com/tuwid/monx-agent/master/data_collector.py',
                           "/opt/data_collector/data_collector.py")
        subprocess.call(
            ['chmod', '0755', '/opt/data_collector/data_collector.py'])
        exit(1)
    # return subprocess.Popen("/sbin/ip route | grep '^default' |  awk '{ print $5 }'",shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).communicate()[0].rstrip()

    def populate(self):
        self.post_data = {
            'uname'						: self._uname,
            'number_of_logins'			: self._number_of_logins,
            'disks'						: self._disks,
            'all_disks'					: self._all_disks,
            'cpu_cores' 				: self._cpu_cores,
            'cpu_speed'					: self._cpu_speed,
            'cpu_model' 	 			: self._cpu_model,
            'cpu_thread_data'           : self._cpu_thread_data,
            'open_files_limit'			: self._open_files_limit,
            'outer_nic'					: self._outer_nic,
            'membuffers'				: self._membuffers,
            'agent_version'             : self._agent_version,
            'ips'                       : self._ips,
            'last_installed'            : self._last_installed,
            'transmitted_data' 			: self._transmitted_data,
            'received_data' 			: self._received_data,
            'usr_cpu'                   : self._usr_cpu,
            'sys_cpu'                   : self._sys_cpu,
            'nic_cpu'                   : self._nic_cpu,
            'idl_cpu'                   : self._idl_cpu,
            'io_wait'                   : self._io_wait,
            'hw_irq'                    : self._hw_irq,
            'sf_irq'                    : self._sf_irq,
            'st_time'                   : self._st_time,
            'load_proc'					: self._load_proc,
            'total_tsk'                 : self._total_tsk,
            'running_tsk'               : self._running_tsk,
            'sleep_tsk'                 : self._sleep_tsk,
            'stopped_tsk'               : self._stopped_tsk,
            'zombie_tsk'                : self._zombie_tsk,
            'open_files'				: self._open_files,
            'uptime'					: self._uptime,
            'process_list'				: self._process_list,
            'number_of_processes'		: self._number_of_processes,
            'connection_list' 			: self._connection_list,
            'number_of_connections'     : self._number_of_connections,
            'memtotal'                  : self._memtotal,
            'memfree'					: self._memfree,
            'memswaptotal' 				: self._memswaptotal,
            'memswapfree' 				: self._memswapfree,
            'memcached' 				: self._memcached,
        }

    def post_to_api(self):

        config = ConfigParser.ConfigParser()
        config.read('/opt/data_collector/default.conf')

        api_url = config.get('settings', 'API_URL')

        req = Request(api_url)
        req.add_header('Content-Type', 'application/json')
        req.add_header('X-Merhaba-From', 'x-monx-api')
        try:
            response = urlopen(req, json.dumps(self.post_data))
            print response.read()
            print response.code
        except HTTPError as e:
            print 'HTTP Issue while posting to API ' + str(e)
        except URLError as e:
            print 'L4 Issue while posting to API ' + str(e)
        except SocketError as e:
            print 'Socket Issue while posting to API ' + str(e)

    def print_collection(self):
        for key in self.post_data:
            print key, ' - ', self.post_data[key]


local_sensor = _sensor()

if len(sys.argv) > 1 and sys.argv[1] == '-u':
    local_sensor.check_update()
local_sensor.collect()
local_sensor.populate()

if (debug):
    local_sensor.print_collection()
else:
    local_sensor.post_to_api()
# TODO
# connection_stats ESTABLISHED, WAIT etc ..
# TODO
# if /var/log/nginx/access.log || /usr/local/apache/logs/error_log |
