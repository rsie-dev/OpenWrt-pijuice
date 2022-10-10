#!/usr/bin/python3

import os
import sys
import re
import argparse
import logging
import json
import datetime

from pijuice import PiJuice

class CommandBase:
    def __init__(self, pijuice):
        self._pijuice = pijuice

class BatteryCommand(CommandBase):
    def __init__(self, pijuice, current_fw_version):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = current_fw_version

    def getBattery(self, args):
        profile_name, profile_status, status_text = self._read_battery_profile_status()
        profile_data, ext_profile_data = self._read_battery_profile_data()
        temp_sense = self._read_temp_sense()
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
        self.logger.info("Temperature sense:        %s" % temp_sense)

    def setBattery(self, args):
        self.logger.info("set battery")
        self._pijuice.config.SelectBatteryProfiles(self.current_fw_version)
        batteryProfiles = self._pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
        if not args.profile in batteryProfiles:
            self.logger.error("unknown or missing profile: %s" % args.profile)
        self.logger.info("new profile: %s" % args.profile)
        self._apply_settings(None, args.profile)

    def listBattery(self, args):
        self.logger.info("available battery profiles:")
        self._pijuice.config.SelectBatteryProfiles(self.current_fw_version)
        batteryProfiles = self._pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
        for profile in batteryProfiles:
            self.logger.info(" - %s" % profile)

    def _read_battery_profile_data(self):
        config = self._pijuice.config.GetBatteryProfile()
        if config['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery data: %s" % config['error'])
        profile_data = config['data']

        if self.current_fw_version >= 0x13:
            extconfig = self._pijuice.config.GetBatteryExtProfile()
            if extconfig['error'] != 'NO_ERROR':
                raise IOError("Unable to read battery data: %s" % extconfig['error'])
            ext_profile_data = extconfig['data']
        else:
            ext_profile_data = None
        return profile_data, ext_profile_data

    def _read_battery_profile_status(self):
        profile_name = 'CUSTOM'
        status_text = ''
        status = self._pijuice.config.GetBatteryProfileStatus()
        if status['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery status: %s" % status['error'])

        profile_status = status['data']

        if profile_status['validity'] == 'VALID':
            if profile_status['origin'] == 'PREDEFINED':
                profile_name = profile_status['profile']
        else:
            status_text = 'Invalid battery profile'
            return profile_name, profile_status, status_text

        self._pijuice.config.SelectBatteryProfiles(self.current_fw_version)
        batteryProfiles = self._pijuice.config.batteryProfiles# + ['CUSTOM', 'DEFAULT']
        if profile_status['source'] == 'DIP_SWITCH' and profile_status['origin'] == 'PREDEFINED' and batteryProfiles.index(profile_name) == 1:
            status_text = 'Default profile'
        else:
            status_text = 'Custom profile by: ' if profile_status['origin'] == 'CUSTOM' else 'Profile selected by: '
            status_text += profile_status['source']

        return profile_name, profile_status, status_text

    def _read_temp_sense(self):
        temp_sense_config = self._pijuice.config.GetBatteryTempSenseConfig()
        if temp_sense_config['error'] != 'NO_ERROR':
            raise IOError("Unable to read battery temp sense: %s" % temp_sense_config['error'])
        return temp_sense_config['data']

    def _apply_settings(self, temp_sense, profile_name):
        if temp_sense:
            status = self._pijuice.config.SetBatteryTempSenseConfig(temp_sense)
            if status['error'] != 'NO_ERROR':
                raise IOError("Unable to set battery temp sense: %s" % status['error'])

        #status = pijuice.config.SetRsocEstimationConfig(self.RSOC_ESTIMATION_OPTIONS[self.rsoc_estimation_profile_idx])
        #if status['error'] != 'NO_ERROR':
        #    confirmation_dialog('Failed to apply rsoc estimation options. Error: {}'.format(
        #        status['error']), next=main_menu, single_option=True)

        if profile_name:
            status = self._pijuice.config.SetBatteryProfile(profile_name)
            if status['error'] != 'NO_ERROR':
                raise IOError("Unable to set battery profile: %s" % status['error'])
        self.logger.info("settings successfully updated")

class FirmwareCommand(CommandBase):
    PiJuiceFirmwarePath = '/usr/share/pijuice/data/firmware/'

    def __init__(self, pijuice, current_fw_version):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.current_fw_version = current_fw_version

    def getFirmware(self, args):
        current_version_txt = self.version_to_str(self.current_fw_version)
        self.logger.info("current firmware version: %s" % current_version_txt)

    def listFirmware(self, args):
        self.logger.info("available firmware versions:")
        binDir = self.PiJuiceFirmwarePath
        files = [f for f in os.listdir(binDir) if os.path.isfile(os.path.join(binDir, f))]
        files = sorted(files)
        regex = re.compile(r"PiJuice-V(\d+)\.(\d+)_(\d+_\d+_\d+).elf.binary")
        for fileName in files:
            match = regex.match(fileName)
            if match:
                major = int(match.group(1))
                minor = int(match.group(2))
                version = (major << 4) + minor
                version_txt = self.version_to_str(version)
                self.logger.info(" - %s (%s)" % (version_txt, fileName))

    def version_to_str(self, number):
        # Convert int version to str {major}.{minor}
        return "{}.{}".format(number >> 4, number & 15)

class RealTimeClockCommand(CommandBase):
    def __init__(self, pijuice):
        super().__init__(pijuice)
        self.logger = logging.getLogger(self.__class__.__name__)

    def getRTC(self, args):
        st = datetime.datetime.utcnow()
        system_time = self._formateDateTime(st)
        device_time, status = self._get_device_time()
        self.logger.info("system UTC Time: " + system_time)
        self.logger.info("device UTC Time: " + device_time)
        self.logger.info("RTC status:      " + status)

    def setRTC(self, args):
        st = datetime.datetime.utcnow()
        self._set_device_time(st)

    def _get_device_time(self):
        device_time = ''
        t = self._pijuice.rtcAlarm.GetTime()
        if t['error'] != 'NO_ERROR':
            raise IOError("Unable to get device time: %s" % t['error'])
        t = t['data']
        dt = datetime.datetime(t['year'], t['month'], t['day'], t['hour'], t['minute'], t['second'])
        device_time = self._formateDateTime(dt)

        s = self._pijuice.rtcAlarm.GetControlStatus()
        if s['error'] != 'NO_ERROR':
            raise IOError("Unable to get device control status: %s" % s['error'])
        status = ""
        if s['data']['alarm_flag']:
            status = 'Last: {}:{}:{}'.format(str(t['hour']).rjust(2, '0'),
                                                  str(t['minute']).rjust(2, '0'),
                                                  str(t['second']).rjust(2, '0'))
            #pijuice.rtcAlarm.ClearAlarmFlag()
        return device_time, status

    def _set_device_time(self, st):
        system_time = self._formateDateTime(st)
        self.logger.info("set device UTC Time to: " + system_time)
        s = self._pijuice.rtcAlarm.SetTime({
            'second': st.second,
            'minute': st.minute,
            'hour': st.hour,
            'weekday': st.weekday() + 1,
            'day': st.day,
            'month': st.month,
            'year': st.year,
            'subsecond': st.microsecond // 1000000
        })
        if s['error'] != 'NO_ERROR':
            raise IOError("Unable to set device RTC time: %s" % s['error'])

    def _formateDateTime(self, dt):
        dt_fmt = "%a %Y-%m-%d %H:%M:%S"
        timeStr = dt.strftime(dt_fmt)
        return timeStr


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
        batteryCommand = BatteryCommand(pijuice, self.current_fw_version)
        if args.get:
            batteryCommand.getBattery(args)
        elif args.set:
            batteryCommand.setBattery(args)
        elif args.list:
            batteryCommand.listBattery(args)

    def service(self, args, pijuice):
        self.logger.debug(args.subparser_name)

    def rtc(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        command = RealTimeClockCommand(pijuice)
        if args.get:
            command.getRTC(args)
        elif args.set:
            command.setRTC(args)

    def firmware(self, args, pijuice):
        self.logger.debug(args.subparser_name)
        firmwareCommand = FirmwareCommand(pijuice, self.current_fw_version)
        if args.get:
            firmwareCommand.getFirmware(args)
        elif args.list:
            firmwareCommand.listFirmware(args)

    def main(self):
        parser = argparse.ArgumentParser(description="pijuice control utility")
        parser.add_argument('-v', '--verbose', action="store_true", help="verbose output")
        subparsers = parser.add_subparsers(dest='subparser_name', title='commands')

        parser_bat = subparsers.add_parser('battery', help='battery configuration')
        parser_bat.set_defaults(func=self.battery)
        group_bat = parser_bat.add_mutually_exclusive_group(required=True)
        group_bat.add_argument('--get', action="store_true", help="get current battery config")
        group_bat.add_argument('--set', action="store_true", help="set battery profile")
        group_bat.add_argument('--list', action="store_true", help="list available battery profiles")
        parser_bat.add_argument('--profile', help="new  battery profile")

        parser_service = subparsers.add_parser('service', help='pijuice service configuration')
        parser_service.set_defaults(func=self.service)

        parser_rtc = subparsers.add_parser('rtc', help='real time clock configuration')
        parser_rtc.set_defaults(func=self.rtc)
        group_rtc = parser_rtc.add_mutually_exclusive_group(required=True)
        group_rtc.add_argument('--get', action="store_true", help="get current RTC")
        group_rtc.add_argument('--set', action="store_true", help="set device RTC to system time")

        parser_firmware = subparsers.add_parser('firmware', help='firmware configuration')
        parser_firmware.set_defaults(func=self.firmware)
        group_firmware = parser_firmware.add_mutually_exclusive_group(required=True)
        group_firmware.add_argument('--get', action="store_true", help="get current firmware")
        group_firmware.add_argument('--list', action="store_true", help="list available firmware files")

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
