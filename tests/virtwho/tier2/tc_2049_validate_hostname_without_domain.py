# coding:utf-8
from virt_who import *
from virt_who.base import Base
from virt_who.register import Register
from virt_who.testing import Testing

class Testcase(Testing):
    def test_run(self):
        self.vw_case_info(os.path.basename(__file__), case_id='RHEL-136708')
        hypervisor_type = self.get_config('hypervisor_type')
        if hypervisor_type not in ("esx", "libvirt-remote"):
            self.vw_case_skip(hypervisor_type)
        self.vw_case_init()

        # case config
        results = dict()
        config = self.get_hypervisor_config()
        hypervisor_host = config['ssh_hypervisor']
        register_config = self.get_register_config()
        register_type = register_config['type']
        register_owner = register_config['owner']
        host_name = self.get_hypervisor_hostname()
        host_uuid = self.get_hypervisor_hostuuid()
        hostname_original = self.get_hypervisor_hostname()
        hostname_non_domain = hostname_original.split('.')[0]
        config_name = "virtwho-config"
        config_file = "/etc/virt-who.d/{0}.conf".format(config_name)
        self.vw_etc_d_mode_create(config_name, config_file)
        self.vw_option_add('hypervisor_id', 'hostname', config_file)
        self.vw_option_enable('[global]', '/etc/virt-who.conf')
        self.vw_option_enable('debug', '/etc/virt-who.conf')
        self.vw_option_update_value('debug', 'True', '/etc/virt-who.conf')

        # case steps
        try:
            logger.info(">>>step1: run virt-who for hostname without domain name")
            if hypervisor_type == "esx":
                cmd = 'esxcli system hostname set --fqdn={}'.format(hostname_non_domain)
                ret, output = self.runcmd(cmd, hypervisor_host, desc="update hostname")
            if hypervisor_type == "libvirt-remote":
                ssh_libvirt = hypervisor_host
                host_ip = self.get_ipaddr(ssh_libvirt)
                etc_hosts_value = "{0} {1}".format(host_ip, hostname_non_domain)
                self.set_hostname(hostname_non_domain, ssh_libvirt)
                self.set_etc_hosts(etc_hosts_value, ssh_libvirt)
            data, tty_output, rhsm_output = self.vw_start(exp_send=1)
            res1 = self.op_normal_value(data, exp_error=0, exp_thread=1, exp_send=1)
            res2 = self.vw_msg_search(str(data), hostname_non_domain, exp_exist=True)
            res3 = self.vw_msg_search(str(data), hostname_original, exp_exist=False)
            results.setdefault('step1', []).append(res1)
            results.setdefault('step1', []).append(res2)
            results.setdefault('step1', []).append(res3)
        except:
            results.setdefault('step1', []).append(False)
            pass
        finally:
            logger.info(">>>step2: start to recovery hostname")
            if "satellite" in register_type:
                self.vw_web_host_delete(host_name, host_uuid)
            if "stage" in register_type:
                self.stage_consumer_clean(self.ssh_host(), register_config)
            if hypervisor_type == "esx":
                cmd = 'esxcli system hostname set --fqdn={}'.format(hostname_original)
                ret, output = self.runcmd(cmd, hypervisor_host)
            if hypervisor_type == "libvirt-remote":
                etc_hosts_value = "{0} {1}".format(hypervisor_host, hostname_original)
                self.set_hostname(hostname_original, hypervisor_host)
                self.set_etc_hosts(etc_hosts_value, hypervisor_host)
            if self.get_hypervisor_hostname() == hostname_original:
                logger.info('Succeeded to change back hostname')
                results.setdefault('step2', []).append(True)
            else:
                logger.error('Failed to change back hostname')
                results.setdefault('step2', []).append(False)

        # Case Result
        self.vw_case_result(results)