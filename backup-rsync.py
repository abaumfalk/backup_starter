#!/usr/bin/env python3
import subprocess as sp
import argparse
import datetime
import os

TEE = "/usr/bin/tee"
BASH = "/bin/bash"

parser = argparse.ArgumentParser()
parser.add_argument('-s', dest='src', nargs='+', action='store', required=True,
                    help='source directories')
parser.add_argument('-d', dest='dst', action='store', required=True,
                    help='destination directory')
parser.add_argument('-e', dest='excl', action='store',
                    help='exclude file')

args = parser.parse_args()

dst = os.path.abspath(args.dst)
src = [os.path.abspath(s) for s in args.src]
excl = None
if args.excl is not None:
    excl = os.path.abspath(args.excl)

now = datetime.datetime.now()
target = os.path.join(dst, "{}-{}".format(now.strftime("%Y%m%d-%H%M%S"), os.getpid()))

os.makedirs(target)
for s in src:
    t_rel = os.path.relpath(s, os.path.sep)
    t = os.path.join(target, t_rel)
    os.makedirs(t)

    cmd = "/usr/bin/rsync -Aav"
    last = os.path.join(dst, "last")
    if os.path.islink(last):
        cmd += " --link-dest={}/".format(os.path.join(last, t_rel))
    if excl is not None:
        cmd += " --exclude-from={}".format(excl)
    cmd += " {}/".format(s)
    cmd += " {}".format(t)

    outfile = "{}/rsync.out".format(target)
    errfile = "{}/rsync.err".format(target)

    with open(outfile, "a") as out, open(errfile, "a") as err:
        out.write('stdout of "{}"\n======\n'.format(cmd))
        err.write('stderr of "{}"\n======\n'.format(cmd))

    print("Executing '{}'".format(cmd))
    cmd = "({}) 2> >({} -a {}) > >({} -a {})".format(cmd, TEE, errfile, TEE, outfile)
    cmd = "{} -c \"{}\"".format(BASH, cmd)

    # shell=True seems necessary, even though the command is 'bash -c "{}"' ?!
    fp = sp.run(cmd, shell=True)

    if fp.returncode != 0:
        print("Command returned error {}".format(fp.returncode))
        fp.check_returncode()


link_source = os.path.relpath(target, dst)
link_name = os.path.join(dst, "last")
print("symlink {} {}".format(link_source, link_name))
if os.path.islink(link_name):
    os.unlink(link_name)
os.symlink(link_source, link_name)

print("Finished successfully")
