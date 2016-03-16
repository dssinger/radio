#!/usr/bin/python
from ouimeaux.environment import Environment
from ouimeaux.utils import matcher
from ouimeaux.signals import receiver, statechange, devicefound
import datetime
import sys
import mysocket

sock = mysocket.mysocket()
sock.connect(('radio.local', 6601))

def log(*msg):
        now = datetime.datetime.now()
        print '%s %s' % (now, ' '.join(msg))
        sys.stdout.flush()

def mainloop(name):
        matches = matcher(name)

        @receiver(devicefound)
        def found(sender, **kwargs):
                if matches(sender.name):
                        log("Found device:", sender.name)

        @receiver(statechange)
        def motion(sender, **kwargs):
                if matches(sender.name):
                        state = True if kwargs.get('state') else False
                        log("{} state is {}".format(sender.name,
                                        "on" if state else "off"))
                        if state:
                            sock.send('play\n')
                        else:
                            sock.send('stop\n')


        env = Environment()

        try:
                env.start()
                env.discover(10)
                env.wait()
        except (KeyboardInterrupt, SystemExit):
                log("Goodbye!")
                sys.exit(0)

if __name__ == "__main__":
        mainloop('streaming')
