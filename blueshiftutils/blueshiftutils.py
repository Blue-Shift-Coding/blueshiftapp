import re, time

#----------------------------------------------------------------------------#
# Miscellaneous helpful utility functions
#----------------------------------------------------------------------------#

def rgx_matches(rgx, string):
    matches = re.search(rgx, string)
    if matches is None:
        return False
    return matches

def uniqid(prefix = ''):
    current_time = time.time() * 1000
    output = prefix + hex(int(current_time))[2:10] + hex(int(current_time*1000000) % 0x100000)[2:7]
    return output
