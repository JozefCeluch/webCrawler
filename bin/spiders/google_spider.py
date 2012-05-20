from scrapy.http import Request
from scrapy.conf import settings
from scrapy.spider import BaseSpider
from items import MyItem
from scrapy.exceptions import CloseSpider

from copy import copy
import cPickle as pickle
import os.path, atexit, errno

from datetime import datetime, date, timedelta
from urllib import urlencode
import urlparse, json
import logging
from scrapy.log import ScrapyFileLogObserver
#date parsing module, not used by default, more info http://code.google.com/p/parsedatetime/
#import parsedatetime.parsedatetime as pdt

"""Creates the folder if it doesn't exist already'"""
FOLDER = './data'
try:
    os.mkdir(FOLDER)
except OSError, e:
    if e.errno != errno.EEXIST:
        raise Exception("Can't create directory'")

"""Enables loging into file and to standard output"""
logfile = open('%s/google.log' %FOLDER, 'a+b')
log_observer = ScrapyFileLogObserver(logfile, level=logging.DEBUG)
log_observer.start()

"""Google custom search API query parameters
Required prameters are:
cx - custom search engine unique ID
key - unique API key, provides API access
q - search query
other parameters are optional: 
filter - 0 disables duplicate content filter (default is 1)
sort - date:a - ascending sort by date
dateRestrict - w[number] - restrict results to number of weeks
more info:
https://developers.google.com/custom-search/v1/using_rest#query-params
"""
PARAMS = {
    'dateRestrict' : 'w0',
    'filter' : '0',
    'sort' : 'date:a',
    'q' : '',
    'start' : '1', # range between 1 and 91
    'cx' : '',
    'key' : '',
}

""" Spider specific settings
More options can be found at http://doc.scrapy.org/en/latest/topics/settings.html

"""
settings.overrides['RANDOMIZE_DOWNLOAD_DELAY'] = True
settings.overrides['DOWNLOAD_DELAY'] = 2
settings.overrides['CONCURRENT_REQUESTS_PER_DOMAIN'] = 8
settings.overrides['USER_AGENT'] = 'scrapy_bot/0.1 Scrapy/0.15'
#settings.overrides['SPIDER_MIDDLEWARES'] = {'scrapy.contrib.spidermiddleware.httperror.HttpErrorMiddleware':1}

class GoogleSpider(BaseSpider):
    """
    Defines Scrapy spider for Google Custom Search API

    It is meant to be run with 'scrapy runspider' command, not as a part of a Scrapy
    project but as a standalone spider even thought it should work in a project as well.
    To run throught scrapyd the FOLDER constant needs to be set to some absolute
    path where scrapyd has writing access, since spider creates some files.

    """
    name = "google"
    allowed_domains = ["googleapis.com"]
    start_urls = ["https://www.googleapis.com/"]
    query = '"kernel bug" OR "kernel warning"'
    link_count = None
    weeks = 10              # number of weeks searched in one run
    last_search = 0         # week number, where previous search finished
    date_file = None        # file containing dates variable in pickled format
    dates = {'pickle': None, 'search': None}
    hashes = None           # set of url hashes
    pickle_fd = None        # pickled hashes variable
    reset = False           # used to restart spider crawl
    error_resp = 0           # number of errorneous responses from google before shutdown
    api_key = None
    search_id = None
    handle_httpstatus_list = [400, 401, 403, 404, 405, 413, 500]

    def __init__(self, *args, **kwargs):
        """Class constructor

        Settings arguments are set by running the spider with option '--set option=VALUE'.
        Opens all files and sets all class variables to either default values or 
        values from the opened files. Api key and search_id must be set or spider closes
        prematurely.
        """
        if settings.get('reset'):
            self.reset = settings.get('reset')
        if settings.get('id'):
            self.search_id = settings.get('id')
        if settings.get('key'):
            self.api_key = settings.get('key')

        if (not self.api_key) or (not self.search_id):
            raise Exception("API Key and search engine ID must be defined")
        try:
            self.date_file = open('%s/%s' %(FOLDER, 'google_date'), 'a+b')
#            self.last_search = int(self.date_file[self.date_file.keys()[0]].readline().strip())
            self.dates = pickle.load(self.date_file)
            self.last_search = self.dates['search']
#            print self.dates
#            print "\n\n\n", self.last_search, self.dates['search'], "\n"
        except (IOError, EOFError, pickle.UnpicklingError):
            self.date_file= open('%s/%s' %(FOLDER, 'google_date'), 'a+b')
            self.last_search = 0
            self.dates['search'] = self.last_search
            self.dates['pickle'] = None

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

        print self.dates['pickle'], self.dates['search']
#        raise Exception
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
        if self.reset == 'True':
            print "Google search reset"
            self.last_search = 0
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
        pages = 100/self.weeks
        i = 0
        while i < self.weeks:
            pg_count = 0
            while pg_count < pages:
                url = self.create_url(self.start_urls[0], self.query, (pg_count*10)+1, self.last_search+i)
                pg_count += 1
#                print url
                yield Request(url, callback=self.parse)
            i += 1
        print self.last_search
        self.dates['search'] = self.last_search + i

    def parse(self, response):
        """ Parsing method

        This is where the magic happens. Since the response is formatted as JSON
        parsing consists only of converting JSON string to dictionary structure and
        saving the url from each item. Spider closes in case there are too many error responses.

        @param response Response to tehe Request yielded in start_request
        """
#        date = None
        items = []
        if (response.status >= 400):
            if response.status == 400:
                print 'Bad request - The request has syntax error.'
            elif response.status == 401:
                print 'Authorization failure'
            elif response.status == 403:
                print 'Forbidden - Daily limit reached'
            elif response.status == 404:
                print 'Resource not found'
            elif response.status == 405:
                print 'Method not allowed'
            elif response.status == 413:
                print 'File too large'
            elif response.status == 500:
                print 'Server error'
            print 'For more information: https://developers.google.com/custom-search/docs/api#status_code'
            raise CloseSpider('Too many error responses')

        res = json.loads(response.body)
        res_num = int(res['searchInformation']['totalResults'])
        if res_num > 0:
            for i in res['items']:
                item = MyItem()
                try:
                    h = hash(i['link'])
                    if h in self.hashes:
                        continue
                    self.hashes.add(h)
                    self.link_count += 1
                    item['url'] = i['link']
#                    item['num'] = self.link_count
#                    item['length'] = len(i['link'])
#                    item['date'] = date
                    print item
                    self.item_file.write('%s\n' %item['url'])
                    items.append(item)
                except (KeyError, IndexError) :
                    print "Item Error"
                    pass
        return items

    def create_url(self, base, query, start_num, week):
        """ Puts together the request url

        Using urlencode creates url that is requested from server.
        @param base 
        @param query Searched query
        @param start_num Technically it means page number
        @param week Number of weeks in the past that are included in search
        """
        qparams = PARAMS.copy()
        qparams['q'] = query
        qparams['start'] = str(start_num)
        qparams['dateRestrict'] = 'w%s' %week
        qparams['cx'] = self.search_id
        qparams['key'] = self.api_key
        req_params = urlencode(qparams, True)
        req_url = urlparse.urljoin(base, 'customsearch/v1')
        req_url += '?' + req_params
        return req_url

#    def filter_result(self, link):
#    """ Filters Google related domains

#    Originally used to filter urls when using Google web interface, obsolete when
#    using API
#    """
#        try:
#            # Valid results are absolute URLs not pointing to a Google domain
#            # like images.google.com or googleusercontent.com
#            o = urlparse.urlparse(link, 'http')
#            if o.netloc and 'google' not in o.netloc:
#                return link

#            # Decode hidden URLs.
#            if link.startswith('/url?'):
#                link = urlparse.parse_qs(o.query)['q'][0]

#            # Valid results are absolute URLs not pointing to a Google domain
#            # like images.google.com or googleusercontent.com
#            o = urlparse.urlparse(link, 'http')
#            if o.netloc and 'google' not in o.netloc:
#                return link

#        # Otherwise, or on error, return None.
#        except Exception:
#            pass
#        return None

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
#        # 0 = failed to parse
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
