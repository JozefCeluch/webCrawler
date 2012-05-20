#!/usr/bin/python -u
import subprocess
from time import sleep, strftime
import os, sys, fcntl, signal
import json, urllib2, tempfile
from datetime import datetime, timedelta, date
import optparse
import ConfigParser
import errno

done = False
STATS_STR = {'NEW DB ENTRIES':'new_entries', 'SUCCESSFUL MATCH':'found_match', 'FAILED REGEX':'failed_match',
            'FAILED DOWNLOAD':'failed_download', 'ALL URLs':'all_urls'}
STATS = {'new_entries':[], 'found_match':[], 'failed_match':[], 'failed_download':[], 'all_urls':[]}
STAT_FILE = 'webcrawler_run_stats'
START_DATE = date.today()
DAY = timedelta(days=1)
SCRAPY = 'scrapy' # command to run scrapy, if Scrapy was not installed from repositories,
                  # add whole path to 'scrapy' script, located in Scrapy/build

def parse_argv():
    opts = {'user':'jozefceluch', 'hour':None, 'minute':'00', 'reset':None, 'db':None,
            'search_id':None, 'api_key':None, 'folder':None, 'reset_now':False}
    opt_parser = optparse.OptionParser("%prog [options] config.ini") # 1st argument is usage, %prog is replaced with sys.argv[0]
    conf_parser = ConfigParser.SafeConfigParser()
    opt_parser.add_option(
        "-d", "--db",    # short and long option
#        dest="delay",       # not needed in this case, because default dest name is derived from long option
#        type="int",         # "string" is default, other types: "int", "long", "choice", "float" and "complex"
#        action="store",      # "store" is default, other actions: "store_true", "store_false" and "append"
#        default=0,          # set default value here, None is used otherwise
        help="Prepared database file",
    )
    opt_parser.add_option(
        "-u", "--user",
        help="User registered in database",
    )
    opt_parser.add_option(
        "--hour",
        help="Hour when to run crawler",
    )
    opt_parser.add_option(
        "--minute",
        help="Minute when to run crawler",
    )
    opt_parser.epilog = "To quit send SIGINT, SIGQUIT or SIGTERM. To show statistics send SIGUSR1."
    options, args = opt_parser.parse_args()
    if not args:
        args = ['config.ini']

    for ini_file in args:
        try:
            if not conf_parser.read(ini_file):
                print '%s is not valid config file' %ini_file
                sys.exit(1)
        except ConfigParser.Error:
            print '%s is not valid config file' %ini_file
            sys.exit(1)
        if conf_parser.has_section('database'):
            if conf_parser.has_option('database','file'):
                opts['db'] = conf_parser.get('database', 'file')
            if conf_parser.has_option('database','user'):
                opts['user'] = conf_parser.get('database', 'user')
        if conf_parser.has_section('time'):
            if conf_parser.has_option('time','hour'):
                opts['hour'] = conf_parser.get('time', 'hour')
            if conf_parser.has_option('time','minute'):
                opts['minute'] = conf_parser.get('time', 'minute')
        if conf_parser.has_section('scrapy'):
            if conf_parser.has_option('scrapy','reset'):
                opts['reset'] = conf_parser.get('scrapy', 'reset')
            if conf_parser.has_option('scrapy','api_key'):
                opts['api_key'] = conf_parser.get('scrapy', 'api_key')
            if conf_parser.has_option('scrapy','search_id'):
                opts['search_id'] = conf_parser.get('scrapy', 'search_id')

    if options.db:
        opts['db'] = options.db
    if options.user:
        opts['user'] = options.user
    if options.hour:
        opts['hour'] = options.hour
    if options.minute:
        opts['minute'] = options.minute
    return opts

    # use parser.error to report missing options or args:
    #parser.error("Option X is not set")

def save_stats():
    try:
        fd = open(STAT_FILE, 'a+b')
    except (IOError, OSError):
        print 'Unable to open file'
        print STATS
    fd.write('%s %s\n' %(str(date.today()), json.dumps(STATS)))
    fd.close

def print_stats():
    print 'CURRENT RUN STATS\n'
    for entry in STATS.keys():
        result = 0
        for i in STATS[entry]:
            result = result + int(i)
        print '\t%s %d' %(entry, result)
    print "\n"

def handler(signum, frame):
    global done
    if (signum == signal.SIGUSR1):
        print_stats()
    else:
        print "Program finished"
        done = 1
        save_stats()
        print_stats()

def reg_signals():
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGQUIT, handler)
    signal.signal(signal.SIGUSR1, handler)

def run_parser(spider, db, user):
    s = None
    ret = None
    try:
        s = subprocess.Popen(['./parser', '-f','%s.item' %spider, '-d', db, '-u', user], stdout=subprocess.PIPE)
    except OSError, (e, msg):
        if e == errno.ENOENT:
            print "ERROR: Parser program is not in current directory"
        print msg
        sys.exit(1)
#    while s.poll() == None:
    try:
        out = s.communicate()[0]
        for line in out.strip().split('\n'):
            try:
                name, value = line.strip().split(':')
                print name, value
                for i in STATS_STR.keys():
                    if name.strip() == i:
                        STATS[STATS_STR[name.strip()]].append(value.strip())
            except (ValueError, NameError):
                print "Error processing parser response"
                continue
        ret = s.wait()
    except (AttributeError):
        print "Error parsing results"
    return ret

def run_process(opts):
    spider_pid = {'bugzilla': None, 'google':None}
    pids=set()
    for spider in spiders:
        args=['%s runspider spiders/%s_spider.py --set reset=%s' %(SCRAPY, spider, opts['reset_now'])]
        if spider == 'google':
            args[0] += ' --set id=%s --set key=%s' %(opts['search_id'], opts['api_key'])
        p = subprocess.Popen(args, shell=True)
        spider_pid[spider]=p.pid
        pids.add(p.pid)
    while pids:
        spider=None
        pid,retval=os.wait()
        print '%s finished' %pid
        for i in spider_pid.keys():
            if spider_pid[i] == pid:
                spider = i
        pids.remove(pid)
        run_parser(spider = spider, db = opts['db'], user = opts['user'])

if __name__ == "__main__":
    reg_signals()
    opts = parse_argv()
    print opts
    reset_period = None
    try:
        reset_period = int(opts['reset']) * DAY
    except (ValueError):
        reset_period = 30 * DAY

    reset_date = START_DATE + reset_period
    spiders = ['bugzilla', 'google']

    hrs = opts['hour']
    mins = opts['minute']
    if hrs == None:
        hrs = strftime('%H')
    if mins == None:
        mins = '00'
    if len(hrs) == 1:
        hrs = '0%s'%hrs
    if len(mins) == 1:
        mins = '0%s' % mins
    try:
        int(hrs)
        int(mins)
    except (ValueError):
        print 'Input error, insert valid numbers'
        sys.exit(1)

    print "PID: %s" %os.getpid()
    curr_time = datetime.now().replace(microsecond=0)
    usr_time = curr_time.replace(hour=int(hrs), minute=int(mins), microsecond=0)
    print "Run program at: %s:%s" %(hrs, mins)
    while True:
        if done:
            break
        print "Time: %s" %strftime('%H:%M:%S')
        if curr_time.date() == reset_date:
            opts['reset_now'] = True
            reset_date = reset_date + reset_period
            print 'Search reset'
        else:
            opts['reset'] = False
#        if strftime('%H') == hrs and strftime('%M') == mins:
        if datetime.now().replace(second=0, microsecond=0) == usr_time.replace(second=0):
            run_start = datetime.now()
            print "process started: %s" %run_start
            run_process(opts)
            run_end = datetime.now()
            print "process finished: %s" %run_end
            runtime = run_end - run_start
            if ((runtime.microseconds + (runtime.seconds + runtime.days * 24 * 3600) * 10**6) / 10**6) < 60:
                print 'Process ran less than a minute'
                sleep(60 - ((runtime.microseconds + (runtime.seconds + runtime.days * 24 * 3600) * 10**6) / 10**6))
            usr_time = usr_time.replace(second=0) + DAY
        else:
            curr_time = datetime.now().replace(microsecond=0)
            sleep_time = usr_time - curr_time - timedelta(seconds=usr_time.second-1)
            if ((sleep_time.microseconds + (sleep_time.seconds + sleep_time.days * 24 * 3600) * 10**6) / 10**6) < 0:
                sleep_time = DAY + sleep_time
                usr_time = usr_time.replace(second=0) + DAY
            print "Sleeping until %s" %(sleep_time + curr_time)
            sleep((sleep_time.microseconds + (sleep_time.seconds + sleep_time.days * 24 * 3600) * 10**6) / 10**6)

#def run_spider(spider, options):
#    """ Unused method to run spider
#        Method to run spider through scrapyd daemon. This is not used by default
#        because all spiders run in local folder and are not managed by the daemon.
#        Should be usable with minor updates.
#
#    """
#    url = 'http://%s:%s/schedule.json' %(options['server'], options['port'])
#    proj = 'project=%s' %options['project']
#    spid = 'spider=%s' %spider
#    fldr = 'folder=%s' %options['folder']
#    raise Exception
#    s = subprocess.Popen(['curl','-s', url, '-d', proj, '-d', spid, '-d', fldr], stdout=subprocess.PIPE)
#    (out, err) = s.communicate()
#    print out, err
#    out = out.strip('{}\n')
#    out = out.split(',')
#    ok = False
#    for item in out:
#        (key, value) = item.split(':')
#        key = key.strip(' \"')
#        value = value.strip(' \"')
#        print key, value
#        if ok:
#            return value
#        if key == 'status' and value == 'ok':
#            ok = True
#    if not ok:
##        raise exception
#        print "Spider did not start successfully"

#def get_items(opts, job_id):
#    """ Unused method to retrieve items from spider
#    """
#    url = 'http://%s:%s/listjobs.json?project=%s' %(opts['server'], opts['port'], opts['project'])
#    done = False
#    spider_name = None
#    while not done:
#        s = subprocess.Popen(['curl','-s', url], stdout = subprocess.PIPE)
#        (out, err) = s.communicate()
#        out = json.loads(out)
#        for i in out['finished']:
#            if i['id'] == job_id:
#                spider_name = i['spider']
#                done = True
#        if not done:
#            print 'Waiting for crawl to finish'
#            sleep(10)
#    url = 'http://localhost:6800/items/tutorial/%s/%s.jl' %(spider_name, job_id)
#    f = tempfile.TemporaryFile()
#    g = open("%s"%job_id, "wb+")
#    data = urllib2.urlopen(url).read()
#    f.write(data)
#    f.seek(0)
#    lines = []
#    for line in f.readlines():
#        line = json.loads(line)
#        g.write('%s\n' %line['url'])
#    g.close()
#    f.close()
#    
