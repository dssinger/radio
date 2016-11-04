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
        

    def __init__(self, label, url):
        self.label = label
        self.url = url
        self.pos = len(self.stationlist)
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


