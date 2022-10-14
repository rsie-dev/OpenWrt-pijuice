#!/usr/bin/python3 -OO
import os
import sys
import logging
import subprocess
import argparse

from pijuice import PiJuice

HALT_FILE = '/tmp/pijuice_poweroff.flag'

def systemHalt(pijuice):
    pijuice.status.SetLedBlink('D2', 3, [150, 0, 0], 200, [0, 100, 0], 200)
    # Setting halt flag 
    with open(HALT_FILE, 'w') as f:
        pass
    subprocess.call(["sudo", "halt"])

def triggerPowerOff(pijuice, delay):
    ret = pijuice.power.SetSystemPowerSwitch(0)
    if ret['error'] != 'NO_ERROR':
        raise IOError("Unable to set system power switch %s" % ret['error'])
    ret = pijuice.power.SetPowerOff(delay)
    if ret['error'] != 'NO_ERROR':
        raise IOError("Unable to set poweroff %s" % ret['error'])

def main():
    parser = argparse.ArgumentParser(description="halts and powers off")
    parser.add_argument('-v', '--verbose', action="store_true", help="verbose output")
    parser.add_argument('-d', '--delay', type=int, choices=range(10, 61), default=20, metavar="{10..60}", help="power off delay")
    args = parser.parse_args()

    if args.verbose:
        consoleLevel = logging.DEBUG
    else:
        consoleLevel = logging.INFO
    logging.basicConfig(level=consoleLevel, format="%(asctime)s %(levelname)-6s: %(message)s")

    result = 0
    try:
        if os.path.exists(HALT_FILE):
            logging.warn("halt already triggered -> ignore")
            return 0

        delay = args.delay
        logging.info("halt and completely power of after %ss" % delay)
        pijuice = PiJuice(1, 0x14)
        triggerPowerOff(pijuice, delay)
    except: # pylint: disable=bare-except
        logging.exception("exception:")
        result = 1

    try:
        systemHalt(pijuice)
    except: # pylint: disable=bare-except
        logging.exception("exception:")
        result = 1

    return result

if __name__ == '__main__':
    sys.exit(main())
