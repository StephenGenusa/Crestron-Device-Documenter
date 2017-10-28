#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
Copyright © 2017 by Stephen Genusa

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
this list of conditions and the following disclaimer in the documentation
and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
"""

from __future__ import print_function
import argparse
import os
import re
import socket
import subprocess
import sys
import textwrap
import webbrowser
from time import sleep
#
import netifaces
import paramiko
#import hexdump
#import pprint

SSH_PORT = 22
CIP_PORT = 41794
CTP_PORT = 41795
MAX_RETRIES = 3
BUFF_SIZE = 20000
CR = "\r"
BROADCAST_IP = '255.255.255.255'
UDP_MSG = "\x14\x00\x00\x00\x01\x04\x00\x03\x00\x00\x66\x65\x65\x64" + \
    ("\x00" * 252)


class CrestronDeviceDocumenter(object):
    """
    Attempt to identify all commands on a Crestron device
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, args):
        """
        initialize internal properties
        """
        self.active_ips_to_check = []
        if args.iptocheck:
            self.active_ips_to_check.append(args.iptocheck)
        self.preseed_command_list = []
        self.possible_commands_filename = args.addtestcommands
        self.preseed_commands_filename = "preseed.upc"
        self.do_not_execute_commands_filename = "donotexec.upc"
        self.do_not_execute_command_list = []
        self.firmwareversion = ""
        self.console_prompt = ""
        self.htmldocfilename = ""
        self.unpublished_commands_filename = ""
        self.args = args

    def initialize_run_variables(self):
        self.console_prompt = ""
        self.firmwareversion = ""
        self.help_dict = {}
        self.pub_command_list = []
        self.hidden_command_list = []
        self.unpublished_command_list = []
        self.htmldocfilename = ""
        self.unpublished_commands_filename = ""


    def place_on_win_clipboard(self, text_to_clipboard):
        """
        For testing of regular expressions
        """
        from Tkinter import Tk
        r = Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text_to_clipboard)
        r.update()
        r.destroy()


    def print_debug_data(self, data, msg):
        """
        debug printing of data
        """
        print("*" * 35, msg, "*" * 35)
        print(data)
        print("*" * 35, msg, "*" * 35)
        print("\n")


    def build_list_of_activeips(self, subnet):
        """
        Build a list of devices that respond to ping for a /24 subnet like 17.1.6.{1}:
        """
        print ("Building list of active IP addresses on subnet {0}.0/24\nPlease wait...".format(subnet))
        with open(os.devnull, "wb") as limbo:
            for last_octet in xrange(1, 255):
                ip = "{0}.{1}".format(subnet, last_octet)
                result = subprocess.Popen(["ping", "-n", "1", "-w", "200", ip],
                         stdout=limbo, stderr=limbo).wait()
                if not result:
                    self.active_ips_to_check.append(ip)
            if self.active_ips_to_check:
                print("Located {0} active IPs on subnet".format(len(self.active_ips_to_check)))


    def build_list_of_crestronips(self):
        """
        Build a list of Crestron devices that respond to a UDP message
        """
        for iface in netifaces.interfaces():
            if netifaces.AF_INET in netifaces.ifaddresses(iface):
                # This works better than current version of Crestron Toolbox's Device Discovery
                if 'broadcast' in netifaces.ifaddresses(iface)[netifaces.AF_INET][0] and \
                   'addr' in netifaces.ifaddresses(iface)[netifaces.AF_INET][0]:
                    cur_ip = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['addr']
                    loc_bcast_ip = netifaces.ifaddresses(iface)[netifaces.AF_INET][0]['broadcast']
                    print("Testing IP subnet", cur_ip)
                    for bcast_ip in [BROADCAST_IP, loc_bcast_ip]:
                        udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        udp_sock.bind((cur_ip, CIP_PORT))
                        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                        udp_sock.sendto(UDP_MSG, (bcast_ip, CIP_PORT))
                        udp_sock.settimeout(2.0)
                        try:
                            while True:
                                data, addr = udp_sock.recvfrom(4096)
                                search = re.findall ('\x00([a-zA-Z0-9-]{2,30})\x00', data[9:40])
                                if search:
                                    dev_name = search[0]
                                    dev_ip = addr[0]
                                    if cur_ip != dev_ip and dev_ip not in self.active_ips_to_check and dev_name is not "feed":
                                        self.active_ips_to_check.append(dev_ip)
                        except Exception, e:
                            #print ("The exception was: %s" % e) //timed out
                            pass
        total_dev_count = len(self.active_ips_to_check)
        print ("\nLocated a total of {0} Crestron".format(total_dev_count), "device" if total_dev_count == 1 else "devices")


    def open_device_connection(self):
        """
        Open the device connection, attempting port 41795
        """
        SOCKET_TIMEOUT = 5.0

        if not self.args.forcessh:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_address = (self.device_ip_address, 41795)
                self.sock.settimeout(SOCKET_TIMEOUT)
                print("Attempting to connect to {0} port {1}".format(self.device_ip_address, CTP_PORT))
                self.sock.connect(server_address)
                self.usingssh = False
                return True
            except:
                pass
        else:
            self.sshclient = paramiko.client.SSHClient()
            try:
                self.sshclient.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.sshclient.load_system_host_keys()
                print("Attempting to connect to {0} port {1}".format(self.device_ip_address, SSH_PORT))
                self.sshclient.connect(self.device_ip_address, port=22, username=self.args.username, password=self.args.password, timeout=SOCKET_TIMEOUT)
                self.usingssh = True
                return True
            except:
                print("Error: Unable to connect to device.")
        return False


    def close_device_connection(self):
        """
        Close the socket
        """
        try:
            print("\nProcess complete.")
            if self.usingssh:
                self.sshclient.close()
            else:
                self.sock.close()
        except:
            pass


    def get_console_prompt(self):
        """
        Determine the device console prompt
        """
        data = ""
        #try:
        for _unused in range(0, MAX_RETRIES):
            if self.usingssh:
                stdin,stdout,stderr=self.sshclient.exec_command("ver")
                data = str(stdout.readlines())
                search = re.findall("([\w-]{3,30})\ ", data, re.MULTILINE)
            else:
                self.sock.sendall(CR)
                data += self.sock.recv(BUFF_SIZE)
                search = re.findall("[\n\r]([\w-]{3,30})>", data, re.MULTILINE)
            
            sleep(.25)
            #self.place_on_win_clipboard(data)
            #print(hexdump.hexdump(data))
            if search:
                self.console_prompt = search[0]
                self.unpublished_commands_filename = self.console_prompt + ".upc"
                print("Console prompt is", self.console_prompt)
                if self.console_prompt == "MERCURY":
                    print("Mercury currently unsupported due to Crestron engin.err.uity")
                    exit()
                return True
        #except:
        #    pass
        print("Console prompt not found on device.")
        return False


    def remove_prompt(self, data, char_limit):
        """
        Remove the console prompt from the text within the specified character limit
        """
        prompt_pos = data.find(self.console_prompt+">")
        if prompt_pos < char_limit:
            data = data.replace(self.console_prompt+">", "", 1)
        if char_limit == -1:
            data = data.replace(self.console_prompt+">", "")
        return data


    def send_command_wait_prompt(self, command, waitforpromptlocation):
        """
        Send a command and wait for the console prompt following the specified location
        """
        if self.usingssh:
            stdin,stdout,stderr=self.sshclient.exec_command(command)
            data = stdout.readlines()
            data = "".join(data)
        else:
            message = CR + command + CR
            self.sock.sendall(message)
            data = ""
            sleep(0.2)
            waitcount = 0
            data = self.sock.recv(BUFF_SIZE)
            data = data.replace(message, "")
            while data.find(self.console_prompt, waitforpromptlocation) == -1:
                # Deal with newer firmware that executes commands / doesn't return a prompt
                #   instead of printing help
                try:
                    sleep(0.2)
                    data += self.sock.recv(BUFF_SIZE)
                except:
                    self.sock.sendall(CR)
                waitcount += 1
                if waitcount == 5:
                    self.sock.sendall(CR)
                    waitcount = 0
        return data


    def get_firmware_version(self):
        """
        Get the firmware version of the device
        """
        data = self.send_command_wait_prompt("ver", 40)
        if not self.usingssh:
            data = data.replace(self.console_prompt + ">", "")
            search = re.search(r"[\r\n]{1,2}([\w\[\]\.\ \(\),#@-]{20,90})[\r\n]{1,2}", data, re.MULTILINE)
            if search:
                self.firmwareversion = search.group().strip()
        else:
            self.firmwareversion = data.strip()
        print("Firmware version ", self.firmwareversion)


    def get_command_help(self, command):
        """
        Get the help text for a command
        """
        if command in self.do_not_execute_command_list:
            return self.help_dict[cmd]
        
        message = command + " ?"
        data = self.send_command_wait_prompt(message, 30)
        if data.upper().find("BAD COMM") > -1 or data.upper().find("INCOMPLETE COMM") > -1:
            return ""
        if data.find("Authentication is not on. Command not allowed.") > -1 or \
           data.find("ERROR: Command Blocked from this console type.") > -1 or \
           data == "":
            return "No help available for this command."
        help_text = ""
        if not self.usingssh:
            search = re.findall(r"[\r\n]{1,2}(.{5," + str(len(data)) + "})[\r\n]{1,2}" + \
                    self.console_prompt + ">", data, re.M|re.S)
            if search:
                help_text = search[0].replace(self.console_prompt + ">", ""). \
                            replace(">", "&gt;").replace("<", "&lt;")
                if help_text.find(message, 1, 30) > -1:
                    help_text = help_text[len(message) + 2:]
        else:
            help_text = data.replace("\r\n\r\n", "\r\n")
        reformatted_help_text = ""
        for line in help_text.split("\n"):
            reformatted_help_text += textwrap.fill(line, 150) + "\n"
        return reformatted_help_text


    def get_command_categories(self):
        """
        Get a list of the command categories
        Not currently used
        """
        print("Getting command categories")
        data = self.send_command_wait_prompt("hidhelp", 20)
        data = data[12:]
        category_list = []
        category_desc = []
        search = re.findall(r"^HELP ([A-Za-z]{2,20})\ will\ (.{10,100})$", data,
                            re.M)
        if search:
            for find in search:
                if find[0] != "ALL":
                    category_list.append(find[0])
                    category_desc.append(find[1])


    def get_categorial_command_list(self, category):
        """
        Get a list of the commands in a given category
        Not currently used
        """
        print("\n\nGetting categorial commandset", category)
        message = CR + "hidhelp " + category
        data = self.send_command_wait_prompt(message, 30)
        data = data[len(message)+4:]
        command_list = []
        help_desc = []
        search = re.findall("^(.{1,200})$", data, re.M)
        if search:
            for find in search:
                search2 = re.findall(r"^(\w{2,25})\ *(\w{7,19}|User\ or\ Connect)?\ *(.{1,120})$", find, re.M|re.S)
                if search2:
                    command_list.append(search2[0][0].strip())
                    help_desc.append(search2[0][2].strip())
            if not command_list:
                print("[None]")


    def get_help_list(self, help_command, command_list, command_dict):
        """
        Get a list of the normal/published commands
        """
        data = self.send_command_wait_prompt(help_command, 30)
        data = data.replace(help_command, "")
        data = self.remove_prompt(data, 100)
        data = self.remove_prompt(data, -1)
        if data.find("\r\n"):
            data = data.replace("\r\n", "\r").replace("\r", "\n")
        if data.find("Bad") > -1 or data.find("Incomplete Command") > -1:
            return
        search = re.findall(r"\n(.{1,200}?)(?=\n)", data, re.MULTILINE)
        if search:
            for find in search:
                search2 = re.findall(r"(\w{2,25})\ *(Programmer|Operator|Administrator|User\ or\ Connect)?\ *(.{1,120})", find, re.MULTILINE)
                if search2:
                    command = search2[0][0].strip()
                    if command not in command_list and command <> "Add":
                        command_list.append(command)
                        if command not in command_dict:
                            command_dict[command] = search2[0][2].strip()


    def get_published_command_list(self):
        """
        Get a list of the normal/published commands
        """
        print("Getting Normal Commandset")
        self.get_help_list("help all", self.pub_command_list, self.help_dict)
        print("Found", len(self.pub_command_list), "Normal commands")


    def get_hidden_command_list(self):
        """
        Get a list of the hidden commands
        """
        print("Getting Hidden Commandset (if available)")
        self.get_help_list("hidhelp all", self.hidden_command_list, self.help_dict)
        if self.hidden_command_list:
            print("Found", len(self.hidden_command_list)-len(self.pub_command_list), "Hidden commands")


    def save_unpublished_command_list(self):
        """
        Save the unpublished commands for reuse
        """
        if self.unpublished_command_list:
            with open(self.unpublished_commands_filename, "w") as cmd_file:
                cmd_file.writelines(["%s\n" % item for item in self.unpublished_command_list])


    def load_preseed_command_list(self):
        """
        Load the preseed unpublished command list
        """
        if os.path.isfile(self.preseed_commands_filename):
            with open(self.preseed_commands_filename, "r") as cmd_file:
                upc_lines = cmd_file.readlines()
                self.preseed_command_list = [item.strip() for item in upc_lines if item.strip != ""]


    def save_preseed_command_list(self):
        """
        Save the unpublished commands for reuse
        """
        if self.preseed_command_list:
            with open(self.preseed_commands_filename, "w") as cmd_file:
                cmd_file.writelines(["%s\n" % item for item in self.preseed_command_list])


    def test_if_command_exists(self, complete_command_list, command1):
        """
        Test if the command exists
        """
        command1 = command1.strip()
        if not command1:
            return
        command_exists = False
        command1_help = self.get_command_help(command1)
        for cmd_known in complete_command_list:
            if cmd_known.upper() == command1.upper():
                command_exists = True
            elif command1.upper() == cmd_known[:len(command1)].upper() or \
               cmd_known.upper() == command1[:len(cmd_known)].upper():
                command2_help = self.get_command_help(cmd_known)
                if len(command1_help) == len(command2_help):
                    command_exists = True
        if not command_exists and command1_help:
            if command1 not in self.preseed_command_list:
                self.preseed_command_list.append(command1)
            if command1 not in self.unpublished_command_list:
                self.unpublished_command_list.append(command1)
                if command1 not in self.help_dict:
                    self.help_dict[command1] = ""
                print(command1 + " ", end="")
                sys.stdout.flush()


    def load_do_not_execute_command_list(self):
        """
        Load commands not to execute from a text file
        File format:
          CMD1FORM1,CMD1FORM2~Short help description|Long help description
          CMD2FORM1,CMD2FORM2~Short help description|Long help description
        """
        if os.path.isfile(self.do_not_execute_commands_filename):
            print ("Loading and parsing do-not-execute commands")
            with open(self.do_not_execute_commands_filename, "r") as cmd_file:
                upc_lines = cmd_file.readlines()
                for item in upc_lines:
                    if item.strip != "":
                        item = item.strip()
                        if item[0] != "#":
                            cmd_forms, short_long_help = item.split("~")
                            cmd_forms = cmd_forms.split(",")
                            for cmd in cmd_forms:
                                if cmd not in self.do_not_execute_command_list:
                                    self.do_not_execute_command_list.append(cmd)
                                if cmd not in self.help_dict:
                                    self.help_dict[cmd] = short_long_help


    def load_possible_command_list(self):
        """
        Load possible commands from a text file
        """
        poss_list = []
        if os.path.isfile(self.possible_commands_filename):
            print ("Loading and parsing possible commands")
            with open(self.possible_commands_filename, "r") as cmd_list_file:
                for line in iter(cmd_list_file):
                    cmds = line.strip().upper()
                    cmds = re.split(r"([\w]+)", cmds)
                    #print (cmds)
                    if cmds:
                        for cmd in cmds:
                            poss_list.append(cmd)
            uniq_cmds = set(poss_list)
            poss_list = list(uniq_cmds)
            poss_list.sort()
            with open("a_" + self.possible_commands_filename, "w") as cmd_list_file:
                for cmd in poss_list:
                    cmd_list_file.write(cmd + "\n")
            return poss_list


    def test_for_unpublished_commands(self):
        """
        Load a text file and test the commands for inclusion in the device documentation
        """
        complete_command_list = []
        complete_command_list.extend(self.pub_command_list)
        if self.hidden_command_list:
            complete_command_list.extend(self.hidden_command_list)

        # Load the possible commands file
        poss_cmds = self.load_possible_command_list()
        if not poss_cmds:
            poss_cmds = []

        # Load the device specific existing unpublished commands file, if it exists
        if os.path.isfile(self.unpublished_commands_filename):
            with open(self.unpublished_commands_filename, "r") as cmd_list_file:
                for line in iter(cmd_list_file):
                    a_cmd = line.strip()
                    if a_cmd:
                        poss_cmds.insert(0, a_cmd)

        # Preseed with known unpublished commands file, it if exists
        if os.path.isfile(self.preseed_commands_filename):
            with open(self.preseed_commands_filename, "r") as cmd_list_file:
                for line in iter(cmd_list_file):
                    a_cmd = line.strip()
                    if a_cmd and a_cmd not in poss_cmds:
                        poss_cmds.insert(0, a_cmd)

        if poss_cmds:
            print("Testing for Unpublished commands")
            for cmd in poss_cmds:
                self.test_if_command_exists(complete_command_list, cmd)
            self.unpublished_command_list.sort()
            self.save_unpublished_command_list()
            self.save_preseed_command_list()
        if self.unpublished_command_list:
            print("\nFound", len(self.unpublished_command_list), "Unpublished commands")


    def write_html_documentation(self):
        """
        Write the HTML file
        """
        if not self.pub_command_list and not self.hidden_command_list and \
           not self.unpublished_command_list:
            print("Help commands not found on this device.")
            return

        complete_command_list = []
        complete_command_list.extend(self.pub_command_list)
        if self.hidden_command_list:
            complete_command_list.extend(self.hidden_command_list)
        if self.unpublished_command_list:
            complete_command_list.extend(self.unpublished_command_list)

        print("")
        uniq_cmds = set(complete_command_list)
        complete_command_list = list(uniq_cmds)
        complete_command_list.sort()

        special_command_color = "#0000FF"
        unpublished_command_color = "#8B0000"

        self.htmldocfilename = self.console_prompt + ".html"
        htmlfile = open(self.htmldocfilename, "w")
        pagetitle = "Commandset for the " + self.console_prompt
        htmlfile.write("<!DOCTYPE HTML>\n")
        htmlfile.write("<html>\n")
        htmlfile.write("<head>\n  <title>" + pagetitle +
                       "</title>\n  <meta name=\"utility_author\" content=\"Stephen Genusa\">\n")
        htmlfile.write("  <meta http-equiv=\"Content-Type\" content=\"text/html; charset=UTF-8\">\n")
        htmlfile.write("  <style type=\"text/css\">\n")
        htmlfile.write("      table { page-break-inside:auto }\n")
        htmlfile.write("      tr    { page-break-inside:avoid; page-break-after:auto }\n")
        htmlfile.write("      thead { display:table-header-group }\n")
        htmlfile.write("      tfoot { display:table-footer-group }\n")
        htmlfile.write("      fwver { font-size:12px }\n")
        htmlfile.write("  </style>\n")
        htmlfile.write("</head>\n<body>\n<font face='arial'>\n")
        htmlfile.write("<h1>" + pagetitle + "</h1>\n")
        htmlfile.write("<blockquote>\n")
        htmlfile.write("<p style=\"font-size:12px\">" + self.firmwareversion + "</p>\n")
        htmlfile.write("<p>" + str(len(self.pub_command_list)) +
                       " normal commands found.&nbsp;")

        if self.hidden_command_list:
            htmlfile.write("<font color=\"" + special_command_color + "\">" +
                           str(len(self.hidden_command_list)-len(self.pub_command_list)) +
                           "</font> hidden commands available.&nbsp;")
        if self.unpublished_command_list:
            htmlfile.write("<font color=\"" + unpublished_command_color + "\">" +
                           str(len(self.unpublished_command_list)) +
                           " unpublished commands available.</font>")
        htmlfile.write("</p>\n")
        htmlfile.write("</blockquote>\n")

        htmlfile.write("<table border=\"1\" cellpadding=\"5\" cellspacing=\"5\" style=\"border-collapse:collapse;\" width=\"100%\">\n")

        for index, command in enumerate(complete_command_list):
            if command in self.unpublished_command_list:
                color = unpublished_command_color
                class_name = "unpub"
            elif command in self.pub_command_list:
                color = "#000000"
                class_name = "pub"
            else:
                color = special_command_color
                class_name = "hid"
            if command in self.do_not_execute_command_list:
                short_help = self.help_dict[command].split("|")[0]
                long_help = self.help_dict[command].split("|")[1]
            else:
                short_help = self.help_dict[command]
                long_help = self.get_command_help(command)
            htmlfile.write("<tr class=\"" + class_name + "\" bgcolor=\"#C0C0C0\">\n  <th width=\"20%\"><font color=\"" +
                           color + "\">" + command +
                           "</font></th>\n  <th align=\"left\"><font color=\"" +
                           color + "\">&nbsp;" + short_help +
                           "</font></th>\n</tr>\n")
            htmlfile.write("<tr>\n  <td colspan=\"2\">\n<pre>" + long_help +
                           "</pre>\n</td>\n</tr>\n")
            print("(" + str(index) + ")" + command + " ", end="")
            sys.stdout.flush()
        htmlfile.write("</table>\n</font>\n")
        htmlfile.write("</body>\n</html>")


    def generate_documentation(self):
        """
        Generate device documentation
        """
        self.load_preseed_command_list()
        if self.args.autolocatecrestron:
            self.build_list_of_crestronips()
        elif self.args.autolocateactiveips:
            self.build_list_of_activeips(self.args.autolocateactiveips)
        for self.device_ip_address in self.active_ips_to_check:
            self.initialize_run_variables()
            self.load_do_not_execute_command_list()
            if self.open_device_connection():
                if self.get_console_prompt():
                    if not os.path.isfile(self.console_prompt + ".html") or self.args.overwrite:
                        try:
                            self.get_firmware_version()
                            self.get_published_command_list()
                            self.get_hidden_command_list()
                            self.test_for_unpublished_commands()
                            self.write_html_documentation()
                        finally:
                            self.close_device_connection()
                            if os.path.isfile(os.path.realpath(self.htmldocfilename)):
                                webbrowser.open_new_tab("file://" + os.path.realpath(self.htmldocfilename))
                    else:
                        print("Documentation file already found for {0}. Overwrite is off.".format(self.console_prompt))


if __name__ == "__main__":
    # pylint: disable-msg=C0103
    print("\nStephen Genusa's Crestron Device Command Documentation Builder 1.81\n")
    parser = argparse.ArgumentParser()
    parser.add_argument("-ip", "--iptocheck", help="A single Crestron IP address to build documentation for.")
    parser.add_argument("-fssh", "--forcessh", action="store_true",
                        help="Force use of SSH rather than CTP 41795")
    parser.add_argument("-uid", "--username", default="crestron", type=str,
                        help="Authentication user name.")
    parser.add_argument("-pwd", "--password", default="", type=str,
                        help="Authentication password.")
    parser.add_argument("-alc", "--autolocatecrestron", action="store_true",
                        help="Automatically locate Crestron devices on all connected subnets and build documentation.")
    parser.add_argument("-ala", "--autolocateactiveips", default="", type=str,
                        help="Automatically locate active IPs on a subnet and look for Crestron devices. Example: 174.209.101 as an argument will check 174.209.101.0/24.")
    parser.add_argument("-atc", "--addtestcommands", default='',
                        help="Filename containing additional commands to test for")
    parser.add_argument("-ow", "--overwrite", action="store_true", default=False,
                        help="Overwrite doc file if it already exists. Off by default.")
    parser_args = parser.parse_args()
    if not parser_args.iptocheck and not parser_args.autolocatecrestron and not parser_args.autolocateactiveips:
        parser.print_help()
        exit()

    documenter = CrestronDeviceDocumenter(parser_args)
    documenter.generate_documentation()
