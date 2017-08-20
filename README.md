# Crestron Device Command Documenter
Generates good looking HTML Documentation for normal and hidden Crestron device commands. Precompiled binary available from release page.

----------
July 2017

- Largely rewritten to clean up the code, add new functionality and conform more closely to PEP 8.
- The program will now take a second command-line parameter, a filename that points to a text file containing known or "word of mouth" commands that are not included in the existing help commands. These will be tested for, saved to a .upc file, and added to the HTML documentation if they exist.
- Regex improvement so that more devices are now supported

August 2017

- Firmware version regex improved
- Additional refactoring of code to cleanup code
- General help capture regex improved to handle more devices

To Do:

 - Additional testing and cleanup
 - Incorporate [code to automatically locate most Crestron devices](https://github.com/StephenGenusa/Crestron-List-Devices-On-Network) using UDP broadcast

----------
- Written using Python 2.7
- Authentication is not currently supported.

----------
I suggest you create a batch file for all Crestron devices on a network and let it generate a full set of documentation.

----------

Copyright © 2017 Stephen Genusa

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.