
from urllib import urlencode
from urlparse import urljoin
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.conf import settings

from scrapy.spider import BaseSpider
from scrapy.exceptions import CloseSpider
from items import MyItem
import cPickle as pickle
import os.path, atexit
import parsedatetime.parsedatetime as pdt
from datetime import datetime, date, timedelta

url_params = {
    'query_format': 'advanced',
    'short_desc_type': '',
	'short_desc': '',
	'long_desc_type': 'anywords',
	'long_desc' : '',
#	'bug_file_loc_type': 'allwordssubstr',
#	'bug_file_loc': '',
#	'status_whiteboard_type': 'allwordssubstr',
#	'status_whiteboard': '',
	# NEW, ASSIGNED and REOPENED is obsolete as of bugzilla 3.x and has
	# been removed from bugs.gentoo.org on 2011/05/01
#	'bug_status': ['NEW', 'ASSIGNED', 'REOPENED', 'NEEDINFO', 'CONFIRMED', 'IN_PROGRESS'],
    'bug_status':['__open__', '__closed__'],
#	'bug_severity': ['unspecified', 'urgent', 'high', 'medium', 'low'],
#	'priority': ['unspecified', 'urgent', 'high', 'medium', 'low'],
#	'bugidtype':'include',
#	'bug_id':'',
    'columnlist':['bug_severity', 'priority', 'op_sys', 'assigned_to', 'bug_status', 'resolution', 'short_desc', 'changeddate'],
	'content':'',
	'chfieldfrom':'', # search from date, format YYYY-MM-DD
	'chfieldto':'Now', # search to date
	'chfieldvalue':'',
#	'cmdtype':'doit',
	'order': 'Bug Number', #other options: 'Importance', 'Assignee', ,'Bug Number'
#	'field0-0-0':'short_desc',
#	'type0-0-0':'allwordssubstr',
#	'value0-0-0':'', 
#	'field0-0-1':'longdesc',
#	'type0-0-1':'allwordssubstr',
#	'value0-0-1':'',
#	'field1-0-0':'bug_status',
#	'type1-0-0':'anyexact',
#	'value1-0-0':['NEW', 'ASSIGNED', 'REOPENED', 'NEEDINFO'],
#	'field1-1-0':'anyexact',
#	'type1-1-0':'anyexact',
#	'value1-1-0':'',
#	'field1-2-0':'content',
#	'type1-2-0':'matches',
#	'value1-2-0':'',
	}
start_novell = "https://bugzilla.novell.com/"
start_redhat = "https://bugzilla.redhat.com/"
start_kernel = "https://bugzilla.kernel.org/"
settings.overrides['USER_AGENT'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/536.5 (KHTML, like Gecko) Chrome/19.0.1084.9 Safari/536.5'
settings.overrides['RANDOMIZE_DOWNLOAD_DELAY'] = True
settings.overrides['DOWNLOAD_DELAY'] = 3
settings.overrides['CONCURRENT_REQUESTS_PER_DOMAIN'] = 2
# probably needs to add constructor and destructor to open and close files
# and initialize variables

class BugzillaSpider(BaseSpider):
    name = "bugzilla"
    allowed_domains = ["bugzilla.redhat.com", "bugzilla.kernel.org", "bugzilla.novell.com"]
    query = 'kernel bug warning'
    last_date = date.today()
    folder = './data' #/var/lib/scrapyd/items/tutorial/
    start_urls = [start_novell, start_redhat, start_kernel]
    link_count = 0;
    date_file = {'bugzilla_date':None}
    pickle_fd = None
    hashes = None
    item_file = None
    raise Exception
    
    def __init__(self, *args, **kwargs):
        super(BugzillaSpider, self).__init__(*args, **kwargs)
        if kwargs.get('query'):
            self.bug_query = kwargs.get('query')
#        if kwargs.get('folder'):
#            self.folder = kwargs.get('folder')
#        else:
#            pass
#            raise CloseSpider('Folder must be specified')
        try:
            self.date_file[self.date_file.keys()[0]] = open('%s/%s' %(self.folder, self.date_file.keys()[0]), 'rb')
            self.last_date = self.date_file[self.date_file.keys()[0]].readline().strip()
            self.last_date = datetime.strptime(self.last_date, '%Y-%m-%d')
            self.last_date = self.last_date.date()
        except (OSError, IOError, ValueError):
#            self.date_file[self.date_file.keys()[0]] = open('%s%s' %(self.folder, self.date_file.keys()[0]), 'wb')
            self.last_date = date.today()
        self.link_count = 0
        # renew files with hashes every 7 days
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
        try:
#            self.pickle_fd = open("%s%s.pck" %(self.folder, self.name),"rb+")
            self.hashes = pickle.load(self.pickle_fd)
        except EOFError:
            self.hashes = set();
        self.item_file = open('bugzilla.item', 'wb+')
        atexit.register(self.save)

    def save(self):
        filename = "%s/%s.pck" %(self.folder, self.name)
        self.pickle_fd = open(filename, 'w+b')
        pickle.dump(self.hashes, self.pickle_fd)
        self.pickle_fd.close()
        self.item_file.close()

    def start_requests(self):
        for url in self.start_urls:
            i = 0
            fieldfrom = self.last_date
#            fieldfrom = fieldto - timedelta(days=10)
            while i < 3:
                i += 1
                fieldto = fieldfrom
                fieldfrom = fieldto - timedelta(days=10)
                req_url = self.create_url(url, self.query, fieldfrom, fieldto)
#               raise Exception("RANDOM EXCEPTION")
                yield Request(req_url, callback=self.parse, dont_filter=True)
        self.date_file[self.date_file.keys()[0]] = open('%s/%s' %(self.folder, self.date_file.keys()[0]), 'wb')
        self.date_file[self.date_file.keys()[0]].write('%s' %(fieldfrom.strftime('%Y-%m-%d')))
        self.date_file[self.date_file.keys()[0]].close()

    def create_url(self, base, query, fieldfrom, fieldto):
        qparams = url_params.copy()
        qparams['short_desc'] = query
        qparams['long_desc'] = query
        qparams['content'] = query
        qparams['bug_status'] = ['__open__']
        qparams['columnlist'] = ['changeddate']
        qparams['chfieldto'] = fieldto.strftime('%Y-%m-%d') #'2011-03-12'
        qparams['chfieldfrom'] = fieldfrom.strftime('%Y-%m-%d') #'2011-03-02'
        if base is start_redhat:
            qparams['short_desc_type'] = 'anywords'
        req_params = urlencode(qparams, True)
        req_url = urljoin(base, 'buglist.cgi')
        req_url += '?' + req_params
        return req_url

    def parse(self, response):
        hxs = HtmlXPathSelector(response)
        link_base = response.url.split('buglist', 1)[0]
        domain = link_base.split('.')[1]
        items = []
        if link_base == 'https://bugzilla.novell.com/':
            data = hxs.select('//td[@class]/a[contains(@href, "show_bug")]/@href|//td[@style]//div//text()').extract()
        else:
            data = hxs.select('//td[@class]/a[contains(@href, "show_bug")]/@href|//td[@style]//text()').extract()

        for link, date in zip(data, data[1:])[::2]:
            item = MyItem()
            searched_link = '%s%s' % (link_base, link)
            if searched_link:
                h = hash(searched_link)
                if h in self.hashes:
                    continue
                self.hashes.add(h)
                self.link_count += 1
                item['url'] = searched_link
                item['num'] = self.link_count
                item['length'] = len(searched_link)
                if self.dateFromString(date.strip()):
                    item['date'] = self.dateFromString(date.strip()).strftime('%Y-%m-%d')
                else:
                    item['date'] = None
                items.append(item)
                self.item_file.write('%s\n' %item['url'])
        return items

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
