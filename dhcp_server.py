import logging as log
import socket
import sys
from dhcp_packet import DHCP_PACKET, DHCP_Packet_Type

FORMAT = '[%(asctime)s] [%(levelname)s] : %(message)s'
log.basicConfig(stream=sys.stdout, level=log.DEBUG, format=FORMAT)

server_port = 67
client_port = 68
MAX_BYTES = 1024
recv_timeout = 5

class DHCP_Server:
    def __init__(self):
        self.ip = '0.0.0.0'
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.dest = ('255.255.255.255', client_port)
        self.running_flag = True
        self.server_is_shut_down = True
        self.name = None
        self.address_pool = {}
        self.address_pool_starting_ip_address = None
        self.address_pool_mask = None
        self.address_pool_broadcast = None
        self.lease_time = None
        #self.set_address_pool('10.0.0.1', 10)

    def set_address_pool_config(self, ip_address, mask):
        self.address_pool_starting_ip_address = ip_address
        self.address_pool_mask = mask

    @staticmethod
    def _update_ip_splitter(ip_1, ip_2, ip_3, ip_4, inf_limit=0, sup_limit=256):
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

    def get_server_name(self):
        return self.name

    def set_server_name(self, value):
        self.name = value

    def set_server_lease_time(self, value):
        self.lease_time = value

    def set_address_pool(self):
        self.address_pool = {}
        number_of_addresses = 2**(32-self.address_pool_mask)-2
        ip_1, ip_2, ip_3, ip_4 = [int(s) for s in self.address_pool_starting_ip_address.split('.')]
        ip_1, ip_2, ip_3, ip_4 = self._update_ip_splitter(ip_1, ip_2, ip_3, ip_4)
        for i in range(number_of_addresses):
            self.address_pool.update({"{}.{}.{}.{}".format(ip_1, ip_2, ip_3, ip_4): None})
            ip_1, ip_2, ip_3, ip_4 = self._update_ip_splitter(ip_1, ip_2, ip_3, ip_4)
        self.address_pool_broadcast = "{}.{}.{}.{}".format(ip_1, ip_2, ip_3, ip_4)
        print(self.address_pool)

    def _send_offer(self, dhcp_packet):
        log.info("Sending DHCP_OFFER")
        dhcp_packet.message_type = DHCP_Packet_Type.DHCP_OFFER
        available_address = self.get_free_address()
        if available_address is not None:
            dhcp_packet.your_ip_address = available_address
        message = dhcp_packet.encode()
        self.server_socket.sendto(message, self.dest)

    def _send_acknowledge(self, dhcp_packet):
        log.info("Sending DHCP_ACKNOWLEDGE")
        dhcp_packet.message_type = DHCP_Packet_Type.DHCP_ACK
        dhcp_packet.client_ip_address = dhcp_packet.your_ip_address
        self.address_pool.update({dhcp_packet.client_ip_address: dhcp_packet.client_hardware_address})
        # self.server_socket.send(dhcp_packet.encode(), self.port)
        message = dhcp_packet.encode()
        self.server_socket.sendto(message, self.dest)

    def _send_nacknowledge(self, dhcp_packet):
        log.info("Sending DHCP_NEGATIVE_ACKNOWLEDGE")
        dhcp_packet.message_type = DHCP_Packet_Type.DHCP_NAK
        message = dhcp_packet.encode()
        self.server_socket.sendto(message, self.dest)

    def _analyze_data(self, data: bytes):
        dhcp_packet = DHCP_PACKET(data)
        print(dhcp_packet)
        if dhcp_packet.message_type == DHCP_Packet_Type.DHCP_DISCOVER:
            log.info("DHCP_DISCOVER received")
            self._send_offer(dhcp_packet)
        elif dhcp_packet.message_type == DHCP_Packet_Type.DHCP_REQEUST:
            log.info("DHCP REQUEST received")
            if self.ip_address_is_free(dhcp_packet.your_ip_address):
                self._send_acknowledge(dhcp_packet)
            else:
                self._send_nacknowledge(dhcp_packet)

    def start_server(self):
        log.info("DHCP Server with name '{}' has started".format(self.name))

        try:
            self.server_socket.bind(('', server_port))
        except OSError:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.server_socket.bind(('', server_port))
        self.server_is_shut_down = False

        while self.running_flag:
            log.info("DHCP Server with name '{}' is waiting for requests ...".format(self.name))
            import select
            ready = select.select([self.server_socket], [], [], recv_timeout)
            if ready[0]:
                data, address = self.server_socket.recvfrom(MAX_BYTES)
                print(address)
                log.info("DHCP Server with name '{}' is analyzing the request".format(self.name))
                self._analyze_data(data)
        self.server_is_shut_down = True
        log.info("DHCP Server with name '{}' has stopped".format(self.name))


    def get_free_address(self):
        print(self.address_pool)
        for ip, mac in self.address_pool.items():
            if mac is None:
                return ip
            return None

    def ip_address_is_free(self, ip):
        if self.address_pool[ip] is None:
            return True
        return False

    def set_flag(self, param):
        self.running_flag = param

