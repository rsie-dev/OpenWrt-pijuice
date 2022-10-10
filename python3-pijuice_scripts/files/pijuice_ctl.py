#!/usr/bin/python3

import os
import sys
import argparse
import logging
import json

from pijuice import PiJuice

class Control:
    PID_FILE = '/tmp/pijuice_sys.pid'
    PiJuiceConfigDataPath = '/var/lib/pijuice/pijuice_config.JSON'

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = None

    def loadPiJuiceConfig(self):
        try:
            with open(self.PiJuiceConfigDataPath, 'r') as outputConfig:
                pijuiceConfigData = json.load(outputConfig)
        except:
            pijuiceConfigData = {}
        return pijuiceConfigData

    def savePiJuiceConfig(self, pijuiceConfigData):
        with open(self.PiJuiceConfigDataPath, 'w+') as outputConfig:
            json.dump(pijuiceConfigData, outputConfig, indent=2)
        ret = self.notify_service()
        if ret != 0:
            self.logger.error("failed to communicate with PiJuice service")
        else:
            self.logger.info("settings saved")

    def notify_service(self):
        ret = -1
        try:
            pid = int(open(self.PID_FILE, 'r').read())
            ret = os.system("kill -SIGHUP " + str(pid) + " > /dev/null 2>&1")
        except:
            pass
        return ret

    def battery(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        if args.get:
            profile_name, profile_status, status_text = self._read_battery_profile_status(pijuice)
            profile_data, ext_profile_data = self._read_battery_profile_data(pijuice)
            self.logger.info("battery status:           " + status_text)
            self.logger.info("profile:                  " + profile_name)
            if profile_data == 'INVALID':
                self.logger.info("profile data:                  " + "invalid")
            else:
                self.logger.info("Capacity [mAh]:           %s" % profile_data['capacity'])
                self.logger.info("Charge current [mA]:      %s" % profile_data['chargeCurrent'])
                self.logger.info("Termination current [mA]: %s" % profile_data['terminationCurrent'])
                self.logger.info("Regulation voltage [mV]:  %s" % profile_data['regulationVoltage'])
                self.logger.info("Cutoff voltage [mV]:      %s" % profile_data['cutoffVoltage'])
                self.logger.info("Cold temperature [C]:     %s" % profile_data['tempCold'])
                self.logger.info("Cool temperature [C]:     %s" % profile_data['tempCool'])
                self.logger.info("Warm temperature [C]:     %s" % profile_data['tempWarm'])
                self.logger.info("Hot temperature [C]:      %s" % profile_data['tempHot'])
                self.logger.info("NTC B constant [1k]:      %s" % profile_data['ntcB'])
                self.logger.info("NTC resistance [ohm]:     %s" % profile_data['ntcResistance'])
                if self.current_fw_version >= 0x13:
                    self.logger.info("Chemistry:                %s" % ext_profile_data['chemistry'])

        elif args.set:
            self.logger.info("set battery")

        elif args.list:
            self.logger.info("available battery profiles:")
            pijuice.config.SelectBatteryProfiles(self.current_fw_version)
            batteryProfiles = pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
            for profile in batteryProfiles:
                self.logger.info(" - %s" % profile)

    def _read_battery_profile_data(self, pijuice):
        config = pijuice.config.GetBatteryProfile()
        if config['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery data: %s" % config['error'])
        profile_data = config['data']

        if self.current_fw_version >= 0x13:
            extconfig = pijuice.config.GetBatteryExtProfile()
            if extconfig['error'] != 'NO_ERROR':
                raise IOError("Unable to read battery data: %s" % extconfig['error'])
            ext_profile_data = extconfig['data']
        else:
            ext_profile_data = None
        return profile_data, ext_profile_data

    def _read_battery_profile_status(self, pijuice):
        profile_name = 'CUSTOM'
        status_text = ''
        status = pijuice.config.GetBatteryProfileStatus()
        if status['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery status: %s" % status['error'])

        profile_status = status['data']

        if profile_status['validity'] == 'VALID':
            if profile_status['origin'] == 'PREDEFINED':
                profile_name = profile_status['profile']
        else:
            status_text = 'Invalid battery profile'
            return profile_name, profile_status, status_text

        pijuice.config.SelectBatteryProfiles(self.current_fw_version)
        batteryProfiles = pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
        if profile_status['source'] == 'DIP_SWITCH' and profile_status['origin'] == 'PREDEFINED' and batteryProfiles.index(profile_name) == 1:
            status_text = 'Default profile'
        else:
            status_text = 'Custom profile by: ' if profile_status['origin'] == 'CUSTOM' else 'Profile selected by: '
            status_text += profile_status['source']

        return profile_name, profile_status, status_text


    def service(self, args, pijuice):
        self.logger.debug(args.subparser_name)

    def rtc(self, args, pijuice):
        self.logger.debug(args.subparser_name)

    def firmware(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        if args.get:
            current_version_txt = self.version_to_str(self.current_fw_version)
            self.logger.info("current firmware version: %s" % current_version_txt)

    def version_to_str(self, number):
        # Convert int version to str {major}.{minor}
        return "{}.{}".format(number >> 4, number & 15)

    def main(self):
        parser = argparse.ArgumentParser(description="pijuice control utility")
        parser.add_argument('-v', '--verbose', action="store_true", help="verbose output")
        subparsers = parser.add_subparsers(dest='subparser_name', title='commands')

        parser_bat = subparsers.add_parser('battery', help='battery configuration')
        parser_bat.set_defaults(func=self.battery)
        group_bat = parser_bat.add_mutually_exclusive_group(required=True)
        group_bat.add_argument('--get', action="store_true", help="get current battery config")
        group_bat.add_argument('--set', action="store_true", help="set battery config")
        group_bat.add_argument('--list', action="store_true", help="list available battery profiles")

        parser_service = subparsers.add_parser('service', help='pijuice service configuration')
        parser_service.set_defaults(func=self.service)

        parser_rtc = subparsers.add_parser('rtc', help='real time clock configuration')
        parser_rtc.set_defaults(func=self.rtc)

        parser_firmware = subparsers.add_parser('firmware', help='firmware configuration')
        parser_firmware.set_defaults(func=self.firmware)
        group_firmware = parser_firmware.add_mutually_exclusive_group(required=True)
        group_firmware.add_argument('--get', action="store_true", help="get current firmware")

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
            pijuice = PiJuice(1, 0x14)
            #pijuice = None
            self.current_fw_version = self.get_current_fw_version(pijuice)
            args.func(args, pijuice)
        except KeyboardInterrupt:
            self.logger.warn("aborted")
            return 2
        except: # pylint: disable=bare-except
            self.logger.exception("exception:")
            return 1
        finally:
            self.logger.debug("### finished ###")

    def get_current_fw_version(self, pijuice):
        # Returns current version as int (first 4 bits - minor, second 4 bits - major)
        status = pijuice.config.GetFirmwareVersion()
        if status['error'] == 'NO_ERROR':
            major, minor = status['data']['version'].split('.')
        else:
            major = minor = 0
        current_version = (int(major) << 4) + int(minor)
        return current_version

if __name__ == '__main__':
    c = Control()
    sys.exit(c.main())
