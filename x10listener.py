#!/usr/bin/python

import sys
from mysocket import *
import socket
import subprocess
from ouimeaux.environment import Environment

def sendcmd(cmd):
    # We don't care about replies, so just blast it and close
    print "sending %s" % cmd; sys.stdout.flush()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(('radio.local', 6601))
    sock.send(cmd + '\n')
    sock.close()


def handlex10line(l,s, switch):
    """ X10 lines have this form:
    01/08 15:47:00 Rx RF HouseUnit: D5 Func: Off

    We only care about RF lines with HouseUnit codes of interest to us.
    """

    if ' Rx RF ' in l:
        try:
            words = l.split()
            hu = words[5]
            func = words[7]
            if hu == 'D2':
                # Turn off or on
                if func == 'Off':
                    sendcmd('stop')
                else:
                    sendcmd('play')

            elif hu == 'D3':
                # Prev or Next
                if func == 'Off':
                    sendcmd('previous')
                else:
                    sendcmd('next')
            elif hu == 'D5':
                s.send('RF D5 ' + func + '\n')
            elif hu in ('D1', 'D8', 'D16'):
                # Need to bridge to the WeMo switch
                if (func == 'Off'):
                    switch.off()
                else:
                    switch.on()
        except:
            pass   # We don't care!



def do_main_program():
    sys.stdout.close()
    sys.stdout = open('/home/david/src/radio/xlog.txt', 'a')
    env = Environment(with_discovery=False,with_subscribers=False)
    env.start()
    env.discover(seconds=3)
    switch = env.get_switch('streaming')
    s = mysocket()
    s.connect(('localhost', 1099))    # Connect to the X10 via mochad
    l = s.readline()
    while len(l) > 0:
        print l; sys.stdout.flush()
        handlex10line(l,s, switch)
        l = s.readline()

if __name__ == "__main__":
    do_main_program()
