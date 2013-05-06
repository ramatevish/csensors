from subprocess import Popen, PIPE
import time
import sys
import re
from pprint import pprint
import colortrans
import colorsys

SENSOR_PATH = '/usr/bin/sensors'
POLL_TIME = 1.5
REGEX_PAT = re.compile('\:|\n  |\n')
SATURATION = .6
LIGHTNESS = 1

def runSensors ():
	return Popen([SENSOR_PATH, '-u'], stdout=PIPE, stderr=PIPE)

def parseOutput (s):
	output = []

	# split on the adapters
	adapters = s.split('\n\n')

	for adapter in adapters:
		lines = adapter.split('\n')
		length, fields, currentField = len(lines), [], None

		# step through the unparsed lines, add fields and subfields based on indentation
		for lineIndex in range(length):
			line = lines[lineIndex]

			if line.startswith('  '): # line is a subfield
				t3 = line[2:].split(': ')
				currentField.append(t3) # append the subfield to the current field

			else: # add line as a new field
				currentField = [line[:-1]] 
				fields.append(currentField)

		output.append(fields[2:])
	return output[:-2][0]

def _strip_hex (s):
    if s.startswith('0x'):
        s = s.lstrip('0x')
    return s

def getHexColor (num, denom):
	ratio = num / denom

	# Hue, Saturation, Lightness
	rgb = colorsys.hls_to_rgb(colorsys.ONE_THIRD - colorsys.ONE_THIRD * ratio, SATURATION, LIGHTNESS)

	# convert to hex values ''.join([str, str, str])
	hexVals = [_strip_hex(str(hex(int(i * 255)))) for i in rgb]
	return colortrans.rgb2short(''.join(hexVals))

def formatColors (l):
	sOut = ''
	for sensor in l:
		sensor = {'name': sensor[0],'curTemp': float(sensor[1][1]), 'critTemp': float(sensor[2][1])}
		sensor['percentage'] = (sensor['curTemp'] / sensor['critTemp']) * 100
		sensor['color']  = getHexColor(sensor['curTemp'], sensor['critTemp'])[0]
		sOut += '{}:\t\033[38;5;{:<}m{} / {:<}\t({} %)\033[0m\n'.format(sensor['name'], \
																		 sensor['color'], \
																		 sensor['curTemp'], \
																		 sensor['critTemp'], \
																		 int(sensor['percentage']))
	return sOut

def watch ():
	running_procs = [runSensors()]
	while running_procs:
		for proc in running_procs:
			ret_code = proc.poll()
			if ret_code is not None:
				proc_out = proc.stdout.read().decode("utf-8")
				print(formatColors(parseOutput(proc_out)))
				running_procs.remove(proc)
				running_procs.append(runSensors())

		else: # wait for process to complete
			time.sleep(POLL_TIME)
			continue

		if ret_code != 0: # process returned a non-zero code
			print("Error: process returned %s" % ret_code, sys.stderr)

if __name__ == '__main__':
	watch()