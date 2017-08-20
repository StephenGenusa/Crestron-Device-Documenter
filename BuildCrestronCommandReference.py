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
import os
import re
import socket
import sys
import textwrap
import webbrowser
from time import sleep
#import hexdump
#import pprint

BUFF_SIZE = 20000
MAX_RETRIES = 3
CR = "\r"


class CrestronDeviceDocumenter(object):
    """
    Attempt to identify all commands on a Crestron device
    """
    # pylint: disable=too-many-instance-attributes

    def __init__(self, device_ip_address, possible_commands_filename):
        """
        initialize internal properties
        """
        self.device_ip_address = device_ip_address
        self.console_prompt = ""
        self.firmwareversion = ""
        self.help_dict = {}
        self.pub_command_list = []
        self.hidden_command_list = []
        self.preseed_command_list = []
        self.unpublished_command_list = []
        self.htmldocfilename = ""
        self.possible_commands_filename = possible_commands_filename
        self.preseed_commands_filename = "preseed.upc"
        self.unpublished_commands_filename = ""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    
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


    def open_device_connection(self):
        """
        Open the device connection, attempting port 41795
        """
        try:
            server_address = (self.device_ip_address, 41795)
            print("Attempting to connect to %s port %s" % server_address)
            self.sock.connect(server_address)
        except:
            print("Error: Unable to connect to device.")
            exit()


    def close_device_connection(self):
        """
        Close the socket
        """
        try:
            print("\nProcess complete.")
            self.sock.close()
        except:
            pass


    def get_console_prompt(self):
        """
        Determine the device console prompt
        """
        data = ""
        for _unused in range(0, MAX_RETRIES):
            self.sock.sendall(CR)
            data = data + self.sock.recv(BUFF_SIZE)
            sleep(.25)
            search = re.findall(r"\r\n([\w-]{3,30})>", data, re.M)
            if search:
                self.console_prompt = search[0]
                self.unpublished_commands_filename = self.console_prompt + ".upc"
                print("\nConsole prompt is", self.console_prompt)
                return
        print("Console prompt not found.")
        exit()


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
        message = CR + command + CR
        self.sock.sendall(message)
        data = ""
        sleep(0.2)
        waitcount = 0
        self.sock.settimeout(1)
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
        data = data.replace(self.console_prompt + ">", "")
        search = re.search(r"[\r\n]{1,2}([\w\[\]\.\ \(\),#@-]{20,90})[\r\n]{1,2}", data, re.MULTILINE)
        if search:
            self.firmwareversion = search.group().strip()
            print("Firmware version ", self.firmwareversion)


    def get_command_help(self, command):
        """
        Get the help text for a command
        """
        message = command + " ?"
        # The following three commands don't behave properly
        # Instead of giving help, they just just execute. The
        #  first requires a CR to terminate and the second
        #  generates a report
        if command == "DBGTRANSMITTER":
            return "Sets or clears Debug flags for IR/RF Transmitter"
        if command == "REPORTPPNTABLe":
            return "Displays Cresnet PPN table if available"
        if command == "LOGOFF":
            return "Logs the currently authenticated user out of the system"
        if command.upper() in ["MACADDRESS", "MACA"]:
            return "Returns the MAC address of the built-in NIC"
        data = self.send_command_wait_prompt(message, 30)
        if data.find("Bad or Incomplete Command") > -1:
            return ""
        if data.find("Authentication is not on. Command not allowed.") > -1 or \
           data.find("ERROR: Command Blocked from this console type.") > -1 or \
           data == "":
            return "No help available for this command."
        search = re.findall(r"[\r\n]{1,2}(.{5," + str(len(data)) + "})[\r\n]{1,2}" + \
                 self.console_prompt + ">", data, re.M|re.S)
        if search:
            help_text = search[0].replace(self.console_prompt + ">", ""). \
                        replace(">", "&gt;").replace("<", "&lt;")
            help_text = help_text[len(message) + 2:]
            reformatted_help_text = ""
            for line in help_text.split("\n"):
                reformatted_help_text += textwrap.fill(line, 150) + "\n"
            return reformatted_help_text
        return ""


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


    def test_if_command_exists(self, complete_command_list, command1):
        """
        Test if the command exists
        """
        command1 = command1.strip()
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
            if command1 not in self.unpublished_command_list:
                self.unpublished_command_list.append(command1)
                self.help_dict[command1] = ""
                print("Found", command1)


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
                    if a_cmd:
                        poss_cmds.insert(0, a_cmd)

        if poss_cmds:
            print("Testing for Unpublished commands")
            for cmd in poss_cmds:
                self.test_if_command_exists(complete_command_list, cmd)
            self.unpublished_command_list.sort()
            self.save_unpublished_command_list()
        if self.unpublished_command_list:
            print("Found", len(self.unpublished_command_list), "Unpublished commands")


    def write_html_documentation(self):
        """
        Write the HTML file
        """
        if not self.pub_command_list and not self.hidden_command_list and \
           not self.unpublished_command_list:
            print("Help commands not found on this device.")
            exit()

        complete_command_list = []
        complete_command_list.extend(self.pub_command_list)
        if self.hidden_command_list:
            complete_command_list.extend(self.hidden_command_list)
        if self.unpublished_command_list:
            complete_command_list.extend(self.unpublished_command_list)

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
        htmlfile.write("<head>  <title>" + pagetitle +
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
            htmlfile.write(" <font color=\"" + unpublished_command_color + "\">" +
                           str(len(self.unpublished_command_list)) +
                           " unpublished commands available.</font>")
        htmlfile.write("</p>\n")
        htmlfile.write("</blockquote>\n")

        htmlfile.write("<table border=\"1\" cellpadding=\"5\" cellspacing=\"5\" style=\"border-collapse:collapse;\" width=\"100%\">\n")

        itemcounter = 0
        print("")
        for command in complete_command_list:
            if command in self.unpublished_command_list:
                color = unpublished_command_color
            elif command in self.pub_command_list:
                color = "#000000"
            else:
                color = special_command_color
            command_help = self.get_command_help(command)
            htmlfile.write("<tr bgcolor=\"#C0C0C0\">\n  <th width=\"20%\"><font color=\"" +
                           color + "\">" + command +
                           "</font></th>\n  <th align=\"left\"><font color=\"" +
                           color + "\">&nbsp;" + self.help_dict[command] +
                           "</font></th>\n</tr>\n")
            htmlfile.write("<tr>\n  <td colspan=\"2\">\n<pre>" + command_help +
                           "</pre>\n</td>\n</tr>\n")
            print("(" + str(itemcounter+1) + ")" + command + " ", end="")
            sys.stdout.flush()
            itemcounter += 1
        htmlfile.write("</table>\n</font>\n</body>\n</html>")


    def generate_documentation(self):
        """
        Generate device documentation
        """
        self.open_device_connection()
        try:
            self.get_console_prompt()
            self.get_firmware_version()
            self.get_published_command_list()
            self.get_hidden_command_list()
            self.test_for_unpublished_commands()
            self.write_html_documentation()

        finally:
            self.close_device_connection()
            if os.path.isfile(os.path.realpath(self.htmldocfilename)):
                webbrowser.open_new_tab("file://" + os.path.realpath(self.htmldocfilename))


if __name__ == "__main__":
    # pylint: disable-msg=C0103
    print("\nStephen Genusa's Crestron Device Command Documentation Builder 1.6\n")
    if len(sys.argv) >= 1:
        DeviceIPAddress = sys.argv[1]
        TestCmdFilename = ""
        if len(sys.argv) == 3:
            TestCmdFilename = sys.argv[2]
    else:
        print("You must provide the IP address of the Crestron device.")
        print("Authentication not currently supported.\n")
        exit()
    documenter = CrestronDeviceDocumenter(DeviceIPAddress, TestCmdFilename)
    documenter.generate_documentation()
