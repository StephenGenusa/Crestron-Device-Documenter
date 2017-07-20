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
import webbrowser
from time import sleep

BUF_SIZE = 20000
MAX_RETRIES = 3

def RemovePrompt(data, console_prompt, char_limit):
    prompt_pos = data.find(console_prompt+">")
    if prompt_pos < char_limit:
        data = data.replace(console_prompt+">", "", 1)
    if char_limit == -1:
        data = data.replace(console_prompt+">", "")
    return data


def GetConsolePrompt(sock):
    CR = "\r"
    data = ""
    for x in range(0, MAX_RETRIES):
        sock.sendall(CR)
        data = data + sock.recv(BUF_SIZE)
        sleep(1)
        search = re.findall("\r\n([\w-]{3,20})>", data, re.M)
        if search:
            return search[0]
    else:
        return ""


def GetFirmwareVersion(sock, console_prompt):
    CR = "\rver\r"
    sock.sendall(CR)
    sleep(1)
    data = sock.recv(BUF_SIZE)
    search = re.findall("^" + console_prompt + ".*$", data, re.M)
    if search:
        return search[0]


def GetCommandHelp(sock, command, console_prompt):
    message = command + ' ?\r'
    # The following three commands don't behave properly
    # Instead of giving help, they just just execute. The
    #  first requires a CR to terminate and the second
    #  generates a report
    if command == "DBGTRANSMITTER":
        message += "\r"
    if command == "REPORTPPNTABLe":
        message = "\r"
    if command == "LOGOFF":
        message = "\r"
    sock.sendall(message)
    data = ""
    sleep(0.1)
    waitcount = 0
    sock.settimeout(1)
    while not data.find(console_prompt) > -1:
        # Deal with newer firmware that executes commands / doesn't return a prompt 
        #   instead of printing help
        try:
            sleep(0.1)
            data = data + sock.recv(BUF_SIZE)
        except:
            sock.sendall("\r")
        waitcount += 1
        if waitcount == 5:
            sock.sendall("\r")
            waitcount = 0
    if data.find("Authentication is not on. Command not allowed.") > -1 or \
        data.find("ERROR: Command Blocked from this console type.") > -1 or \
        data == "":
            return "No help available for this command."
    search = re.findall(r"\?\r(.{5," + str(len(data)) + "})\r\n" + console_prompt + ">", data,
                        re.M|re.S)
    if search:
        return search[0].replace(console_prompt + ">", "").replace(">", "&gt;").replace("<", "&lt;").strip()
    else:
        return ""


def GetCommandCategories(sock, console_prompt):
    print ("Getting command categories")
    message = '\rhidhelp\r'
    sock.sendall(message)
    sleep(1)
    data = sock.recv(BUF_SIZE)
    data = data[12:]
    while data.find(console_prompt) == -1:
        data = data + sock.recv(BUF_SIZE)
    category_list = []
    category_desc = []
    search = re.findall("^HELP ([A-Za-z]{2,20})\ will\ (.{10,100})$", data,
                        re.M)
    if search:
        for find in search:
            if find[0] != "ALL":
                category_list.append(find[0])
                category_desc.append(find[1])
        return category_list, category_desc
    else:
        return [], []


def GetCategorialCommandList(sock, console_prompt, command):
    print ("\n\nGetting categorial commandset", command)
    message = '\r\hidhelp ' + command + '\r'
    sock.sendall(message)
    sleep(.2)
    data = sock.recv(BUF_SIZE)
    data = data[len(message)+4:]
    while data.find(console_prompt) == -1:
        data = data + sock.recv(BUF_SIZE)
    command_list = []
    help_desc = []
    search = re.findall("^(.{1,200})$", data, re.M)
    if search:
        for find in search:
            search2 = re.findall("^(\w{2,25})\ *(\w{7,19}|User\ or\ Connect)?\ *(.{1,120})$", find, re.M|re.S)
            if search2:
                command_list.append(search2[0][0].strip())
                help_desc.append(search2[0][2].strip())
        if len(command_list) == 0:
            print ("[None]")
        return command_list, help_desc
    else:
        return [], []


def GetFullCommandList(sock, console_prompt):
    print ("Getting Full Commandset")
    message = 'hidhelp all'
    sock.sendall("\r" + message + "\r")
    sleep(1)
    data = sock.recv(BUF_SIZE)
    data = data.replace(message, "")
    data = RemovePrompt(data, console_prompt, 100)
    while data.find(console_prompt) == -1:
        data = data + sock.recv(BUF_SIZE)
    data = data.replace(message, "")
    command_list = []
    help_desc = []
    data = RemovePrompt(data, console_prompt, -1)
    if data.find("Bad or") == -1:
        search = re.findall("^(.{1,200})$", data, re.M)
        if search:
            for find in search:
                search2 = re.findall("^(\w{2,25})\ *(\w{8,20}|User\ or\ Connect)?\ *?(.{1,120})$", find, re.M)
                if search2:
                    command_list.append(search2[0][0].strip())
                    help_desc.append(search2[0][2].strip())
    return command_list, help_desc


def GetCommandList(sock, console_prompt):
    print ("Getting Normal Commandset")
    message = 'help all'
    sock.sendall("\r" + message + "\r")
    sleep(1)
    data = sock.recv(BUF_SIZE)
    data = data.replace(message, "")
    data = RemovePrompt(data, console_prompt, 100)
    command_list = []
    help_desc = []
    while data.find(console_prompt) == -1:
        data = data + sock.recv(BUF_SIZE)
    command_list = []
    data = RemovePrompt(data, console_prompt, -1)
    if not data.find("\r\n"):
        data = data.replace ("\r", "\r\n")
    search = re.findall("^(.{1,200})$", data, re.MULTILINE)
    if search:
        for find in search:
            search2 = re.findall("^(\w{2,25})\ *(\w{8,20}|User\ or\ Connect)?\ *(.{1,120})$", find, re.M)
            if search2:
                if search2[0][0] not in command_list:
                    command_list.append(search2[0][0].strip())
                    help_desc.append(search2[0][2].strip())
    return command_list, help_desc


if __name__ == "__main__":
    print("\nStephen Genusa's Crestron Processor Command Documentation Builder 1.2\n")
    if len(sys.argv) >= 1:
        device_ip_address = sys.argv[1]
    else:
        print("You must provide the IP address of the Crestron processor.\nAuthentication not currently supported.\n")
        exit()

    console_prompt = ""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_address = (device_ip_address, 41795)
    print ('Connecting to %s port %s' % server_address)
    sock.connect(server_address)
    try:
        console_prompt = GetConsolePrompt(sock)
        if len(console_prompt) == 0:
            print("Console prompt not found.")
            exit()

        print("Console prompt is", console_prompt)

        #firmware_version = GetFirmwareVersion(sock, console_prompt)
        #print ("Firmware version is", firmware_version)
        
        command_list, cmd_help_desc = GetCommandList(sock, console_prompt)

        full_command_list, help_desc = GetFullCommandList(sock, console_prompt)

        if len(command_list) == 0 and len(full_command_list) == 0:
            print ("Help commands not found on this device.")
            exit()

        if len(full_command_list) == 0:
            full_command_list = command_list
            help_desc = cmd_help_desc
            print(len(command_list),
                  "normal commands found. No hidden commands found\n")
        else:
            print(len(command_list), "normal commands found.",
                  len(full_command_list)-len(command_list),
                  "hidden commands found.\n")

        special_command_color = "#0000FF"

        htmlfile = open(console_prompt+".html", "w")
        pagetitle = "Commandset for the " + console_prompt
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
        htmlfile.write("  </style>\n")
        htmlfile.write("</head>\n<body>\n<font face='arial'>\n")
        htmlfile.write("<h1>" + pagetitle + "</h1>\n")
        if len(full_command_list) != len(command_list):
            htmlfile.write("<p>&nbsp;&nbsp;" + str(len(command_list)) +
                           " normal commands found. <font color=\"" +
                           special_command_color + "\">" +
                           str(len(full_command_list)-len(command_list)) +
                           "</font> hidden commands available.</p>\n")
        else:
            htmlfile.write("<p>&nbsp;&nbsp;" + str(len(command_list)) +
                           " normal commands found.</p>\n")

        # htmlfile.write("<p><smaller>" + firmware_version + "</smaller>\n")
        htmlfile.write("<table border=\"1\" cellpadding=\"5\" cellspacing=\"5\" style=\"border-collapse:collapse;\" width=\"100%\">\n")

        itemcounter = 0
        for command in full_command_list:
            if command not in command_list and (len(command_list) != len(full_command_list)):
                color = special_command_color
            else:
                color = "#000000"
            command_help = GetCommandHelp(sock, command, console_prompt)
            htmlfile.write("<tr bgcolor=\"#C0C0C0\">\n  <th width=\"20%\"><font color=\"" +
                           color + "\">" + command +
                           "</font></th>\n  <th align=\"left\"><font color=\"" +
                           color + "\">" + help_desc[itemcounter] +
                           "</font></th>\n</tr>\n")
            htmlfile.write("<tr>\n  <td colspan=\"2\">\n<pre>" + command_help +
                           "</pre>\n</td>\n</tr>\n")
            print("(" + str(itemcounter+1) + ")" + command + " ", end="")
            sys.stdout.flush()
            itemcounter += 1
        htmlfile.write("</table>\n</font>\n</body>\n</html>")

    finally:
        print ('\nProcess complete. Closing connection.')
        sock.close()
        if os.path.isfile(os.path.realpath(console_prompt+".html")):
            webbrowser.open_new_tab("file://" + os.path.realpath(console_prompt+".html"))
