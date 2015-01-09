#!/usr/bin/python

from mysocket import *

def sendcmd(cmd):
    sock = mysocket()
    sock.connect(('localhost', 6600))
    sock.send(cmd + '\n')
    print "sent %s" % cmd
    resp = self.readline()
    while resp != '' and resp != 'OK' and not resp.startswith('ACK '):
        print resp
        resp = self.readline()
    sock.close()


def handlex10line(l):
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
        except:
            pass   # We don't care!



s = mysocket()
s.connect(('localhost', 1099))    # Connect to the X10 via mochad
l = s.readline()
while len(l) > 0:
    print l
    handlex10line(l)
    l = s.readline()


