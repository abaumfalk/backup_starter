# -*- coding: utf-8 -*-
from subprocess import check_call, check_output
from time import sleep
import sys
import os

# options_file: array of options, exported as a json-object
#
# each option is an object with following parameters (some optional):
#
# name:        name of the backup destination, as presented in the menu
# profile:     profile for BackInTime
# mount:       command for mounting of the backup volume
# umount:      command for unmounting of the backup volume
# crypt_open:  command for opening decryption of the backup volume ($KEYFILE see below)
# crypt_close: command for closing decryption of the backup volume
#
### following parameters are used for keys located on removable media, which are auto-mounted. We identify the
### device via an id-file or directory. The actual key is located inside the id-dir or at the same level
### of the id-file
# keydir:      directory where the key will be mounted
# keydepth:    max-depth to search for the keyid file or directory
# keyid:       see above
# keyname:     name of the keyfile. This filename including the full path will replace $KEYFILE.

#example .options file
# [
#     {
#         "profile": "Hauptprofil",
#         "name": "interne Festplatte",
#         "tasks": {
# 			"mount":  {
# 				"call": [
# 					"udisksctl",
# 					"mount",
# 					"-b",
# 					"/dev/disk/by-uuid/987495C17495A314"
# 				]
# 			},
# 			"umount": {
# 				"call": [
# 					"udisksctl",
# 					"unmount",
# 					"-b",
# 					"/dev/disk/by-uuid/987495C17495A314"
# 				]
# 			}
# 		}
#     },
#     {
#         "profile": "NAS",
#         "name": "NAS",
#         "tasks": {
# 			"mount": {
# 				"call": [
# 					"mount",
# 					"/media/baumfalk/nas"
# 				]
# 			},
# 			"umount": {
# 				"call": [
# 					"umount",
# 					"/media/baumfalk/nas"
# 				]
# 			},
# 			"crypt_open": {
# 				"call": [
# 					"sudo",
# 					"veracrypt",
# 					"/media/baumfalk/nas/Arno/backup_container",
# 					"/media/baumfalk/Sicherung_NAS"
# 				]
# 			},
# 			"crypt_close": {
# 				"call": [
# 					"sudo",
# 					"veracrypt",
# 					"--dismount",
# 					"/media/baumfalk/nas/Arno/backup_container"
# 				]
# 			}
# 		}
#     }
# ]

def process_keyfile(opt_arg):
    arg = opt_arg['preprocess']
    if not 'keyid' in arg or not 'keydir' in arg or not 'keydepth' in arg or not 'keyname' in arg:
        error_exit('missing parameter for process_keyfile function')

    sys.stdout.write(u'Warte auf Schlüssel mit id ' + arg['keyid'] + '..')
    sys.stdout.flush()

    while True:
        sys.stdout.write('.')
        sys.stdout.flush()
        id = check_output(['find', arg['keydir'], '-maxdepth', arg['keydepth'], '-iname', arg['keyid']]).strip()
        if len(id):
            break

        sleep(1)

    print ' ok'

    print('id is \'{}\''.format(id))
    if os.path.isdir(id):
        keyfile = os.path.join(id, arg['keyname'])
    else:
        keyfile = os.path.join(os.path.dirname(id), arg['keyname'])

    if not os.path.isfile(keyfile):
        error_exit('keyfile \'' + keyfile + '\' nicht gefunden')

    opt_arg['keyfile'] = keyfile

    for i, x in enumerate(opt_arg['call']):
        opt_arg['call'][i] = opt_arg['call'][i].replace('$KEYFILE', keyfile)


def unmount_key(opt_arg):
    keydev = check_output('df ' + opt_arg['keyfile'] + ' | sed \'1 d\' | cut -f 1 -d \' \'', shell=True).rstrip()
    print('Trenne Schlüssel-Laufwerk')
    try_call(['umount', keydev])

    sys.stdout.write(u'Bitte Schlüssel entfernen..')
    sys.stdout.flush()
    while os.path.exists(keydev):
        sys.stdout.write('.')
        sys.stdout.flush()
        sleep(1)

    print 'ok'


#the option_template describes the backup-options file
#required: the option is required
#call: pre/post - the option provides an array for the check_call function an will be executed pre/post backup
#      NOTE: callable options will be processed in template order
#preprocess: preprocessing function for callable option
#      NOTE: the function is only triggered if preprocess is set in option; the preprocess argument will be passed
option_template = [
    {'name': 'name', 'required': True},
    {'name': 'profile', 'required': True},
    {'name': 'tasks'}
]

preprocessing_tasks = [
    {'name': 'mount', 'msg': 'Verbinde backup Laufwerk'},
    {'name': 'crypt_open', 'msg': u'Öffne Daten-Verschlüsselung',
     'preprocess': process_keyfile, 'postprocess': unmount_key},
]

postprocessing_tasks = [
    {'name': 'crypt_close', 'msg': u'Schließe Daten-Verschlüsselung'},
    {'name': 'umount', 'msg': 'Trenne backup Laufwerk'}
]

def error_exit(msg):
    print "Error:", msg
    raw_input('<ENTER> zum Beenden')
    exit(1)

def read_options():
    import json
    options_file = os.path.expanduser('~') + "/.backup-options"

    try:
        file_handle = open(options_file, "r")
        options = json.load(file_handle)
        file_handle.close()
    except IOError:
        error_exit("could not open options file " + options_file)
    except ValueError as e:
        error_exit("syntax error in json file {}: {}".format(options_file, e))

    #check for required option keys
    for template in option_template:
        if not 'name' in template:
            error_exit('option without name in option_template')
        if not 'required' in template or template['required'] == False:
            continue
        for option in options:
            if not template['name'] in option:
                error_exit('option without \'' + template['name'] + '\' key in ' + options_file)

    #check options
    for option in options:
        for key in option.keys():
            in_template = False
            for template in option_template:
                if key == template['name']:
                    in_template = True
                    break

            if not in_template:
                error_exit('option \'' + key + '\' not in template')

            if key == 'tasks':
                for option_task in option[key].keys():
                    in_tasks = False
                    for template_task in postprocessing_tasks + preprocessing_tasks:
                        if option_task == template_task['name']:
                            in_tasks = True
                            break
                    if not in_tasks:
                        error_exit('task \'' + option_task + '\' not in task list')

    return options


def try_call(call):
    try:
        if isinstance(call, list):
            check_call(call)
        else:
            check_call(call, shell=True)
    except:
        error_exit('calling {} failed'.format(call))


def sleep_echo(s):
    for i in range(s, 0, -1):
        print i,
        sys.stdout.flush()
        sleep(1)

    print


def choose_option(options):
    while True:
        for key, option in enumerate(options):
            print key + 1, ':', option['name']

        line = raw_input('Auswahl: ')
        try:
            if not line.isdigit():
                raise IndexError

            index = int(line) - 1
            if index < 0:
                raise IndexError

            option = options[index]
        except IndexError:
            print u'keine gültige Auswahl!'
            print
            continue

        return option


def call_options(template_tasks, option_tasks):
    for template_task in template_tasks:
        name = template_task['name']
        if not name in option_tasks:
            continue
        option_task = option_tasks[name]

        if 'msg' in template_task:
            print(template_task['msg'])

        if 'preprocess' in template_task and 'preprocess' in option_task:
            template_task['preprocess'](option_task)

        try_call(option_task['call'])

        if 'postprocess' in template_task and 'postprocess' in option_task:
            template_task['postprocess'](option_task)


print('******************')
print('* BACKUP-STARTER *')
print('******************')

option = choose_option(read_options())

print

if 'tasks' in option:
    call_options(preprocessing_tasks, option['tasks'])

print(
    '*****************************\n'
    '* Starte backup-Programm    *\n'
    '*****************************\n'
    '* Fenster nicht schliessen! *\n'
    '*****************************')
try_call(['backintime-qt4', '--profile', option['profile']])

if 'tasks' in option:
    call_options(postprocessing_tasks, option['tasks'])

print 'Fertig -',
sleep_echo(3)
