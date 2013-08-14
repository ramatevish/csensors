#!/usr/bin/python
from subprocess import Popen, PIPE
import time
import sys
import re
from pprint import pprint
import colortrans
import colorsys
import curses
import os
from collections import namedtuple, OrderedDict


SENSOR_PATH = '/usr/bin/sensors'
POLL_TIME = 1.5
SATURATION = .6
LIGHTNESS = 1


SensorReading = namedtuple('SensorReading', ['name', 'numerator', 'denominator', 'unit'])
Adapter = namedtuple('Adapter', ['name', 'type', 'sensors'])


class Cursor(object):

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __call__(self, arg):
        return (self.y, self.x, arg)

    def cr(self):
        self.y += 1
        return self

    def t(self):
        self.x += 4
        return self

    def n(self):
        self.x = 1
        self.y += 1


def runSensors():
    return Popen([SENSOR_PATH], stdout=PIPE, stderr=PIPE)


def parseParens(string):
    params = string.strip().lstrip('(').rstrip(')').strip().split(',')
    def parseAndUpdate(d, string):
        key, val = string.split(' = ')
        d.update({key: parseTemp(val)[0]})
        return d
    paramDict = reduce(parseAndUpdate, params, dict())
    return paramDict


def parseTemp(string):
    value, unit = (1 if string[0:1] == '+' else -1) * float(string[1:-3]), string[-1:]
    return value, unit


def parseOutput(string):
    output = []

    # split on the adapters
    adapters = string.split('\n\n')
    adapters.remove('')  # remove trailing empty line

    for adapter in adapters:
        lines = adapter.split('\n')
        adapterName, adapterType, lines = lines[0], lines[1], lines[2:]
        
        sensors = []
        for index, line in enumerate(lines):
            sensorName, line = line.split(':', 1)
            sensorTemp, line = line.strip().split(' ', 1)
            numerator, unit = parseTemp(sensorTemp)

            # parse parameters in parenthesis
            params = parseParens(line)
            if 'crit' in params:
                denominator = params['crit']
            elif 'high' in params:
                denominator = params['high']
            else:
                denominator = 128.0
            sensor = SensorReading(sensorName,
                                   numerator,
                                   denominator,
                                   unit)
            sensors.append(sensor)
        output.append(Adapter(adapterName, adapterType, sensors))
    return output


def getHexColor(num, denom):
    ratio = float(num) / denom
    rgb = colorsys.hls_to_rgb(colorsys.ONE_THIRD - colorsys.ONE_THIRD * ratio, SATURATION, LIGHTNESS)
    def strip_hex(s):
        if s.startswith('0x'):
            s = s.lstrip('0x')
        return s
    hexVals = [strip_hex(str(hex(int(i * 255)))) for i in rgb]
    return colortrans.rgb2short(''.join(hexVals))


def sensorToDict(sensor):
    sensorDict = sensor._asdict()
    sensorDict.update({'color': getHexColor(sensor.numerator,
                                            sensor.denominator)[0],
                       'percentage': (sensor.numerator / sensor.denominator) * 100})
    return sensorDict


def getTerminalSize():
    # returns (rows, cols)
    return map(int, os.popen('stty size', 'r').read().split())


def getStringBounds(s):
    splitString = s.split('\n')
    return len(splitString), max(map(len,splitString)) if len(splitString) > 0 else 0
    

def drawScreen(stdscr, adapterList):
    # todo: fix colors and crash on terminal size
    stdscr.clear()
    stdscr.border()
    tRows, tCols = getTerminalSize()
    cursor = Cursor(1, 1)
    for adapterIndex, adapter in enumerate(adapterList):
        stdscr.addstr(*cursor(adapter.name))
        stdscr.addstr(*cursor.cr()(adapter.type))
        cursor.t()
        for sensorIndex, sensor in enumerate(adapter.sensors):
            stdscr.addstr(*cursor.cr()(str(sensor)))
        cursor.n()
    stdscr.refresh()


def watch(stdscr):
    running_procs = [runSensors()]
    while running_procs:
        for proc in running_procs:
            ret_code = proc.poll()
            if ret_code is not None:
                proc_out = proc.stdout.read().decode("utf-8")
                drawScreen(stdscr, parseOutput(proc_out))
                running_procs.remove(proc)
                running_procs.append(runSensors())

        else: # wait for process to complete
            time.sleep(POLL_TIME)
            continue

        if ret_code is not 0: # process returned a non-zero code
            print("Error: process returned %s" % ret_code, sys.stderr)

if __name__ == '__main__':
    curses.wrapper(watch)
