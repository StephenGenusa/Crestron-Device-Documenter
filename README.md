# Crestron Device Command Documenter
Generates good looking HTML Documentation for normal and hidden Crestron device commands. Precompiled binary available from release page.

----------
July 2017

- Largely rewritten to clean up the code, add new functionality and conform more closely to PEP 8.
- The program will now take a command-line parameter, a filename that points to a text file containing known or "word of mouth" commands that are not included in the existing help commands. These will be tested for, saved to a .upc file, and added to the HTML documentation if they exist.
- Regex improvement so that more devices are now supported

August 2017

- Firmware version regex improved
- Additional refactoring of code to cleanup code
- General help capture regex improved to handle more devices
- Automatic detection of Crestron devices using UDP using -alc option
- If working via VPN or router that prevents UDP, use the -ala option to determine active devices on network, test each device for Crestron console and build documentation for all devices that provide console
- Support for SSH added (first pass; needs testing)

## Example Program Usage ##

**Build documentation for a single Crestron device that provides console:**
<pre>
BuildCrestronCommandReference -ip 10.61.101.24
</pre>

**Build documentation for a single Crestron device using SSH:**
<pre>
BuildCrestronCommandReference -ip 10.61.101.24 -fssh -uid cresuser -pwd pptron9
</pre>

**Build documentation for all Crestron devices on all (computer connected) subnets that respond to UDP and provide a console:**
<pre>
BuildCrestronCommandReference -alc
</pre>

**Build documentation for all devices that are active on 10.61.101.0/24 that provide a Crestron console:**
<pre>
BuildCrestronCommandReference -ala 10.61.101
</pre>

**Build documentation for a single Crestron device that provides console adding any valid commands found in addtlcmds.txt:**
<pre>
BuildCrestronCommandReference -ip 10.61.101.24 -atc addtlcmds.txt
</pre>


## To Do ##
 - Additional testing and cleanup

## Notes ##
- Some Crestron devices only support a single console session so be sure Toolbox is completely shut down if running against multiple devices
- Written using Python 2.7

----------

Copyright © 2017 Stephen Genusa

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.