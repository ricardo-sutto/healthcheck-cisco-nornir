from nornir import InitNornir
from nornir_utils.plugins.functions import print_result
from nornir_netmiko.tasks import netmiko_send_command
from nornir.core.filter import F
from datetime import datetime
import json, getpass

start_time = datetime.now()

dev_status = {}

#cria objeto 'nr' com as informações presentes no arquivo 'nornir.yaml'
nr = InitNornir(
    config_file="nornir.yaml", dry_run=True
)

#requisitar credencial do usuario com permissão de entrada na lista de hosts
username = input('Enter your TACACS Username:')
password = getpass.getpass(prompt="Enter your Password:")

#substituir credenciais recebidas do arquivo defaults.yaml
nr.inventory.groups['padrao'].username = username
nr.inventory.groups['padrao'].password = password
nr.inventory.groups['padrao'].dict()['connection_options']['netmiko']['extras']['secret'] = password

#envia paralelamente para todos os dispositivos do objeto o comando 'show version'
show_ver = nr.run(task=netmiko_send_command,  command_string='show ver', enable=False)


for ip in nr.inventory.hosts:
    #preencher lista dev_status com o formato JSON esperado
    dev_status[ip] = {
        "timestamps": str(datetime.now()),
        "vendor": "Cisco",
        "criticidade": "Informational",
        "ambiente": "Internet",
        "texto": "CPU OK: 20%",
        "hostname": "MMXXSSDD",
        "ip": ip
    }

    #através do resultado do comando 'show version', verificar qual tipo de equipamento e colocar em seu respectivo grupo (ex.: cisco asa)
    if ('Adaptive Security Appliance' in show_ver[ip].result):
        nr.inventory.hosts[ip].groups = 'asa'
    elif ('NX-OS' in show_ver[ip].result):
        nr.inventory.hosts[ip].groups = 'nxos'
    else:
        nr.inventory.hosts[ip].groups = 'ios'


#cria outros objetos exclusivos para cada tipo de equipamento
asa = nr.filter(F(groups__contains="asa"))
cisco = nr.filter(F(groups__contains="ios"))
nexus = nr.filter(F(groups__contains="nxos"))

#cria metodos adicionais nos objetos criados. Como nome, qual comando de verificar a cpu e hostname
asa.show_cpu, asa.name, asa.show_hostname = "show cpu usage", "asa", "show runn hostname"
cisco.name, cisco.show_cpu, cisco.show_hostname = "cisco", "show processes cpu | i five", "show runn | i hostname"
nexus.name, nexus.show_cpu, nexus.show_hostname = "nexus", "show processes cpu | i five", "show runn | i hostname"

#coloca os objetos numa lista
all_devs = [asa, cisco, nexus]

show_cpu = {}
show_hostname = {}

for dev in all_devs:
    #envia paralelamente para todos os dispositivos do objeto percorrido os comandos de show_cpu e show_hostname
    show_cpu[dev.name] = dev.run(task=netmiko_send_command, command_string=dev.show_cpu, enable=True)
    show_hostname[dev.name] = dev.run(task=netmiko_send_command, command_string=dev.show_hostname, enable=True)

    for ip in dev.inventory.hosts:
        #manipula as informações tiradas dos comandos e insere na lista dev_status para o resultado final
        try:
            dev_status[ip]['hostname'] = show_hostname[dev.name][ip].result.split('hostname')[-1].split('\n')[0]
            dev_status[ip]['texto'] = "CPU OK: " + show_cpu[dev.name][ip].result.split('5 minutes: ')[-1].split('five minutes: ')[-1].split('\n')[0]
        except Exception as E:
            continue

#mostra o resultado final de todos os dispositivos em formato JSON
print(json.dumps(dev_status, indent=2))

end_time = datetime.now()
total_time = end_time - start_time
print('Total Time: {}'.format(total_time))

input("Type anything to finish")
