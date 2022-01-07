from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_netmiko.tasks import netmiko_send_command
from nornir.core.filter import F
from datetime import datetime
import json, getpass

start_time = datetime.now()

dev_status = {}

nr = InitNornir(
    config_file="nornir.yaml", dry_run=True
)

username = input('Enter your TACACS Username:')
password = getpass.getpass(prompt="Enter your Password:")

nr.inventory.groups['padrao'].dict()['connection_options']['netmiko']['extras']['secret'] = password
nr.inventory.groups['padrao'].username = username
nr.inventory.groups['padrao'].password = password


show_ver = nr.run(task=netmiko_send_command,  command_string='show ver', enable=False)


for ip in nr.inventory.hosts:
    dev_status[ip] = {
        "timestamps": str(datetime.now()),
        "vendor": "Cisco",
        "criticidade": "Informational",
        "ambiente": "Internet",
        "texto": "CPU OK: 20%",
        "hostname": "MMXXSSDD",
        "ip": ip
    }
    
    if ('Adaptive Security Appliance' in show_ver[ip].result):
        nr.inventory.hosts[ip].groups = 'asa'
    elif ('NX-OS' in show_ver[ip].result):
        nr.inventory.hosts[ip].groups = 'nxos'
    else:
        nr.inventory.hosts[ip].groups = 'ios'



asa = nr.filter(F(groups__contains="asa"))
cisco = nr.filter(F(groups__contains="ios"))
nexus = nr.filter(F(groups__contains="nxos"))

asa.show_cpu, asa.name, asa.show_hostname = "show cpu usage", "asa", "show runn hostname"
cisco.name, cisco.show_cpu, cisco.show_hostname = "cisco", "show processes cpu | i five", "show runn | i hostname"
nexus.name, nexus.show_cpu, nexus.show_hostname = "nexus", "show processes cpu | i five", "show runn | i hostname"

all_devs = [asa, cisco, nexus]
show_cpu = {}
show_hostname = {}

for dev in all_devs:
    show_cpu[dev.name] = dev.run(task=netmiko_send_command, command_string=dev.show_cpu, enable=True)
    show_hostname[dev.name] = dev.run(task=netmiko_send_command, command_string=dev.show_hostname, enable=True)

    for j in dev.inventory.hosts:
        try:
            dev_status[j]['hostname'] = show_hostname[dev.name][j].result.split('hostname')[-1].split('\n')[0]
            dev_status[j]['texto'] = "CPU OK:" + show_cpu[dev.name][j].result.split('5 minutes: ')[-1].split('five minutes: ')[-1].split('\n')[0]
        except Exception as E:
            continue

print(json.dumps(dev_status, indent=2))

end_time = datetime.now()
total_time = end_time - start_time
print('Total Time: {}'.format(total_time))

input("Type anything to finish")
