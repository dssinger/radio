class Station:
    stationlist = []
    stationdir = {}
    stationpos = 0

    @classmethod
    def next(self):
        self.stationpos += 1
        if self.stationpos >= len(self.stationlist):
            self.stationpos = 0
        return self.stationlist[self.stationpos]

    @classmethod
    def prev(self):
        self.stationpos -= 1
        if self.stationpos < 0:
            self.stationpos = len(self.stationlist) - 1
        return self.stationlist[self.stationpos]

    @classmethod
    def current(self):
        return self.stationlist[self.stationpos]

    @classmethod
    def select(self, what):
        try:
            pos = int(what)
            if (pos > 0) and (pos < len(self.stationlist)):
                self.stationpos = pos
        except ValueError:
            if what in self.stationdir:
                self.stationpos = self.stationdir[what].pos
        return self.stationlist[self.stationpos]

    @classmethod
    def stations(self):
        ret = []
        for s in self.stationlist:
            ret.append(repr(s))
        return '[%s]' % ','.join(ret)
        

    def __init__(self, label, url, islist=False, nickname=None):
        self.label = label
        self.url = url
        self.pos = len(self.stationlist)
        self.islist = islist
        self.nickname = nickname if nickname else label
        self.stationlist.append(self)
        self.stationdir[label] = self

    def __repr__(self):
        return '{"pos":%d,"label":"%s","url":"%s"}' % (self.pos, self.label, self.url)
        
    def json(self):
        ans = {}
        ans['pos'] = self.pos
        ans['label'] = self.label
        ans['url'] = self.url
        return ans


Station('KDFC', 'http://32.aac.pls.kdfc.live/', islist=True)
Station('Venice Classical Radio', 'http://174.36.206.197:8000/stream')
Station('Radio Swiss Classic', 'http://stream.srg-ssr.ch/m/rsc_de/aacp_96')
Station('BBC Radio 3', 'http://bbcmedia.ic.llnwd.net/stream/bbcmedia_radio3_mf_p?s=1449788045&e=1449802445&h=30697f7cb4a7a30b994f677063a26493')
Station('Dutch Radio 4', 'http://icecast.omroep.nl/radio4-bb-mp3')
Station('Linn Classical', 'http://89.16.185.174:8004/stream')
Station('WQXR', 'http://stream.wqxr.org/wqxr')
Station('WGBH', 'http://audio.wgbh.org:8004')
