#!/usr/bin/env python
#
# dockbar.py
#
# Example program places a coloured bar across the top of the
# current monitor
#
# demonstrates
#
# (a) creating the bar as an undecorated "dock" window
# (b) setting its colour
# (c) getting the number of monitors and their sizes
#
#                                               JL 20140512, 20170220

import gi
gi.require_version('Gtk','3.0')
from gi.repository import Gtk, Gdk
import Xlib
from Xlib.display import Display
from Xlib import X

# Colour style for (b)
stylesheet=b"""
window#bar {
  background-color: darkred;
}
"""

#  the size of the bar (its height), in pixels
bar_size = 50

class TestBar:

    def __init__(self):
        # Version information
        print("Gtk %d.%d.%d" % (Gtk.get_major_version(),
                                Gtk.get_minor_version(),
                                Gtk.get_micro_version()))

        # (a) Create an undecorated dock
        window = Gtk.Window()
        window.set_name("bar")
        window.set_type_hint(Gdk.WindowTypeHint.DOCK)
        window.set_decorated(False)
        window.connect("delete-event", Gtk.main_quit)

        # (b) Style it
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(stylesheet)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # the screen contains all monitors
        screen = window.get_screen()
        width = screen.width()  # width = Gdk.Screen.width()
        print("width: %d" % width)

        # (c) collect data about each monitor
        monitors = []
        nmons = screen.get_display().get_n_monitors()
        print("there are %d monitors" % nmons)
        for m in range(nmons):
            mg = screen.get_monitor_geometry(m)
            print("monitor %d: %d x %d" % (m, mg.width, mg.height))
            monitors.append(mg)

        # current monitor
        curmon = screen.get_monitor_at_window(screen.get_active_window())
        x = monitors[curmon].x
        y = monitors[curmon].y
        width = monitors[curmon].width
        height = monitors[curmon].height
        print("monitor %d: %d x %d (current, offset %d)" % (curmon, width, height, x))
        print("bar: start=%d end=%d" % (x, x + width - 1))

        # display bar along the top of the current monitor
        window.move(x, y)
        window.resize(width, bar_size)

        # it must be shown before changing properties
        window.show_all()
        print("Window shown")
        # (d) reserve space (a "strut") for the bar so it does not become obscured
        #     when other windows are maximized, etc
        # http://stackoverflow.com/questions/33719686  property_change not in gtk3.0
        # https://sourceforge.net/p/python-xlib/mailman/message/27574603
        display = Display()
        topw = display.create_resource_object('window',
                                              window.get_toplevel().get_window().get_xid())

        # http://python-xlib.sourceforge.net/doc/html/python-xlib_21.html#SEC20
        topw.change_property(display.intern_atom('_NET_WM_STRUT'),
                             display.intern_atom('CARDINAL'), 32,
                             [0, 0, bar_size, 0],
                             X.PropModeReplace)
        topw.change_property(display.intern_atom('_NET_WM_STRUT_PARTIAL'),
                             display.intern_atom('CARDINAL'), 32,
                             [0, 0, bar_size, 0, 0, 0, 0, 0, x, x + width - 1, 0, 0],
                             X.PropModeReplace)

        # we set _NET_WM_STRUT, the older mechanism as well as _NET_WM_STRUT_PARTIAL
        # but window managers ignore the former if they support the latter.
        #
        # the numbers in the array are as follows:
        #
        # 0, 0, bar_size, 0 are the number of pixels to reserve along each edge of the
        # screen given in the order left, right, top, bottom. Here the size of the bar
        # is reserved at the top of the screen and the other edges are left alone.
        #
        # _NET_WM_STRUT_PARTIAL also supplies a further four pairs, each being a
        # start and end position for the strut (they don't need to occupy the entire
        # edge).
        #
        # In the example, we set the top start to the current monitor's x co-ordinate
        # and the top-end to the same value plus that monitor's width, deducting one.
        # because the co-ordinate system starts at zero rather than 1. The net result
        # is that space is reserved only on the current monitor.
        #
        # co-ordinates are specified relative to the screen (i.e. all monitors together).
        #

        # main event loop
        # Gtk.main()
        # Control-C termination broken in GTK3 http://stackoverflow.com/a/33834721
        # https://bugzilla.gnome.org/show_bug.cgi?id=622084
        from gi.repository import GLib
        # self.mainloop = GObject.MainLoop()
        # try:
        #     self.mainloop.run()
        # except KeyboardInterrupt:
        #     print("Keyboard interrupt")
        #     self.mainloop.quit()
        print("Running main loop")
        GLib.MainLoop().run()

if __name__ == "__main__":
    TestBar()