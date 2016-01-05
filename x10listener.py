#!/usr/bin/python

import sys
from mysocket import *

def sendcmd(cmd):
    sock = mysocket()
    sock.connect(('radio.local', 6600))
    sock.send(cmd + '\n')
    print "sent %s" % cmd; sys.stdout.flush()
    resp = sock.readline()
    print "back from readline, resp = '%s'" % resp; sys.stdout.flush()
    while resp != '' and resp != 'OK' and not resp.startswith('ACK '):
        print resp; sys.stdout.flush(); 
        resp = sock.readline()
    print 'ready to close socket'; sys.stdout.flush()
    sock.close()


def handlex10line(l,s):
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
        except:
            pass   # We don't care!



def do_main_program():
    s = mysocket()
    s.connect(('localhost', 1099))    # Connect to the X10 via mochad
    l = s.readline()
    while len(l) > 0:
        print l; sys.stdout.flush()
        handlex10line(l,s)
        l = s.readline()

if __name__ == "__main__":
    do_main_program()
