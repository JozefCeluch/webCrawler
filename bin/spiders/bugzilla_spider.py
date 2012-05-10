
from urllib import urlencode
from urlparse import urljoin
from scrapy.selector import HtmlXPathSelector
from scrapy.http import Request
from scrapy.conf import settings
from scrapy.spider import BaseSpider
from scrapy.exceptions import CloseSpider
from items import MyItem
import cPickle as pickle
import os.path, atexit, errno
from datetime import datetime, date, timedelta
import logging
# enables logging to file and to stdout at the same time
from scrapy.log import ScrapyFileLogObserver
#date parsing module, not used by default, more info http://code.google.com/p/parsedatetime/
#import parsedatetime.parsedatetime as pdt

FOLDER = './data'
try:
    os.mkdir(FOLDER)
except OSError, e:
    if e.errno != errno.EEXIST:
        raise Exception("Can't create directory'")

logfile = open('%s/bugzilla.log' %FOLDER, 'a+b')
# for debugging set level to DEBUG other values INFO, WARNING, ERROR, CRITICAL
log_observer = ScrapyFileLogObserver(logfile, level=logging.DEBUG)
log_observer.start()

URL_PARAMS = {
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
	'order': 'Bug Number', #other options: 'Importance', 'Assignee', ,'Bug Number'
	}
start_novell = "https://bugzilla.novell.com/"
start_redhat = "https://bugzilla.redhat.com/"
start_kernel = "https://bugzilla.kernel.org/"

""" Spider specific settings
More options can be found at http://doc.scrapy.org/en/latest/topics/settings.html

"""
settings.overrides['USER_AGENT'] = 'scrapy_bot/0.1 Scrapy/0.15' 
settings.overrides['RANDOMIZE_DOWNLOAD_DELAY'] = True
settings.overrides['DOWNLOAD_DELAY'] = 3
settings.overrides['CONCURRENT_REQUESTS_PER_DOMAIN'] = 4
#settings.overrides['LOG_ENABLED'] = False
#settings.overrides['LOG_FILE'] = 'bugzilla.log'
#settings.overrides['LOG_LEVEL'] = 'INFO'

class BugzillaSpider(BaseSpider):
    """
    Defines Scrapy spider for crawling Bugzilla type sites

    It is meant to be run with 'scrapy runspider' command, not as a part of a Scrapy
    project but as a standalone spider even thought it should work in a project as well.
    To run throught scrapyd the FOLDER constant needs to be set to some absolute
    path where scrapyd has writing access, since spider creates some files.

    """
    name = "bugzilla"
    allowed_domains = ["bugzilla.redhat.com", "bugzilla.kernel.org", "bugzilla.novell.com"]
    query = 'kernel bug warning'

    last_search = None      # date when the previous search stopped
    start_urls = [start_novell, start_redhat, start_kernel]
    link_count = 0;
#    date_file = {'bugzilla_date':None}
    date_file = None        # file containig dates dict in pickled format
    dates = {'pickle': '', 'search':''}
    pickle_fd = None        # file containing pickled hashes of links
    hashes = None           # set of hashed links
    item_file = None        # file containing extracted URLs
    reset = False           # used to restarts the spider to the current date
    error_resp = 0           # maximum number of error responses before shutdown

    def __init__(self, *args, **kwargs):
        """Class constructor

        Settings arguments are set by running the spider with option '--set option=VALUE'.
        Opens all files and sets all class variables to either default values or 
        values from the opened files.
        """
        if settings.get('reset'):
            self.reset = settings.get('reset')
        try:
            self.date_file = open('%s/%s' %(FOLDER, 'bugzilla_date'), 'a+b')
#            self.start_week = int(self.date_file[self.date_file.keys()[0]].readline().strip())
            self.dates = pickle.load(self.date_file)
            self.last_search = self.dates['search']
        except (IOError, EOFError, pickle.UnpicklingError):
            self.date_file= open('%s/%s' %(FOLDER, 'bugzilla_date'), 'a+b')
            self.last_search = date.today()
            self.dates['search'] = self.last_search
            self.dates['pickle'] = None

        # renew files with hashes every 7 days
        filename = "%s/%s.pck" %(FOLDER, self.name)
        try:
            file_time = self.dates['pickle']
            delta = datetime.now() - file_time
            self.pickle_fd = open(filename, 'a+b')
            if delta.days > 7:
                self.pickle_fd.truncate(0)
                self.dates['pickle'] = datetime.now()
        except (TypeError, IOError):
                self.pickle_fd = open(filename, 'a+b')
                self.pickle_fd.truncate(0)
                self.dates['pickle'] = datetime.now()

        try:
            self.hashes = pickle.load(self.pickle_fd)
        except (pickle.UnpicklingError, EOFError):
            self.hashes = set();
        try:
            self.item_file = open('%s.item' %self.name, 'wb+')
        except IOError:
            raise CloseSpider('No writing access in this folder')
        self.link_count = 0
        atexit.register(self.save)
        if self.reset:
            print "Search reset"
            self.last_search = date.today()
            self.dates['search'] = self.last_search
            self.dates['pickle'] = datetime.now()
            self.pickle_fd.truncate(0)
            self.hashes = set()

    def save(self):
        """ Method registerd to be executed atexit

        Saves all files that are needed to be kept between searches, according to some 
        Scrapy forums, this is not the best practice how to register something to be
        executed when spider closes, but it seems to work.

        """
        self.item_file.close()
        self.pickle_fd.truncate(0)
        self.date_file.truncate(0)
        pickle.dump(self.hashes, self.pickle_fd)
        pickle.dump(self.dates, self.date_file)
        self.pickle_fd.close()
        self.date_file.close()

    def start_requests(self):
        """ Starting point of spider

        Method creates reguests for all spidered pages. Yielded Request objecs are
        queued by Scrapy and then executed according to some inner scheduling and also
        in accordance to the set settings.
        """
        for url in self.start_urls:
            i = 0
            fieldfrom = self.last_search
#            fieldfrom = fieldto - timedelta(days=10)
            while i < 3:
                i += 1
                fieldto = fieldfrom
                fieldfrom = fieldto - timedelta(days=10)
                req_url = self.create_url(url, self.query, fieldfrom, fieldto)
#                print req_url
                yield Request(req_url, callback=self.parse, dont_filter=True)
        self.dates['search'] = fieldfrom

    def create_url(self, base, query, fieldfrom, fieldto):
        """ Puts together the request url

        Using urlencode creates url that is requested from server.
        @param base 
        @param query Searched query
        @param fieldfrom Lower boundary of date limit
        @param fieldto Upper boundary of date limit
        """
        qparams = URL_PARAMS.copy()
        qparams['short_desc'] = query
        qparams['long_desc'] = query
        qparams['content'] = query
        qparams['bug_status'] = ['__open__']
        qparams['columnlist'] = ['changeddate']
        qparams['chfieldto'] = fieldto.strftime('%Y-%m-%d') #'YYYY-MM-DD'
        qparams['chfieldfrom'] = fieldfrom.strftime('%Y-%m-%d')
        if base is start_redhat:
            qparams['short_desc_type'] = 'anywords'
        req_params = urlencode(qparams, True)
        req_url = urljoin(base, 'buglist.cgi')
        req_url += '?' + req_params
        return req_url

    def parse(self, response):
        """ Parsing method

        This is where the magic happens. The used XPath selector also extracts dates
        from the page but they can be in various formats and non-standard module is needed
        for conversion to unified format. Extracted urls are saved to file. Other values 
        are not necessary, but may bye used if needed in which case they also must be 
        added in items.py file.
        """
        if (response.status >= 400):
            self.error_resp += 1
            print "Page not found"
            if self.error_resp > 10:
                raise CloseSpider('Too many error responses')
            return None
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
#                item['num'] = self.link_count
#                item['length'] = len(searched_link)
#                if self.dateFromString(date.strip()):
#                    item['date'] = self.dateFromString(date.strip()).strftime('%Y-%m-%d')
#                else:
#                    item['date'] = None
                items.append(item)
                self.item_file.write('%s\n' %item['url'])
        return items

#    def dateFromString(self, in_str):
#        """ Date converter

#        Uses parsedatetime module to convert date and time to corresponding date
#        therefore it is not used by default since dates are not necessary. Also if date is
#        in format for example 'Fri 13:30' it is assumed that it is last Friday
#        """
#        s = in_str.strip()
#        if len(s) > 12 or len(s) < 5:
#            return None
#        dt = None
#        try:
#            dt = datetime.strptime(s, '%Y-%m-%d').date()
#            if dt:
#                return dt
#        except (ValueError, TypeError, IndexError):
#            pass

#        dt = None
#        now = date.today()
#        c = pdt.Calendar()
#        result, what = c.parse(s)

#        # what was returned (see http://code-bear.com/code/parsedatetime/docs/)
#        # 1 = date (with current time, as a struct_time)
#        # 2 = time (with current date, as a struct_time)
#        # 3 = datetime
#        if what in (1,2):
#            dt = date(*result[:3])
#            if (dt == now):
#                try:
#                    d = datetime.strptime(s, '%Y-%m-%d').date()
#                    if (d) and (d != now):
#                        dt = d
#                except (ValueError, TypeError, IndexError):
#                    pass
#        elif what == 3:
#            dt = date(*result[:3])
#        else:
#            return None
#        if (now-dt) < timedelta(0) and (now-dt) >= timedelta(days=-7):
#            dt = dt - timedelta(days=7)
#        elif (now-dt) < timedelta(days=-7):
#            dt = None
#        if dt:
#            return dt
#        else:
#            return None
