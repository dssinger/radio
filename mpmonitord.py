#!/usr/bin/python
""" Daemonize MPMonitor """
import daemon
import sys
from mpmonitor import do_main_program

logf = open('/home/david/src/radio/log.txt', 'a')
errlogf = open('/home/david/src/radio/errlog.txt', 'a')


with daemon.DaemonContext(stdout=logf,stderr=errlogf,working_directory="/home/david/src/radio",initgroups=False):
    do_main_program()

print "done"
