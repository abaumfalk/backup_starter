#!/usr/bin/env python3
import subprocess as sp
import contextlib as cl
import sys
from time import sleep
import argparse
import yaml

# example config (yaml):
# ##global actions can be referenced in all options by name
# actions:
# - name: "global action"
#   open: "test"
#   close: "test"
#
# options:
# - name: "USB Disk Toshiba"
#   actions:
#   - name: "mount"
#     open: "mountpoint -q /media/user/TOSHIBA_EXT4 || mount /media/user/TOSHIBA_EXT4"
#     close: "umount /media/user/TOSHIBA_EXT4"
#   - name: "crypt"
#     open:
#     - "encfs"
#     - "/media/user/TOSHIBA_EXT4/backup"
#     - "/home/user/backup_mnt"
#     close:
#     - "fusermount"
#     - "-u"
#     - "/home/user/backup_mnt"
#   - name: "backup"
#     open:
#     - "backintime-qt4"
#     - "--profile"
#     - "default"


def error_exit(msg):
    print("Error:", msg)
    input('Press <ENTER> to exit')
    exit(1)


def sleep_echo(s):
    for i in range(s, 0, -1):
        print(i, end=' ')
        sys.stdout.flush()
        sleep(1)

    print()


class ControlledExecution:
    def __init__(self, setup_call, cleanup_call=None):
        self._setup_call = setup_call
        self._cleanup_call = cleanup_call

    def __enter__(self):
        shell = isinstance(self._setup_call, str)
        cp = sp.run(self._setup_call, shell=shell)
        if cp.returncode != 0:
            error_exit("Executing setup call '{}' finished with returncode {} - giving up!"
                       .format(self._setup_call, cp.returncode))
        return self

    def __exit__(self, _type, _value, _traceback):
        if self._cleanup_call is not None:
            shell = isinstance(self._cleanup_call, str)
            cp = sp.run(self._cleanup_call, shell=shell)
            if cp.returncode != 0:
                print("Warning: Executing cleanup call '{}' finished with returncode {}"
                      .format(self._cleanup_call, cp.returncode))


class Runner:
    def __init__(self, _config):
        if 'options' not in _config:
            error_exit("config has no options")

        self._config = config

        if 'title' in config:
            for t in config['title']:
                print(t)

        while True:
            for key, option in enumerate(self._config['options']):
                print("{}: {}".format(key + 1, option['name']))

            line = input('Choice: ')
            try:
                if not line.isdigit():
                    raise IndexError

                index = int(line) - 1
                if index < 0:
                    raise IndexError

                self._choice = self._config['options'][index]
                return
            except IndexError:
                print('Invalid choice!')
                print()
                continue

    def run(self):
        print("Running '{}'".format(self._choice['name']))

        with cl.ExitStack() as stack:
            for action in self._choice['actions']:
                act = None
                name = action['name']
                print(name)

                if 'open' in action:
                    act = action
                else:
                    # search in global actions
                    for a in self._config['actions']:
                        if a['name'] == name:
                            act = a
                            break
                    else:
                        error_exit("action '{}' not found in global actions".format(name))

                setup = act['open']
                cleanup = act.get('close')

                resource = ControlledExecution(setup, cleanup)
                stack.enter_context(resource)

            print("Cleaning up")


parser = argparse.ArgumentParser()
parser.add_argument('-c', dest='config', action='store',
                    help='config file')

args = parser.parse_args()
if args.config is None:
    error_exit("no config file given")

config_file = args.config

with open(config_file, "r") as file:
    config = yaml.load(file)

runner = Runner(config)
runner.run()
