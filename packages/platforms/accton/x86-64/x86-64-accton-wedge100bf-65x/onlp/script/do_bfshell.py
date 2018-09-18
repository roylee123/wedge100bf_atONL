#!/usr/bin/env python

import sys
import pexpect
import getopt
import os

def usage():
    print "usage: {} [-f command_file] [-a ipv4_addr] [-p port] [-c command [-c comand] ...]".format(__file__)


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "a:p:f:c:")
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err)  # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    commands = []
    bfshell_path = '/usr/local/barefoot/bin/bfshell'
    #bfshell_path = '/opt/bfn/install/bin/bfshell'
    bfshell_cmd = [ bfshell_path ]
    for o, a in opts:
        if o == '-a':
            bfshell_cmd.extend(['-a', a])
        elif o == '-p':
            bfshell_cmd.extend(['-p', a])
        elif o == '-f':
            bfshell_cmd.extend(['-f', a])
        elif o == '-c':
            commands.append(a)
        else:
            assert False, "unhandled option"

    if commands:
        prompt_list = ['bfshell> $', 'bf-sde\.*.*> $', 'pd-switch:\d+> $', pexpect.EOF]
        child = pexpect.spawn(' '.join(bfshell_cmd))
        child.expect(prompt_list)
        for cmd in commands:
            child.sendline(cmd)
            child.expect(prompt_list)
            for line in child.before.splitlines():
                if line.strip() and line != cmd:
                    print line

    else:
        os.execv(bfshell_path, bfshell_cmd)

if __name__ == '__main__':
    main()
    

