#!/usr/bin/python3 -OO
import os
import sys
import logging
import subprocess

from pijuice import PiJuice

HALT_FILE = '/tmp/pijuice_poweroff.flag'

def systemHalt(pijuice):
    pijuice.status.SetLedBlink('D2', 3, [150, 0, 0], 200, [0, 100, 0], 200)
    # Setting halt flag 
    with open(HALT_FILE, 'w') as f:
        pass
    subprocess.call(["sudo", "halt"])

def triggerPowerOff(pijuice):
    ret = pijuice.power.SetSystemPowerSwitch(0)
    if ret['error'] != 'NO_ERROR':
        raise IOError("Unable to set system power switch %s" % ret['error'])
    ret = pijuice.power.SetPowerOff(20)
    if ret['error'] != 'NO_ERROR':
        raise IOError("Unable to set poweroff %s" % ret['error'])

def main():
    consoleLevel = logging.INFO
    logging.basicConfig(level=consoleLevel, format="%(asctime)s %(levelname)-6s: %(message)s")

    try:
        if os.path.exists(HALT_FILE):
            logging.warn("halt already triggered -> ignore")
            return 0

        logging.info("halt and completely power of")
        pijuice = PiJuice(1, 0x14)
        triggerPowerOff(pijuice)
        systemHalt(pijuice)
        return 0
    except: # pylint: disable=bare-except
        logging.exception("exception:")
        return 1


if __name__ == '__main__':
    main()
    sys.exit(main())
