#!/usr/bin/python
import subprocess
from time import sleep, strftime
import os, sys, fcntl, signal
import json, urllib2, tempfile
from datetime import datetime, timedelta, date
import optparse
import ConfigParser

done = False
STATS_STR = {'NEW DB ENTRIES':'new_entries', 'SUCCESSFUL MATCH':'found_match', 'FAILED REGEX':'failed_match',
            'FAILED DOWNLOAD':'failed_download', 'ALL URLs':'all_urls'}
STATS = {'new_entries':[], 'found_match':[], 'failed_match':[], 'failed_download':[], 'all_urls':[]}
START_DATE = date.today()
DAY = timedelta(days=1)

def parse_argv():
#    probably move first 3 options to the C program and save as macros
    opts = {'user':'jiryslaby', 'hour':None, 'minute':'00', 'days':'7', 'reset':'0', 'db':None}
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
        "-u", "--user",    # short and long option
#        dest="delay",       # not needed in this case, because default dest name is derived from long option
#        type="int",         # "string" is default, other types: "int", "long", "choice", "float" and "complex"
#        action="store",      # "store" is default, other actions: "store_true", "store_false" and "append"
#        default=0,          # set default value here, None is used otherwise
        help="User registered in database",
    )
    opt_parser.add_option(
        "--hour",    # short and long option
#        dest="delay",       # not needed in this case, because default dest name is derived from long option
#        type="int",         # "string" is default, other types: "int", "long", "choice", "float" and "complex"
#        action="store",      # "store" is default, other actions: "store_true", "store_false" and "append"
#        default=0,          # set default value here, None is used otherwise
        help="Hour when to run crawler",
    )
    opt_parser.add_option(
        "--minute",    # short and long option
#        dest="delay",       # not needed in this case, because default dest name is derived from long option
#        type="int",         # "string" is default, other types: "int", "long", "choice", "float" and "complex"
#        action="store",      # "store" is default, other actions: "store_true", "store_false" and "append"
#        default='00',          # set default value here, None is used otherwise
        help="Minute when to run crawler",
    )
    opt_parser.epilog = "To quit send SIGINT, SIGQUIT or SIGTERM. To show statistics send SIGUSR1."
    options, args = opt_parser.parse_args()
    # options.key = value
    # args = [arg1, ... argN]

    for ini_file in args:
        conf_parser.read(ini_file)
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
                print opts['minute']
        if conf_parser.has_section('scrapy'):
            if conf_parser.has_option('scrapy','days'):
                opts['days'] = conf_parser.get('scrapy', 'days')
            if conf_parser.has_option('scrapy','project'):
                opts['project'] = conf_parser.get('scrapy', 'project')

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

def print_stats():
    for entry in STATS.keys():
        result = 0
        for i in STATS[entry]:
            result = result + int(i)
        print '%s %d' %(entry, result)

def handler(signum, frame):
    global done
    if (signum == signal.SIGUSR1):
        print "SIGUSR1"
        print_stats()
    else:
        print "Program finished"
        print_stats()
        done = 1

def reg_signals():
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGQUIT, handler)
    signal.signal(signal.SIGUSR1, handler)

def run_parser(spider, db, user):
    s = subprocess.Popen(['./webCrawler', '-f','%s.item' %spider, '-d', db, '-u', user], stdout=subprocess.PIPE)
    finished = False
    while s.poll() == None:
        out = s.stdout.read()
        s.stdout.flush()
        if len(out)> 0:
	        print "program: %s" %out.strip()
        if finished:
            (name, value) = out.strip().split(':')
            for i in STATS_STR.keys():
                if name.strip() == i:
                    STATS[STATS_STR[name.strip()]].append(value.strip())
        if out.strip() == 'FINISHED':
            finished = True
#        except IOError as err:
#            print err.errno
#            print err.strerror
    ret = s.wait()
    return ret

def run_process(opts):
    spider_pid = {'bugzilla': None, 'google':None}
    pids=set()
    for spider in spiders:
        args=['scrapy runspider %s_spider.py' %spider]
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
    try:
        reset_date = START_DATE + timedelta(days=int(opts['reset']))
    except ValueError:
        reset_date = START_DATE + timedelta(days=52)
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
    print hrs, mins
    raise Exception
    print "PID: %s" %os.getpid()
    curr_time = datetime.now().replace(second=0, microsecond=0)
    usr_time = curr_time.replace(hour=int(hrs), minute=int(mins), second=0, microsecond=0)
    print "Run program at: %s:%s" %(hrs, mins)
    while True:
        if done:
            break
        print "Time: %s" %strftime('%H:%M:%S')
        if strftime('%H') == hrs and strftime('%M') == mins:
            run_start = datetime.now()
            print "process started: %s" %run_start
            run_process(opts)
            run_end = datetime.now()
            print "process finished: %s" %run_end
            runtime = run_end - run_start
            if (runtime.total_seconds() < 60):
                sleep(60 - runtime.total_seconds())
        else:
            curr_time = datetime.now().replace(second=0, microsecond=0)
            sleep_time = usr_time - curr_time
            if sleep_time.total_seconds() < 0:
                sleep_time = DAY + sleep_time
            print "Sleeping until %s" %(sleep_time)
            sleep(sleep_time.total_seconds()-1)

#def run_spider(spider, options):
#    url = 'http://%s:%s/schedule.json' %(options['server'], options['port'])
#    proj = 'project=%s' %options['project']
#    spid = 'spider=%s' %spider
#    fldr = 'folder=%s' %options['folder']
#    days = 'days=%s' %options['days']
#    print options['folder'], options['days']
#    raise Exception
#    s = subprocess.Popen(['curl','-s', url, '-d', proj, '-d', spid, '-d', fldr, '-d', days], stdout=subprocess.PIPE)
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
