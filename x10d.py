#!/usr/bin/python
""" Daemonize the X10 Listener """
import daemon
import daemon.pidfile
import sys
import pwd
import os
from x10listener import do_main_program


user = pwd.getpwnam('david')   # This is kinda ugly...
workdir = os.path.join(user.pw_dir,'src/radio') 
pidfile = os.path.join(workdir,'x10d.pid')
uid = user.pw_uid
gid = user.pw_gid
logf = open(os.path.join(workdir, 'dlog.txt'),'a')

with daemon.DaemonContext(stdout=logf,working_directory=workdir,pidfile=daemon.pidfile.PIDLockFile(pidfile),uid=uid,gid=gid):
    do_main_program()

print "done"
