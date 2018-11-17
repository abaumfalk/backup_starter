#!/usr/bin/python3
from subprocess import check_call, check_output
from contextlib import ExitStack
import sys
from time import sleep
import argparse
import yaml
import os

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


def call(call, capture_output=False):
    if capture_output:
        cfn = check_output
    else:
        cfn = check_call

    if isinstance(call, list):
        return cfn(call)
    else:
        return cfn(call, shell=True)


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
        self._setup_result = call(self._setup_call)
        return self

    def __exit__(self, _type, _value, _traceback):
        if self._cleanup_call is not None:
            if isinstance(self._cleanup_call, str):
                call(self._cleanup_call.format(self._setup_result))
            else:
                call(self._cleanup_call)


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

        with ExitStack() as stack:
            for action in self._choice['actions']:
                name = action['name']
                print(name)

                if 'open' in action:
                    act = action
                else:
                    #search in global actions
                    for a in self._config['actions']:
                        if a['name'] == name:
                            act = a
                            break

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
