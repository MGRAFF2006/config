#!/usr/bin/env python3
"""Set only an X11 window's input region, leaving its painted shape alone."""
import json
import math
import sys
from Xlib import X, display, error
from Xlib.ext import shape

connection = display.Display()

def report_error(exception, request):
    if not isinstance(exception, error.BadWindow):
        print('[WisprInputRegion] X11 error: ' + type(exception).__name__, file=sys.stderr)

connection.set_error_handler(report_error)
try:
    for line in sys.stdin:
        try:
            packet = json.loads(line)
            rectangles = packet['rects']
            if len(rectangles) > 128 or packet['width'] <= 0 or packet['height'] <= 0:
                raise ValueError('invalid region bounds')
            window = connection.create_resource_object('window', int(packet['window']))
            geometry = window.get_geometry()
            scale_x = geometry.width / packet['width']
            scale_y = geometry.height / packet['height']
            region = []
            for rectangle in rectangles:
                left = max(0, math.floor(rectangle['x'] * scale_x))
                top = max(0, math.floor(rectangle['y'] * scale_y))
                right = min(geometry.width, math.ceil((rectangle['x'] + rectangle['width']) * scale_x))
                bottom = min(geometry.height, math.ceil((rectangle['y'] + rectangle['height']) * scale_y))
                if right > left and bottom > top:
                    region.append((left, top, right - left, bottom - top))
            window.shape_rectangles(shape.SO.Set, shape.SK.Input, X.Unsorted, 0, 0, region)
            connection.sync()
        except error.BadWindow:
            pass  # A queued report may outlive its window.
        except (ValueError, KeyError, TypeError) as exception:
            print('[WisprInputRegion] Invalid report: ' + str(exception), file=sys.stderr)
finally:
    connection.close()
