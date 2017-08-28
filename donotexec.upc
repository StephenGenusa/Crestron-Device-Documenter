#
#  This file contains any command you never want to be executed or help queried for.
#  Some device console firmware, on some commands ignores the "?" on a help request 
#  "command ?" and instead executes the command. Any command listed here will not be
#  queried on the firmware and will get the short help and long help descriptions from 
#  this file.
#
#  This also gives you the ability to customize the published help by replacing the
#  console help with your own text.
#
#  Some commands may have multiple forms so you can list such command using the format:
#  CMD1FORM1,CMD1FORM2~Short help description|Long help description
#  CMD2FORM1~Short help description|Long help description
#  CMD3FORM1,CMD3FORM2,CMD3FORM3~Short help description|Long help description
#
#  A comma separates duplicated commands with differing forms, a tilde followed by the short help description
#  and pipe | symbol separating short and long help
#
#  Examples:
#
DBGTRANSMITTER~(*) Sets or clears Debug flag for IR/RF Transmitter|Sets or clears Debug flag for IR/RF Transmitter<p>Customizable help. See the text file donotexec.upc
REPORTPPNTABLe~Displays Cresnet PPN table if available|Displays Cresnet PPN table if available
LOGOFF~Logs the currently authenticated user out of the system|Logs the currently authenticated user out of the system