#!/usr/bin/env python
import sys
import getopt
import os
import cPickle as pickle
import commands
import time
import re
import argparse
import logging
import fcntl
import subprocess
from functools import wraps

logger = None
logging.basicConfig()
logger = logging.getLogger('sfp_poll')
logger.setLevel(logging.INFO)

CACHE_FILE = "/tmp/.OnlSfps.cache."
PORT_NUM = 65
g_dist_codename = os.popen('cat /etc/onl/platform').read().strip() 
#g_dist_codename = os.popen('cat ./platform').read().strip()

INIT_EEPROM = {'time':0, 'data':'','interval': 5}
DATA = {'is_UpToDate': False,
        'port_num': PORT_NUM,
        'presence': {'time':0, 'bitmap':0, 'interval': 5},
        'eeprom' : {0:{'time':0, 'data':'','interval': 5}},
        }

def usage():
    print "usage: {} [-f command_file] [-a ipv4_addr] [-p port] [-c command [-c comand] ...]".format(__file__)

class Lock(object):
    """File Locking class."""

    def __init__(self, filename):
        self.filename = filename
        self.handle = open(filename, 'w')

    def take(self):
        # logger.debug("taking lock %s" % self.filename)
        fcntl.flock(self.handle, fcntl.LOCK_EX)
        # logger.debug("took lock %s" % self.filename)

    def give(self):
        fcntl.flock(self.handle, fcntl.LOCK_UN)
        # logger.debug("released lock %s" % self.filename)

    def __enter__(self):
        self.take()

    def __exit__(self ,type, value, traceback):
        self.give()

    def __del__(self):
        self.handle.close()

class OnlCpld(object):
    BFCMD = "do_bfshell.py -c ucli -c .. -c .. -c bf_pltfm -c cp2112 -c "
    CPLD_ADDR = '0x64'    #bfshell take 8-bits I2C address.

    def __init__(self, cmd):
        if cmd == "cpldr":
            self.rw = 0
        if cmd == "cpldw":
            self.rw = 1

    def access(self, address, data):
        rwcmd = [ "write-read-unsafe 1 %s 1 1 " % self.CPLD_ADDR
                  , "write 1 %s 2 "% self.CPLD_ADDR ]
                  
        subcmd = [rwcmd[0] + "%s" % address, 
                  rwcmd[1] + "%s %s" % (address, data) ]                    
            
        cmd = self.BFCMD + "\'" + subcmd[self.rw] + "\'"    
        lines = os.popen(cmd).readlines()
        
        ret = False    
        for line in lines:
            mt = re.search('SUCCESS', line)
            if mt != None:
                ret = True
                break
        byte = 0
        if self.rw == 0: 
            last = lines[-1].strip()
            raw = last.split()
            byte = chr(int(raw[0],16))
        return ret, byte


class OnlSfp(object):
    BFCMD = "do_bfshell.py -c ucli -c .. -c .. -c bf_pltfm -c qsfp -c "
    EEPROM_BYTES = 256
    cache_file = ""

    def __init__(self):
        global DATA

        total = DATA['port_num']
        self.total = total 
        self.cache_file = CACHE_FILE + "%s" % g_dist_codename
        self.load()
        for p in range(1, total):
            if DATA['eeprom'].has_key(p) == False:
                DATA['eeprom'][p] = {'time':0, 'data':'','interval': 5} 
        self.save() 

 
    def get_cache_file(self):
        return self.cache_file
        
    def run_command(self, command):
        p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         shell=True)
        return p

    def _syscmd(self, cmd):
        status, output = commands.getstatusoutput(cmd)
        #p = self.run_command(cmd)
        #output = p.stdout.read() 
        #status = True 
        #print "cmd:%s" % cmd
        #output = '0xfffffffffff'
        #status = True
        return  status, output
        
    def is_upToDate(self, last, interval):
        now = time.time()
        if now < (last + interval):
            return True, last
        else:
            return False, now 
        
    def get_present(self):
        global DATA    
        last = DATA['presence']['time']    
        interval = DATA['presence']['interval']            
        ret, DATA['presence']['time'] = self.is_upToDate(last, interval)
        if ret == True:
            DATA['is_UpToDate'] = True
        else:
            DATA['is_UpToDate'] = False
            subcmd = "get-pres"
            cmd = self.BFCMD + "\'" + subcmd + "\'"    
            st, log = self._syscmd(cmd)
            if st != 0:
                return False
            mt = re.findall("0x[\da-z]+" , log)    
            if mt == None:
                return False
            bitmap = "" 
            for e in mt:
                bitmap = bin(int(e[2:], 16))[2:].zfill(32) + bitmap
            
            DATA['presence']['bitmap'] = bitmap[::-1]
        return True
        
    def load(self, rebuildcache=False):
        global DATA
        CACHE = self.cache_file
        if rebuildcache == True:
            logger.debug("Removing package cache %s" % CACHE)
            os.unlink(CACHE)

        # Lock the CACHE file
        with Lock(CACHE + ".lock"):
           if os.path.exists(CACHE):
               logger.debug("Loading from package cache %s" % CACHE)
               DATA = pickle.load(open(CACHE, "rb"))
               #print "load time:%d" % DATA['presence']['time']
               
    def save(self):
        CACHE = self.cache_file
        # Lock the CACHE file
        with Lock(CACHE + ".lock"):
           pickle.dump(DATA, open(CACHE, "wb"))
           #print "save time:%d" % DATA['presence']['time']
           return

           
    def _strip_pg0(self, log):  
        input = log.replace("\r", "")
        input = input.replace("\n", "")
        input = re.sub(r"Byte Bit\(s\) Field(.+)", "", input)
        p = re.compile(r'(QSFP \d+)(.*?)(Page \d+:)', re.I+re.S)
        while True:
           output = p.sub(r'\1 \3',input)
           if output == input:
                break
           input = output
        buf = input
        buf += "QSFP 1023"

        return buf   

    def poll_all_eeprom(self):
        global DATA
        subcmd = "pg0"
        cmd = self.BFCMD + "\'" + subcmd + "\'"

        st, log = self._syscmd(cmd)
        if st != 0:
            return None
        buf = self._strip_pg0(log)
        pp = []
        tmp = re.split("QSFP ", buf)
        for a in tmp:
            mt = re.search("Page \d+", a)
            if mt != None:
                pp.append(a)

        #slice all data into port[page]
        portd = {}
        for p in pp:
            m = re.match("(\d+)", p)
            if m == None:
                 continue
            port = "Port " + m.group(1)
            portd[port] = {}
            last_pg = "" 
            for match in re.finditer("Page \d+", p):
                s = match.start()
                e = match.end()
                pg_str = p[s:e]
                portd[port][p[s:e]] = {}
                portd[port][pg_str]['end'] = e
                portd[port][p[s:e]]['in'] = p[e:]
                if last_pg != "":
                    last_e = portd[port][last_pg]['end']
                    portd[port][last_pg]['in'] = p[:s] 
                last_pg = pg_str

        for prt in portd:
            for pg in portd[prt]:
                if pg != "Page 0":
                    continue
                dct_pg = portd[prt][pg]
                dct_pg['rom'] = [0] * self.EEPROM_BYTES
                bulk = dct_pg['in']
                #for m1 in re.finditer(" \d+ :[ \da-z]+ :?", dct_pg['in']):
                for m1 in re.finditer("\d+ : (\w\w ){16}", bulk):
                    eeprom = dct_pg['rom']
                    m2 = re.findall('[\da-z]+', bulk[m1.start():m1.end()])
                    offset = int(m2[0])
                    eeprom[offset:] = m2[1:17]
                if pg == "Page 0":
                    # for bfshell is 1-based
                    port = int(prt.split()[1]) - 1
                    DATA['eeprom'][port]['data'] = eeprom          
                    now = time.time()
                    DATA['eeprom'][port]['time'] = now

        return None
    
    def read_eeprom(self, port):
        totoal = DATA['port_num']
        interval = DATA['eeprom'][0]['interval']
        now = time.time()
        #scour overdue data
        for p in range(0, totoal):
            if DATA['eeprom'].has_key(p):
                if now > (DATA['eeprom'][p]['time'] + interval):
                    DATA['eeprom'][p]['data'] = None
        
        #return if port's eeprom is up-to-date
        if now <= (DATA['eeprom'][port]['time'] + interval):
            if DATA['eeprom'][port]['data'] != None:                    
                return DATA['eeprom'][port]['data']
                    
        self.poll_all_eeprom()
        return DATA['eeprom'][port]['data']
 
def _is_port_valid(port):
    if port == None:
        return False
    if port < 0 or port >=PORT_NUM:
        return False
    return True    
    
def check_port(func):
    def check(*args):
        if len(args) == 0:
            return False
        if _is_port_valid(args[0]) == False:
            return False
        return func(*args)
    return check
 
def poll_presence():
    pm = OnlSfp()
    pm.load()
    ret = pm.get_present()
    if DATA['is_UpToDate'] == False:
        pm.save()
    return ret, DATA['presence']['bitmap']
    
@check_port
def poll_eeprom(port):
    pm = OnlSfp()
    pm.load()    
    pm.read_eeprom(port)
    pm.save()
    return True
     
def how_many_port_in(bitmap):
    c = 0
    for i in range(PORT_NUM):
        if bitmap[i] == '0':
            c = c + 1 
    return c


def hex_to_int(data):
   ol = [] 
   for h in data:
       ol.append(int(h, 16))
   return ol
 
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action='store_true')
    ap.add_argument("--verbose", action='store_true')    
    ap.add_argument("-p", dest="port_index", help="Which port", type=int)  
    ap.add_argument("-addr", dest="cpld_offset", help="Address to access", type=str)  
    ap.add_argument("-data", dest="cpld_data", help="data to write", type=str)    
    ap.add_argument("subcmd", help="presence/eeprom/cpldr/cpldw/clean")
    
    ops = ap.parse_args()    
    program = os.environ.get('_')
    
    logger.setLevel(logging.INFO)
    if ops.quiet:
        logger.setLevel(logging.ERROR)
    if ops.verbose:
        logger.setLevel(logging.DEBUG)    
        
    if ops.subcmd=='clean':
        pm = OnlSfp()
        file = pm.get_cache_file()
        if os.path.exists(file):
            os.unlink(file) 
            print "Cache(%s) removed!" % file
        return

    if ops.subcmd == 'cpldw' or ops.subcmd == 'cpldr':    
        offset = ops.cpld_offset
        if offset == None:        
            return
        data = ''
	if 'cpld_data' in ops:
            data = ops.cpld_data

        cpld = OnlCpld(ops.subcmd)        
        ret, data = cpld.access(offset, data)
        if ret == True and ops.subcmd == 'cpldr':
            print data
        return        
       
    port = ops.port_index
    if ops.subcmd=='presence':
        ret, bitmap = poll_presence()
        if ret == True:
            if port == None:
                print bitmap
            else: 
                print bitmap[port] 

    if ops.subcmd=='eeprom':
        if port == None:
            print "Cannot print all eeprom"    
            
    #update present status to reduce invalid read.
        ret, bitmap = poll_presence()
        #if no port's up, skip
        if ret == True and 0 == how_many_port_in(bitmap):
            print "None"
            return 

        #if target port's out, skip
        if bitmap[port] == '1':
            print "None"
            return 
        
        ret = poll_eeprom(port)
        if ret == False:
            print "None"
            return 
        else:
            if DATA['eeprom'][port]['data'] != None:
                #print DATA['eeprom'][port]['data']
                #print "======================" 
                hex_a = DATA['eeprom'][port]['data']
                print bytearray(hex_to_int(hex_a))
    
if __name__ == '__main__':
    main()
    

