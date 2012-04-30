
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.conf import settings
from scrapy.spider import BaseSpider
from items import MyItem
from scrapy.exceptions import CloseSpider

from copy import copy
import cPickle as pickle
import os.path, atexit
import parsedatetime.parsedatetime as pdt
from datetime import datetime, date, timedelta
from urllib import urlencode
import urlparse

url_params = {
    'hl':'en',
    'q':'',
    'start':'',
    'tbs':'qdr:0',
    'num':'100',
    'filter':'0',
    'qscrl':'1'
}

settings.overrides['USER_AGENT'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5'
settings.overrides['RANDOMIZE_DOWNLOAD_DELAY'] = True
settings.overrides['DOWNLOAD_DELAY'] = 3
settings.overrides['CONCURRENT_REQUESTS_PER_DOMAIN'] = 2

class GoogleSpider(BaseSpider):
    name = "google"
    allowed_domains = ["google.com"]
    start_urls = ["https://www.google.com/"]
#    url_home          = "http://www.google.com/"
#    url_search        = "http://www.google.com/search?hl=%en&q=%(query)s&tbs=qdr:%(qdr)s&btnG=Google+Search"
#    url_search        = "http://www.google.com/search?hl=en&q='kernel bug at'&tbs=qdr:0&btnG=Google+Search"
#    url_next_page     = "http://www.google.com/search?hl=%(lang)s&q=%(query)s&start=%(start)d&tbs=qdr:%(qdr)s"
#    url_search_num    = "http://www.google.com/search?hl=%(lang)s&q=%(query)s&num=%(num)d&tbs=qdr:%(qdr)s&btnG=Google+Search"
#    url_next_page_num = "http://www.google.com/search?hl=%(lang)s&q=%(query)s&num=%(num)d&start=%(start)d&tbs=qdr:%(qdr)s"
#https://www.google.com/search?aq=f&q=dom&hl=en&qscrl=1&tbs=cdr:1%2Ccd_min%3A4%2F10%2F2012%2Ccd_max%3A4%2F25%2F2012
    query = '"kernel bug" OR "kernel warning"'
    link_count = None
    last_date = None # load previous date from file in date format
    days = 7
    date_file = {'google_date':None}
    folder = './data'
    hashes = None
    pickle_fd = None
    
    def __init__(self, *args, **kwargs):
        super(GoogleSpider, self).__init__(*args, **kwargs)
        if kwargs.get('days'):
            self.days = kwargs.get('days')
#        if kwargs.get('query'):
#            self.query = kwargs.get('query')
#        if kwargs.get('folder'):
#            self.folder = kwargs.get('folder')
#        else:
#		    raise CloseSpider('Folder must be specified')
        try:
            self.date_file[self.date_file.keys()[0]] = open('%s/%s' %(self.folder, self.date_file.keys()[0]), 'rb')
            self.last_date = self.date_file[self.date_file.keys()[0]].readline().strip()
            self.last_date = datetime.strptime(self.last_date, '%Y-%m-%d')
            self.last_date = self.last_date.date()
        except (OSError, IOError, ValueError):
#            self.date_file[self.date_file.keys()[0]] = open('%s%s' %(self.folder, self.date_file.keys()[0]), 'wb')
            self.last_date = None
        print self.last_date

        filename = "%s/%s.pck" %(self.folder, self.name)
        try:
            t1 = os.path.getctime(filename)
            file_time = datetime.fromtimestamp(t1)
            delta = datetime.now() - file_time
        except OSError:
            delta = timedelta(days=8)
        try:
            if delta.days < 7:
                self.pickle_fd = open(filename, 'a+b')
            else:
                self.pickle_fd = open(filename, 'w+b')
        except (OSError, IOError):
            print 'Error opening file scrapyd must have writing access to folder'
            raise CloseSpider('No writing access in this folder')
        print self.pickle_fd
        self.link_count = 0
        try:
#            self.pickle_fd = open("%s%s.pck" %(self.folder, name),"rb+")
            self.hashes = pickle.load(self.pickle_fd)
        except EOFError :
            self.hashes = set();
        self.item_file = open('google.item', 'wb+')
        atexit.register(self.save)

    def save(self):
        self.item_file.close()
        filename = "%s/%s.pck" %(self.folder, self.name)
        self.pickle_fd = open(filename, 'w+b')
        pickle.dump(self.hashes, self.pickle_fd)
        self.pickle_fd.close()

    def start_requests(self):
        min_date = self.last_date
        max_date = min_date
        pages = 10
        i = 0
        while i < self.days:
            max_date = min_date
            print max_date
            if max_date:
                min_date = max_date - timedelta(days=1)
                pages = 7
                print min_date
            pg_count = 0
            while pg_count < pages:
                url = self.create_url(self.start_urls[0], self.query, pg_count*100, min_date, max_date)
                pg_count += 1
                print url
                yield Request(url, callback=self.parse_results)
            if not min_date:
                min_date = date.today()
            else:
                i += 1

        self.date_file[self.date_file.keys()[0]] = open('%s/%s' %(self.folder, self.date_file.keys()[0]), 'wb')
        self.date_file[self.date_file.keys()[0]].write('%s' %(min_date.strftime('%Y-%m-%d')))
        self.date_file[self.date_file.keys()[0]].close()

#        raise Exception("RANDOM EXCEPTION")

    def parse_results(self, response):
        hxs = HtmlXPathSelector(response)
        date = None
        items = []
#        for link in hxs.select('//span[@class="st"] | //li[@class="g"]'):
        for link in hxs.select('//li[@class="g"]'):
            item = MyItem()
#           for link in hxs.select('//li[@class="g"]'):
#           url = link.select('*/h3[@class="r"]/a[@href]/@href').extract()
#           date = 

            # link.select('*/a[contains(@href, "http")]/@href').extract()
            searched_link = link.select('*/h3[@class="r"]/a[@href]/@href').extract()
 	    #link.select('text()').extract() link.select('*/text()').extract()
            link_date = link.select('*//span[@class="f std"]/text()').extract()

            if len(link_date) > 0:
                date = copy(link_date[0].strip()) #add date parsing here
                date = self.dateFromString(copy(link_date[0].strip()))
                if date:
                    date = date.strftime('%Y-%m-%d')

            if len(searched_link) > 0:
                searched_link = self.filter_result(searched_link[0])
            if searched_link:
#                print "LINK %s" %searched_link
                h = hash(searched_link)
                if h in self.hashes:
                    continue
                self.hashes.add(h)
                self.link_count += 1
                item['url'] = searched_link
                item['num'] = self.link_count
                item['length'] = len(searched_link)

                item['date'] = date
                print item
                items.append(item)
                self.item_file.write('%s\n' %item['url'])
        return items

    def create_url(self, base, query, start_num, min_date, max_date):
        qparams = url_params.copy()
        qparams['q'] = query
        qparams['start'] = str(start_num)
        # if there was no previous date saved, search without date limits
        if (not min_date) or (not max_date):
            qparams['tbs'] = 'qdr:0'
        else:
            qparams['tbs'] = 'cdr:1,cd_min:%s,cd_max:%s' %(min_date.strftime('%m/%d/%Y'), max_date.strftime('%m/%d/%Y'))
        req_params = urlencode(qparams, True)
        req_url = urlparse.urljoin(base, 'search')
        req_url += '?' + req_params
        return req_url

    def filter_result(self, link):
        try:
            # Valid results are absolute URLs not pointing to a Google domain
            # like images.google.com or googleusercontent.com
            o = urlparse.urlparse(link, 'http')
            if o.netloc and 'google' not in o.netloc:
                return link

            # Decode hidden URLs.
            if link.startswith('/url?'):
                link = urlparse.parse_qs(o.query)['q'][0]

            # Valid results are absolute URLs not pointing to a Google domain
            # like images.google.com or googleusercontent.com
            o = urlparse.urlparse(link, 'http')
            if o.netloc and 'google' not in o.netloc:
                return link

        # Otherwise, or on error, return None.
        except Exception:
            pass
        return None

    def dateFromString(self, in_str):

        s = in_str.strip()
        if len(s) > 12 or len(s) < 5:
            return None
        dt = None
        try:
            dt = datetime.strptime(s, '%Y-%m-%d').date()
            if dt:
                return dt
        except (ValueError, TypeError, IndexError):
            pass

        dt = None
        now = date.today()
        c = pdt.Calendar()
        result, what = c.parse(s)

        # what was returned (see http://code-bear.com/code/parsedatetime/docs/)
        # 0 = failed to parse
        # 1 = date (with current time, as a struct_time)
        # 2 = time (with current date, as a struct_time)
        # 3 = datetime
        if what in (1,2):
            dt = date(*result[:3])
            if (dt == now):
                try:
                    d = datetime.strptime(s, '%Y-%m-%d').date()
                    if (d) and (d != now):
                        dt = d
                except (ValueError, TypeError, IndexError):
                    pass
        elif what == 3:
            dt = date(*result[:3])
        else:
            return None
        if (now-dt) < timedelta(0) and (now-dt) >= timedelta(days=-7):
            dt = dt - timedelta(days=7)
        elif (now-dt) < timedelta(days=-7):
            dt = None
        if dt:
            return dt
        else:
            return None
