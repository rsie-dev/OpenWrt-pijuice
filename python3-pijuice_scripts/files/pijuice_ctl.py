#!/usr/bin/python3 -OO
import sys
import argparse
import logging

#from pijuice import PiJuice

class Control:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def main(self):
        parser = argparse.ArgumentParser(description="pijuice control utility")
        parser.add_argument('-v', '--verbose', action="store_true", help="verbose output")
        #pijuice = PiJuice(1, 0x14)

        args = parser.parse_args()

        if args.verbose:
            consoleLevel = logging.DEBUG
        else:
            consoleLevel = logging.INFO
        logging.basicConfig(level=consoleLevel, format="%(levelname)-6s:%(message)s")

        self.logger.debug("### started ###")

if __name__ == '__main__':
    c = Control()
    sys.exit(c.main())
