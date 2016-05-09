# Run the Valgrind-based C/C++ backend for OPT and produce JSON to
# stdout for piping to a web app, properly handling errors and stuff

# Created: 2016-05-09

import json
import os
from subprocess import Popen, PIPE
import re
import sys

DN = os.path.dirname(sys.argv[0])
USER_PROGRAM = sys.argv[1] # string containing the program to be run
LANG = sys.argv[2] # 'c' for C or 'cpp' for C++

if LANG == 'c':
    CC = 'gcc'
    FN = 'usercode.c'
else:
    CC = 'g++'
    FN = 'usercode.cpp'

F_PATH = os.path.join(DN, FN)
VGTRACE_PATH = os.path.join(DN, 'usercode.vgtrace')
EXE_PATH = os.path.join(DN, 'usercode.exe')

# get rid of stray files so that we don't accidentally use a stray one
for f in (F_PATH, VGTRACE_PATH, EXE_PATH):
    if os.path.exists(f):
        os.remove(f)

# write USER_PROGRAM into F_PATH
with open(F_PATH, 'w') as f:
    f.write(USER_PROGRAM)

# compile it!
p = Popen([CC, '-ggdb', '-O0', '-fno-omit-frame-pointer', '-o', EXE_PATH, F_PATH],
          stdout=PIPE, stderr=PIPE)
(gcc_stdout, gcc_stderr) = p.communicate()
gcc_retcode = p.returncode

if gcc_retcode == 0:
    # run it with Valgrind
    VALGRIND_EXE = os.path.join(DN, 'valgrind-3.11.0/inst/bin/valgrind')
    # tricky! --source-filename takes a basename only, not a full pathname:
    valgrind_p = Popen([VALGRIND_EXE,
                        '--tool=memcheck',
                        '--source-filename=' + FN,
                        '--trace-filename=' + VGTRACE_PATH,
                        EXE_PATH],
                       stdout=PIPE, stderr=PIPE)
    (valgrind_stdout, valgrind_stderr) = valgrind_p.communicate()
    valgrind_retcode = valgrind_p.returncode

    #print '=== Valgrind stdout ==='
    #print valgrind_stdout
    #print '=== Valgrind stderr ==='
    #print valgrind_stderr

    # TODO: gracefully handle Valgrind-produced errors

    # convert vgtrace into an OPT trace

    # TODO: integrate call into THIS SCRIPT since it's simply Python
    # code; no need to call it as an external script
    POSTPROCESS_EXE = os.path.join(DN, 'vg_to_opt_trace.py')
    postprocess_p = Popen(['python', POSTPROCESS_EXE,
                           '--jsondump', F_PATH],
                          stdout=PIPE, stderr=PIPE)
    (postprocess_stdout, postprocess_stderr) = postprocess_p.communicate()
    postprocess_retcode = postprocess_p.returncode
    print postprocess_stdout
else:
    #print '==='
    #print gcc_stderr
    #print '==='
    # compiler error. parse and report gracefully!

    exception_msg = 'unknown compiler error'
    lineno = None
    column = None

    # just report the FIRST line where you can detect a line and column
    # number of the error.
    for line in gcc_stderr.splitlines():
        m = re.search('usercode.c:(\d+):(\d+):(.*$)', line)
        if m:
            lineno = int(m.group(1))
            column = int(m.group(2))
            exception_msg = m.group(3).strip()
            break

    ret = {'code': USER_PROGRAM,
           'trace': [{'event': 'uncaught_exception',
                    'exception_msg': exception_msg,
                    'line': lineno}]}
    print json.dumps(ret)

