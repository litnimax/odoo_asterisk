import commands
import os
import shutil
import tempfile
from transliterate import translit

ASTERISK_SPOOL_DIR = '/tmp/spool'
ASTERISK_EXECUTABLE = '/bin/echo'
CALLOUT_TEMPLATE = """Channel: Local/%(number)s@confman-dialout
Context: confman-bridge
Extension: %(confnum)s
Priority: 1
MaxRetries: 0
RetryTime: 15
WaitTime: 300
Set: participant_name=%(name)s
Set: participant_number=%(number)s
Set: conf_number=%(confnum)s
"""


def _cli_command(cmd):
    status, output = commands.getstatusoutput(
        "%s -rx '%s'" % (ASTERISK_EXECUTABLE, cmd))
    if status != 0:
        raise Exception(output)
    return output



def confbridge_list():
    rooms = []
    output = _cli_command('confbridge list')
    for line in output.split('\n')[2:]: # Skip 2 line headers
        line = line.split()
        if line[0].isdigit():
            rooms.append(line)
    return rooms

def confbridge_list2():
    return open('/tmp/confbridge_list2').readlines()


def confbridge_list_participants(confno):
    output = _cli_command('confbridge list %s' % confno)
    if 'No conference' in output:
        return []
    participants = []
    lines = output.split('\n')
    header = lines[0].split()
    for line in lines[2:]:
        line = line.split()
        channel = line[0]
        flags = ''
        callerid = ''
        if len(header) == 7 and header[6] == 'CallerID':
            # ['Channel', 'User', 'Profile', 'Bridge', 'Profile', 'Menu', 'CallerID']
            if len(line) == 3:
                # User Profile and Bridge Profile are empty as it should be.
                callerid = line[2]
        elif len(header) == 8 and header[7] == 'Muted':
            # ['Channel', 'User', 'Profile', 'Bridge', 'Profile', 'Menu', 'CallerID', 'Muted']
            if len(line) == 4:
                # User Profile and Bridge Profile are empty as it should be.
                callerid = line[2]
                flags = 'm' if line[3] == 'Yes' else ''
        elif len(header) == 8 and header[1] == 'Flags':
            # ['Channel', 'Flags', User', 'Profile', 'Bridge', 'Profile', 'Menu', 'CallerID']
            if len(line) == 3:
                # No flags no default profiles
                callerid = line[2]
            elif len(line) == 4:
                # Flags are set default profiles not set
                flags = line[1]
                callerid = line[3]
            elif len(line) == 5:
                # Flags are not set and default profiles are set
                callerid = line[4]
            elif len(line) == 6:
                # Flags are set and default profiles also set
                flags = line[1]
                callerid = line[5]

        participants.append({
                'channel': channel,
                'flags': flags,
                'callerid': callerid,
                }
        )
    return participants


def originate(confnum, number, name='', bridge_options=[], user_options=[]):
    tempname = tempfile.mktemp()
    f = open(tempname, mode='w')
    f.write(CALLOUT_TEMPLATE % {'number': number,
                                              'name': translit(name, 'ru',
                                                               reversed=True),
                                              'confnum': confnum})
    f.write('\n')
    # Now iterate over profile options
    for option in user_options:
        o, v = option.split('=')
        f.write('Set: CONFBRIDGE(user,%s)=%s\n' % (o, v))
    for option in bridge_options:
        o, v = option.split('=')
        f.write('Set: CONFBRIDGE(bridge,%s)=%s\n' % (o, v))

    f.flush()
    f.close()
    # Move it to Asterisk outgoing calls queue.
    try:
        shutil.move(tempname, os.path.join(
            ASTERISK_SPOOL_DIR,
                    '%s.%s' % (confnum, number)))
        raise OSError
    except OSError:
        # This happends that Asterisk immediately deleted call file
        pass


def confbridge_get(confno):
    output = _cli_command('confbridge list')
    for line in output.split('\n')[2:]: # Skip 2 line headers
        line = line.split()
        if line[0].isdigit() and line[0] == confno:
            return {
                'name': line[0],
                'users': int(line[1]),
                'marked': False if line[2] == '0' else True,
                'locked': False if line[3] == 'unlocked' else True
            }
    # If no conference is running return empty dict
    return {
        'name': confno,
        'users': 0,
        'marked': False,
        'locked': False
    }


def confbridge_get_user_count(confno):
    return confbridge_get(confno)['users']


def confbridge_is_locked(confno):
    return confbridge_get(confno)['locked']


def confbridge_kick(confno, channel):
    return _cli_command('confbridge kick %s %s' % (confno, channel))


def confbridge_kick_all(confno):
    return _cli_command('confbridge kick %s all' % confno)


def confbridge_mute(confno, channel):
    return _cli_command('confbridge mute %s %s' % (confno, channel))


def confbridge_unmute(confno, channel):
    return _cli_command('confbridge unmute %s %s' % (confno, channel))


def confbridge_lock(confno):
    return _cli_command('confbridge lock %s' % confno)


def confbridge_unlock(confno):
    return _cli_command('confbridge unlock %s' % confno)


def confbridge_record_start(confno):
    return _cli_command('confbridge record start %s' % confno)


def confbridge_record_stop(confno):
    return _cli_command('confbridge record stop %s' % confno)
