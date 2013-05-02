from subprocess import Popen, PIPE
import time
import sys
import re
from pprint import pprint
import colortrans
import colorsys

POLL_TIME = 2
REGEX_PAT = re.compile('\:|\n  |\n')
LOWER_BOUND = 0
UPPER_BOUND = 0
SATURATION = .6
LIGHTNESS = 1

def runSensors ():
	return Popen(['/usr/bin/sensors', '-u'], stdout=PIPE, stderr=PIPE)

def outToDict (s):
	adapters = s.split('\n\n')
	out = []
	for adapter in adapters:
		t1 = adapter.split('\n')
		length, t2, cur = len(t1), [], None
		for i in range(length):
			line = t1[i]
			if len(line) > 2 and line[0:2] == '  ':
				t3 = line[2:].split(': ')
				cur.append(t3)
			else:
				cur = [line[:-1]]
				t2.append(cur)
		out.append(t2[2:])
	return out[:-2][0]

def _strip_hex(h):
    # Strip leading `0x` if exists.
    if h.startswith('0x'):
        h = h.lstrip('0x')
    return h

def getHexColor (t):
	ratio = (float(t[0]) - LOWER_BOUND) / float(t[1]) # -24 gives us better range of colors (~room temp - max)

	# Hue, Saturation, Lightness
	rgb = colorsys.hls_to_rgb(*(colorsys.ONE_THIRD - colorsys.ONE_THIRD * ratio, SATURATION, LIGHTNESS))

	# convert to hex values ''.join([str, str, str])
	hexVals = [_strip_hex(str(hex(int(i * 255)))) for i in rgb]

	return colortrans.rgb2short(''.join(hexVals))

def formatColors (l):
	out = ''
	for sensor in l:
		v1, v2 = sensor[1][1], sensor[2][1]
		color = getHexColor((v1, v2))
		out += '%s: \033[38;5;%sm%s / %s\033[0m\n' % (sensor[0], color[0], v1, sensor[2][1])
	return out

def watch ():
	running_procs = [runSensors()]
	while running_procs:
		for proc in running_procs:
			ret_code = proc.poll()
			if ret_code is not None:
				proc_out = proc.stdout.read().decode("utf-8")
				print(formatColors(outToDict(proc_out)))
				running_procs.remove(proc)
				running_procs.append(runSensors())

		else: # wait for process to complete
			time.sleep(POLL_TIME)
			continue

		if ret_code != 0: # process returned a non-zero code
			print("Error: process returned %s" % ret_code, sys.stderr)

if __name__ == '__main__':
	watch()