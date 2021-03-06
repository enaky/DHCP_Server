import logging as log
import socket
import sys
from dhcp_packet import DHCP_PACKET, DHCP_Message_Type, DHCP_Opcode
import tkinter as tk
import datetime

FORMAT = '[%(asctime)s] [%(levelname)s] : %(message)s'
log.basicConfig(stream=sys.stdout, level=log.DEBUG, format=FORMAT)

server_port = 67
client_port = 68
MAX_BYTES = 1024
recv_timeout = 5


class DHCP_Server:
    def __init__(self, gui=None):
        self.ip = '0.0.0.0'
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.dest = ('255.255.255.255', client_port)
        self.running_flag = True
        self.server_is_shut_down = True
        self.name = None
        self.address_pool = {}
        self.old_mac_ip = {}
        self.address_pool_starting_ip_address = None
        self.address_pool_mask = None
        self.address_pool_broadcast = None
        self.lease_time = None
        self.renewal_time = None
        self.rebinding_time = None
        self.gui = gui
        self.show_packets_debug = False
        self.router = '127.0.0.1'
        self.dns = 'retele_proiect.org'

    def set_address_pool_config(self, ip_address, mask):
        self.address_pool_starting_ip_address = ip_address
        self.address_pool_mask = mask

    @staticmethod
    def update_ip_splitter(ip_1, ip_2, ip_3, ip_4, inf_limit=0, sup_limit=256):
        ip_4 += 1
        if ip_4 == sup_limit:
            ip_4 = inf_limit
            ip_3 += 1
        if ip_3 == sup_limit:
            ip_3 = inf_limit
            ip_2 += 1
        if ip_2 == sup_limit:
            ip_2 = inf_limit
            ip_1 += 1
        if ip_1 == sup_limit:
            ip_1 = inf_limit
        return ip_1, ip_2, ip_3, ip_4

    def set_server_name(self, value):
        self.name = value

    def set_server_lease_time(self, value):
        self.lease_time = value
        self.renewal_time = value//2
        self.rebinding_time = value*7//8

    def set_address_pool(self):
        self.address_pool, self.address_pool_broadcast = self.calculate_address_pool(self.address_pool_starting_ip_address, self.address_pool_mask)
        for ip in self.address_pool.keys():
            self.old_mac_ip.update({ip: None})
        print(self.address_pool)

    @staticmethod
    def calculate_address_pool(starting_ip_address, mask):
        address_pool = {}
        number_of_addresses = 2 ** (32 - mask) - 2
        ip_1, ip_2, ip_3, ip_4 = [int(s) for s in starting_ip_address.split('.')]
        ip_1, ip_2, ip_3, ip_4 = DHCP_Server.update_ip_splitter(ip_1, ip_2, ip_3, ip_4)
        for i in range(number_of_addresses):
            address_pool.update({"{}.{}.{}.{}".format(ip_1, ip_2, ip_3, ip_4): {'mac': None, 'time': None}})
            ip_1, ip_2, ip_3, ip_4 = DHCP_Server.update_ip_splitter(ip_1, ip_2, ip_3, ip_4)
        address_pool_broadcast = "{}.{}.{}.{}".format(ip_1, ip_2, ip_3, ip_4)
        return address_pool, address_pool_broadcast

    def _get_old_mac_ip(self, mac_to_check):
        if mac_to_check in self.old_mac_ip.values():
            for ip, mac in self.old_mac_ip.items():
                if mac == mac_to_check:
                    return ip
        return None

    def _send_offer(self, dhcp_packet):
        dhcp_packet.message_type = DHCP_Message_Type.DHCP_OFFER
        old_ip = self._get_old_mac_ip(dhcp_packet.client_hardware_address)
        if old_ip:
            self.debug("Offering the old ip of {}".format(dhcp_packet.client_hardware_address))
            dhcp_packet.your_ip_address = old_ip
        else:
            available_address = self.get_free_address()
            if available_address is not None:
                dhcp_packet.your_ip_address = available_address
            else:
                self.debug("Can't offer any ip.")
                return

        self.debug("Sending DHCP_OFFER")
        self.debug_packet(dhcp_packet)
        message = dhcp_packet.encode()
        self.server_socket.sendto(message, self.dest)

    def _send_acknowledge(self, dhcp_packet):
        self.debug("Sending DHCP_ACKNOWLEDGE")
        dhcp_packet.message_type = DHCP_Message_Type.DHCP_ACK
        dhcp_packet.client_ip_address = dhcp_packet.your_ip_address
        self.address_pool.update({dhcp_packet.client_ip_address: {'mac': dhcp_packet.client_hardware_address, 'time': datetime.datetime.now()}})
        self.old_mac_ip.update({dhcp_packet.client_ip_address: dhcp_packet.client_hardware_address})
        # self.server_socket.send(dhcp_packet.encode(), self.port)
        self.debug_packet(dhcp_packet)
        if self.gui:
            self.gui.update_frames_address_pool()

        message = dhcp_packet.encode()
        self.server_socket.sendto(message, self.dest)

    def _send_nacknowledge(self, dhcp_packet):
        self.debug("Sending DHCP_NEGATIVE_ACKNOWLEDGE")
        dhcp_packet.message_type = DHCP_Message_Type.DHCP_NAK
        self.debug_packet(dhcp_packet)

        message = dhcp_packet.encode()
        self.server_socket.sendto(message, self.dest)

    def _add_packet_options(self, dhcp_packet):
        dhcp_packet.opcode = DHCP_Opcode.REQUEST
        dhcp_packet.set_lease_time(self.lease_time)
        dhcp_packet.server_name = self.name
        dhcp_packet.broadcast_address = self.address_pool_broadcast
        dhcp_packet.set_subnet_mask(self.address_pool_mask)
        dhcp_packet.router = self.router
        dhcp_packet.dns = self.dns

    def _analyze_data(self, data: bytes):
        dhcp_packet = DHCP_PACKET(data, server_mode=True)
        print(dhcp_packet)
        if dhcp_packet.opcode != DHCP_Opcode.REQUEST:
            return
        if dhcp_packet.message_type == DHCP_Message_Type.DHCP_DISCOVER:
            self.debug("DHCP_DISCOVER received", endLine=True)
            self.debug_packet(dhcp_packet)

            if not self._mac_holds_an_addrees(dhcp_packet.client_hardware_address):
                self._add_packet_options(dhcp_packet)
                self._send_offer(dhcp_packet)
            else:
                self.debug("The chaddr {} has already one of my ip address".format(dhcp_packet.client_hardware_address), afterEndLine=True)
        elif dhcp_packet.message_type == DHCP_Message_Type.DHCP_REQUEST:
            self.debug("DHCP REQUEST received", endLine=True)
            self.debug_packet(dhcp_packet)

            self._add_packet_options(dhcp_packet)
            ip_address_to_check = dhcp_packet.your_ip_address if dhcp_packet.your_ip_address != '0.0.0.0' else dhcp_packet.client_ip_address
            if ip_address_to_check not in self.address_pool.keys():
                self.debug("{} is not in my pool".format(ip_address_to_check), afterEndLine=True)
                self._send_nacknowledge(dhcp_packet)
            elif self.ip_address_is_free(ip_address_to_check):
                if self._mac_holds_an_addrees(dhcp_packet.client_hardware_address):
                    self.debug("The chaddr {} has already another of my ip address".format(dhcp_packet.client_hardware_address), afterEndLine=True)
                    self._send_nacknowledge(dhcp_packet)
                else:
                    self.debug("The chaddr {} is now owner of the ip address {}".format(dhcp_packet.client_hardware_address, ip_address_to_check), afterEndLine=True)
                    self._send_acknowledge(dhcp_packet)
            else:
                if self.address_pool[ip_address_to_check]['mac'] != dhcp_packet.client_hardware_address:
                    self.debug("The ip address {} is taken by another client".format(ip_address_to_check), afterEndLine=True)
                    self._send_nacknowledge(dhcp_packet)
                else:
                    self.debug("Updating the lease time for mac {}".format(dhcp_packet.client_hardware_address), afterEndLine=True)
                    self._send_acknowledge(dhcp_packet)
        elif dhcp_packet.message_type == DHCP_Message_Type.DHCP_DECLINE:
            self.debug("DHCP DECLINE received", endLine=True)
            self.debug_packet(dhcp_packet)
        elif dhcp_packet.message_type == DHCP_Message_Type.DHCP_RELEASE:
            self.debug("DHCP RELEASE received", endLine=True)
            self.address_pool.update({dhcp_packet.client_ip_address: {'mac': None, 'time': None}})
            self.gui.update_frames_address_pool()
            self.debug_packet(dhcp_packet)
        elif dhcp_packet.message_type == DHCP_Message_Type.DHCP_INFORM:
            self.debug("DHCP INFORM received", endLine=True)
            self.debug_packet(dhcp_packet)

    def start_server(self):
        self.debug("{} has started".format(self.name))

        try:
            self.server_socket.bind(('', server_port))
        except OSError:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.server_socket.bind(('', server_port))
        self.server_is_shut_down = False

        import threading
        update_pool_thread = threading.Thread(target=self._update_address_pool)
        update_pool_thread.daemon = True
        update_pool_thread.start()

        while self.running_flag:
            self.debug("{} is waiting for requests ...".format(self.name))
            import select
            ready = select.select([self.server_socket], [], [], recv_timeout)
            if ready[0]:
                data, address = self.server_socket.recvfrom(MAX_BYTES)
                print(address)
                self.debug("{} is analyzing the request".format(self.name))
                self._analyze_data(data)
        self.server_is_shut_down = True
        self.debug("{} is saving address pool to 'address_pool.json'".format(self.name))
        self.save_address_pool_to_json()
        self.debug("{} has stopped".format(self.name))

    def _mac_holds_an_addrees(self, mac):
        return any(mac in ip_info.values() for ip_info in self.address_pool.values())

    def get_free_address(self):
        print(self.address_pool)
        for ip, ip_info in self.address_pool.items():
            if ip_info['mac'] is None:
                return ip
        return None

    def ip_address_is_free(self, ip):
        if self.address_pool[ip]['mac'] is None:
            return True
        return False

    def set_flag(self, param):
        self.running_flag = param

    def debug(self, param, endLine = False, afterEndLine = False):
        if self.gui:
            datetime_object = datetime.datetime.now()
            printable = "{} : {}\n".format(datetime_object, param)
            if endLine:
                self.gui.frames['ServerStartPage'].server_status_text.insert(tk.END, "\n")
            self.gui.frames['ServerStartPage'].server_status_text.insert(tk.END, printable)
            if afterEndLine:
                self.gui.frames['ServerStartPage'].server_status_text.insert(tk.END, "\n")

        log.info(param)

    def debug_packet(self, packet):
        if self.gui and self.show_packets_debug:
            self.gui.frames['ServerStartPage'].server_status_text.insert(tk.END, '\n' + str(packet) + '\n')

    def _update_address_pool(self, time_sleep=3):
        import time
        while self.running_flag:
            for ip, ip_info in self.address_pool.items():
                if ip_info['mac'] is not None and ip_info['time'] is not None:
                    if self.lease_time <= (datetime.datetime.now() - ip_info['time']).total_seconds():
                        self.debug("Lease time of {} for user {} has expired".format(ip, ip_info['mac']), afterEndLine=True)
                        self.address_pool.update({ip: {'mac': None, 'time': None}})
                        self.gui.update_frames_address_pool()
            time.sleep(time_sleep)

    def save_address_pool_to_json(self):
        import json
        with open('address_pool.json', 'w') as file:
            log.info("Saving address pool status to address_pool.json")
            file.write(json.dumps(self.address_pool, indent=2, sort_keys=True, default=str))
        with open('old_mac.json', 'w') as file:
            log.info("Saving old mac history to old_mac.json")
            file.write(json.dumps(self.old_mac_ip, indent=2, sort_keys=True, default=str))

    def load_address_pool_from_json(self, path_pool='address_pool.json', path_old_mac='old_mac.json'):
        import json
        import math
        import ipaddress
        try:
            with open(path_pool, 'r') as file:
                log.info("Loading address pool status to address_pool.json")
                self.address_pool = json.load(file)
                for item in self.address_pool.values():
                    if item['time'] is not None:
                        item['time'] = datetime.datetime.strptime(item['time'], '%Y-%m-%d %H:%M:%S.%f')
                self.address_pool_mask = 32 - int(math.log(len(self.address_pool.keys()) + 2, 2))
                host = ipaddress.IPv4Address(list(self.address_pool.keys())[0])
                net = ipaddress.IPv4Network(list(self.address_pool.keys())[0] + '/' + str(self.address_pool_mask), False)
                self.address_pool_starting_ip_address = str(ipaddress.IPv4Address(int(host) & int(net.netmask)))
                self.address_pool_broadcast = str(net.broadcast_address)
                log.info("Setting mask: {}".format(self.address_pool_mask))
                log.info("Setting network address: {}".format(self.address_pool_starting_ip_address))
                log.info("Setting network broadcast address: {}".format(self.address_pool_broadcast))
            with open(path_old_mac, 'r') as file:
                log.info("Loading old mac history to old_mac.json")
                self.old_mac_ip = json.load(file)
        except json.decoder.JSONDecodeError:
            log.info("JSON corrupted or empty")
