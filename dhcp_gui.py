import socket
import sys
import threading
import tkinter as tk
from tkinter import font as tkfont, messagebox
import logging as log
from dhcp_server import DHCP_Server

FORMAT = '[%(asctime)s] [%(levelname)s] : %(message)s'
log.basicConfig(stream=sys.stdout, level=log.DEBUG, format=FORMAT)

class DHCP_Server_GUI(tk.Tk):
    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold")
        self.text_label_title = tkfont.Font(family='Helvetica', size=12)
        self.button_text_font = tkfont.Font(family='Times', size=11)
        self.text_label = tkfont.Font(family='Arial', size=11)
        # the container is where we'll stack a bunch of frames
        # on top of each other, then the one we want visible
        # will be raised above the others
        self.title("DHCP SERVER")
        container = tk.Frame(self)
        container.pack(side="top", fill=tk.BOTH, expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F in (ServerStartPage, ServerConfigurationsPage):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame

            # put all of the pages in the same location;
            # the one on the top of the stacking order
            # will be the one that is visible.
            frame.grid(row=0, column=0, sticky="nsew")
        self.frames['ServerStartPage'].set_other_page(self.frames['ServerConfigurationsPage'])
        self.frames['ServerConfigurationsPage'].set_other_page(self.frames['ServerStartPage'])
        self.show_frame("ServerConfigurationsPage")
        self.dhcp_server = DHCP_Server()

    def start_server(self):
        self.server_thread = threading.Thread(target=self.dhcp_server.start_server)
        self.server_thread.daemon = True
        self.dhcp_server.set_flag(True)
        self.server_thread.start()

    def stop_server(self):
        self.dhcp_server.set_flag(False)

    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()

    def gui_exit(self):
        log.info('Stopping Server')
        self.dhcp_server.set_flag(1)
        exit()


class ServerPage(tk.Frame):
    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent, bg="#101010")
        self.controller = controller
        self.other_page = None

    def set_other_page(self, other_page):
        self.other_page = other_page


class ServerStartPage(ServerPage):
    def __init__(self, parent, controller):
        ServerPage.__init__(self, parent, controller)
        self.init_window()

    def init_window(self, button_bg='#222222', button_fg='#ffffff', label_bg='#303030', label_txt='yellow', txt_color='#00FF41'):
        # --------------------------------TOP FRAME----------------------------------
        tk.Label(master=self, text='DHCP SERVER', bg=self["bg"], fg=label_txt,font=self.controller.title_font).pack(side=tk.TOP)

        # --------------------------------BOTTOM FRAME----------------------------------
        server_frame = tk.Frame(master=self, bg="#050505")
        server_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=0)

        # Space for Server configurations Button
        tk.Grid.columnconfigure(server_frame, 0, weight=1)

        tk.Button(server_frame, text="Server Configurations", width=20, bg=button_bg, fg=button_fg, command=lambda: self.controller.show_frame("ServerConfigurationsPage")).grid(row=0, column=0, padx=5, pady=5)
        self.start_server_button = tk.Button(server_frame, text="Start Server", width=10, bg=button_bg, fg=button_fg, command=self.start_server, font=self.controller.button_text_font)
        self.start_server_button.grid(row=0, column=1, padx=5, pady=5)
        self.start_server_button['state'] = tk.DISABLED

        self.stop_server_button = tk.Button(server_frame, text="Stop Server", width=10, bg=button_bg, fg=button_fg, command=self.stop_server, font=self.controller.button_text_font)
        self.stop_server_button.grid(row=0, column=2, padx=5, pady=5)
        self.stop_server_button['state'] = tk.DISABLED

        tk.Button(server_frame, text="Close", width=10, command=self.controller.gui_exit, bg=button_bg, fg=button_fg, font=self.controller.button_text_font) \
            .grid(row=0, column=3, padx=5, pady=5)

        # --------------------------------RIGHT FRAME-----------------------------------
        server_info_frame = tk.Frame(master=self, bg="#101010")
        server_info_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=1, padx=5, pady=5)
        server_info_label = tk.LabelFrame(server_info_frame, text="Server Info", bg=label_bg, fg=label_txt, font=self.controller.text_label_title)
        server_info_label.grid(row=0, column=0, padx=10, pady=10)

        self.server_name_label_var = tk.StringVar()
        self.server_name_label_var.set("unknown")
        tk.Label(server_info_label, text="Server Name: ", bg=server_info_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=0, column=0, sticky='w')
        tk.Label(server_info_label, textvariable=self.server_name_label_var, bg=server_info_label["bg"], fg=button_fg, font=self.controller.text_label).grid(row=0, column=1, sticky='w')

        self.lease_time_label_var = tk.StringVar()
        self.lease_time_label_var.set("unknown")
        tk.Label(server_info_label, text="Lease Time: ", bg=server_info_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=1, column=0, sticky='w')
        tk.Label(server_info_label, textvariable=self.lease_time_label_var, bg=server_info_label["bg"], fg=button_fg, font=self.controller.text_label).grid(row=1, column=1, sticky='w')

        # --------------------------------LEFT FRAME----------------------------------
        address_pool_frame = tk.Frame(master=self, bg="#101010")
        address_pool_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=1, padx=5, pady=5)

        address_pool_label = tk.LabelFrame(address_pool_frame, text="Address Pool", bg=label_bg, fg='yellow', font=self.controller.text_label_title)
        address_pool_label.grid(row=0, column=0, padx=10, pady=10, sticky='w')

        self.ip_address_label_var = tk.StringVar()
        self.ip_address_label_var.set("unknown")
        tk.Label(address_pool_label, text="IP Address: ", bg=address_pool_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=0, column=0, sticky='w')
        tk.Label(address_pool_label, textvariable=self.ip_address_label_var, bg=address_pool_label["bg"], fg=button_fg, font=self.controller.text_label).grid(row=0, column=1, sticky='w')

        self.mask_label_var = tk.StringVar()
        self.mask_label_var.set("unknown")
        tk.Label(address_pool_label, text="Mask: ", bg=address_pool_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=1, column=0, sticky='w')
        tk.Label(address_pool_label, textvariable=self.mask_label_var, bg=address_pool_label["bg"], fg=button_fg, font=self.controller.text_label).grid(row=1, column=1, sticky='w')

        self.ip_address_pool_text = tk.Text(address_pool_frame, height=10, width=40)
        ip_address_pool_scroll = tk.Scrollbar(address_pool_frame, command=self.ip_address_pool_text.yview)
        self.ip_address_pool_text['yscrollcommand'] = ip_address_pool_scroll.set
        self.ip_address_pool_text.grid(row=2, column=0, sticky=tk.N+tk.S)
        ip_address_pool_scroll.grid(row=2, column=1, sticky=tk.N+tk.S+tk.W)

    def start_server(self):
        self.start_server_button['state'] = tk.DISABLED
        self.stop_server_button['state'] = tk.NORMAL
        self.other_page.set_pool_address_button['state'] = tk.DISABLED
        self.controller.start_server()

    def activate_start_button(self):
        while self.controller.dhcp_server.server_is_shut_down is not True:
            pass
        self.start_server_button['state'] = tk.NORMAL

    def stop_server(self):
        self.stop_server_button['state'] = tk.DISABLED
        self.other_page.set_pool_address_button['state'] = tk.NORMAL
        self.controller.stop_server()
        activate_btn_thread = threading.Thread(target=self.activate_start_button)
        activate_btn_thread.daemon = True
        activate_btn_thread.start()

class ServerConfigurationsPage(ServerPage):
    def __init__(self, parent, controller):
        ServerPage.__init__(self, parent, controller)
        self.init_window()

    def init_window(self, button_bg='#222222', button_fg='#ffffff', label_bg='#303030', label_txt='yellow', txt_color='#00FF41'):
        #--------------------------------TOP FRAME----------------------------------
        tk.Label(master=self, text='DHCP SERVER Configurations', bg=self["bg"], fg=label_txt, font=self.controller.title_font).pack(side=tk.TOP)

        #--------------------------------BOTTOM FRAME----------------------------------
        server_frame = tk.Frame(master=self, bg="#050505")
        server_frame.pack(side=tk.BOTTOM, fill=tk.X, expand=0)

        #Space for Server configurations Button
        tk.Grid.columnconfigure(server_frame, 0, weight=1)

        tk.Button(server_frame, text="Server Start Page", width=20, bg=button_bg, fg=button_fg, font=self.controller.button_text_font,
                  command=lambda: self.controller.show_frame("ServerStartPage")).grid(row=0, column=0, padx=5, pady=5)

        # --------------------------------LEFT FRAME----------------------------------
        address_pool_frame = tk.Frame(master=self, bg="#101010")
        address_pool_frame.pack(side=tk.LEFT, fill=tk.Y, expand=1)

        address_pool_label = tk.LabelFrame(address_pool_frame, text="Address Pool", bg=label_bg, fg=label_txt, font=self.controller.text_label_title)
        address_pool_label.grid(row=0, column=0, padx=10, pady=10)

        tk.Label(address_pool_label, text='IP Address', bg=address_pool_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=0, column=0)
        self.ip_address_entry = tk.Entry(address_pool_label, width=30)
        self.ip_address_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Label(address_pool_label, text='Mask', bg=address_pool_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=1, column=0)
        self.mask_entry = tk.Entry(address_pool_label, width=30)
        self.mask_entry.grid(row=1, column=1, padx=5, pady=5)

        self.ip_address_entry.insert(0, '10.1.0.127')
        self.mask_entry.insert(0, '/29')
        self.set_pool_address_button = tk.Button(address_pool_label, text='Set Pool Address', command=self.set_pool_address, bg=button_bg, fg=button_fg, font=self.controller.button_text_font)
        self.set_pool_address_button.grid(row=2, padx=5, pady=5, columnspan=2)

        self.ip_address_pool_text = tk.Text(address_pool_frame, height=10, width=40)
        ip_address_pool_scroll = tk.Scrollbar(address_pool_frame, command=self.ip_address_pool_text.yview)
        self.ip_address_pool_text['yscrollcommand'] = ip_address_pool_scroll.set
        self.ip_address_pool_text.grid(row=3, column=0, sticky=tk.N+tk.S)
        ip_address_pool_scroll.grid(row=3, column=1, sticky=tk.N+tk.S+tk.W)

        # --------------------------------RIGHT FRAME----------------------------------
        widget_frame = tk.Frame(master=self, bg="#101010")
        widget_frame.pack(side=tk.RIGHT, fill=tk.Y, expand=1)

        #set server name
        server_name_label_frame = tk.LabelFrame(widget_frame, text="Server Name", bg=label_bg, fg=label_txt, font=self.controller.text_label_title)
        server_name_label_frame.grid(row=0, column=0, padx=10, pady=10)
        tk.Label(server_name_label_frame, text='Server Name', bg=address_pool_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=0, column=0)
        self.server_name_entry = tk.Entry(server_name_label_frame, width=30)
        self.server_name_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Button(server_name_label_frame, text='Set Server Name', bg=button_bg, fg=button_fg, font=self.controller.button_text_font, command=self.set_server_name).grid(row=2, padx=5, pady=5, columnspan=2)

        #Set Lease Time
        lease_time_label_frame = tk.LabelFrame(widget_frame, text="Lease Time", bg='#303030', fg='yellow', font=self.controller.text_label_title)
        lease_time_label_frame.grid(row=1, column=0, padx=10, pady=10)
        tk.Label(lease_time_label_frame, text='Lease Time', bg=address_pool_label["bg"], fg=txt_color, font=self.controller.text_label).grid(row=1, column=0)
        self.lease_time_entry = tk.Entry(lease_time_label_frame, width=30)
        self.lease_time_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        tk.Button(lease_time_label_frame, text='Set Lease Time', bg=button_bg, fg=button_fg, font=self.controller.button_text_font, command=self.set_server_lease_time).grid(row=2, padx=5, pady=5, columnspan=2)
        self.server_name_entry.insert(0, "DHCP Server")
        self.lease_time_entry.insert(0, "600")

    @staticmethod
    def _get_ip_network_of_ipv4(ipv4, mask):
        import ipaddress
        return str(ipaddress.ip_interface(ipv4 + '/' + str(mask)).network).split('/')[0]

    def set_pool_address(self):
        mask = self.mask_entry.get()
        ip = self.ip_address_entry.get()
        log.info("Set pool address")
        try:
            socket.inet_aton(ip)
            if mask == '':
                raise ValueError
            if mask[0] == '/':
                mask_result = int(mask[1:])
            else:
                mask_result = int(mask)
            if mask_result < 1 or mask_result > 32:
                raise ValueError
            starting_ip = self._get_ip_network_of_ipv4(ip, mask_result)
            self.other_page.ip_address_label_var.set(starting_ip)
            self.other_page.mask_label_var.set("/{}".format(mask_result))
            self.controller.dhcp_server.set_address_pool_config(starting_ip, mask_result)
            self.controller.dhcp_server.set_address_pool()
            self.ip_address_pool_text.delete(1.0, tk.END)
            self.ip_address_pool_text.insert(tk.END, "Net Address : {}\n".format(starting_ip))
            self.ip_address_pool_text.insert(tk.END, "Broadcast Address : {}\n".format(self.controller.dhcp_server.address_pool_broadcast))
            for key, value in self.controller.dhcp_server.address_pool.items():
                self.ip_address_pool_text.insert(tk.END, key + '\n')

            self.other_page.ip_address_pool_text.insert(tk.END, "Net Address : {}\n".format(starting_ip))
            self.other_page.ip_address_pool_text.insert(tk.END, "Broadcast Address : {}\n".format(
            self.other_page.controller.dhcp_server.address_pool_broadcast))
            for key, value in self.controller.dhcp_server.address_pool.items():
                self.other_page.ip_address_pool_text.insert(tk.END, key + '\n')

            if self.other_page.server_name_label_var.get() != "unknown" and self.other_page.lease_time_label_var != "unknown":
                self.other_page.start_server_button['state'] = tk.NORMAL

        except socket.error:
            messagebox.showinfo("IP Format error", "IP Format: x.x.x.x where x = 0-255")
        except ValueError:
            messagebox.showinfo("Mask Format error", "Mask Format: x or \\x, where x = 1-32")

    def set_server_name(self):
        server_name = self.server_name_entry.get()
        log.info("Set Server Name: {}".format(server_name))
        self.other_page.server_name_label_var.set(server_name)
        self.controller.dhcp_server.set_server_name(server_name)
        if self.other_page.mask_label_var.get() != "unknown" and self.other_page.lease_time_label_var.get() != "unknown":
            self.other_page.start_server_button['state'] = tk.NORMAL

    def set_server_lease_time(self):
        lease_time = self.lease_time_entry.get()
        log.info("Set Lease Time: {}".format(lease_time))
        self.other_page.lease_time_label_var.set(lease_time)
        self.controller.dhcp_server.set_server_lease_time(int(lease_time))
        if self.other_page.server_name_label_var.get() != "unknown" and self.other_page.mask_label_var.get() != "unknown":
            self.other_page.start_server_button['state'] = tk.NORMAL
