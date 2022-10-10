#!/usr/bin/python3

import sys
import argparse
import logging

#from pijuice import PiJuice

class Control:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def battery(self, args, pijuice):
        self.logger.info(args.subparser_name)

    def service(self, args, pijuice):
        self.logger.info(args.subparser_name)

    def rtc(self, args, pijuice):
        self.logger.info(args.subparser_name)

    def main(self):
        parser = argparse.ArgumentParser(description="pijuice control utility")
        parser.add_argument('-v', '--verbose', action="store_true", help="verbose output")
        subparsers = parser.add_subparsers(dest='subparser_name', title='commands')

        parser_bat = subparsers.add_parser('battery', help='battery configuration')
        parser_bat.set_defaults(func=self.battery)

        parser_service = subparsers.add_parser('service', help='pijuice service configuration')
        parser_service.set_defaults(func=self.service)

        parser_rtc = subparsers.add_parser('rtc', help='real time clock configuration')
        parser_rtc.set_defaults(func=self.rtc)

        args = parser.parse_args()
        if not 'func' in args:
            parser.error(message="no command")

        if args.verbose:
            consoleLevel = logging.DEBUG
        else:
            consoleLevel = logging.INFO
        logging.basicConfig(level=consoleLevel, format="%(levelname)-6s:%(message)s")

        try:
            self.logger.debug("### started ###")
            #pijuice = PiJuice(1, 0x14)
            pijuice = None
            args.func(args, pijuice)
        except KeyboardInterrupt:
            self.logger.warn("aborted")
            return 2
        except: # pylint: disable=bare-except
            self.logger.exception("exception:")
            return 1
        finally:
            self.logger.debug("### finished ###")

if __name__ == '__main__':
    c = Control()
    sys.exit(c.main())
