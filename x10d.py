#!/usr/bin/python
""" Daemonize the X10 Listener """
import daemon
import sys
from x10listener import do_main_program

logf = open('/home/david/src/radio/dlog.txt', 'a')


with daemon.DaemonContext(stdout=logf,working_directory="/home/david/src/radio/"):
    do_main_program()

print "done"
