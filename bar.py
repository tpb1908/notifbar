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

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk
from Xlib.display import Display
from Xlib import X

import argparse

# Colour style for (b)
stylesheet = b"""
window#bar {
  background-color: darkred;
}
"""

#  the size of the bar (its height), in pixels
bar_size = 50


class TestBar(Gtk.Window):

    def __init__(self, message: str):
        # Version information
        print("Gtk %d.%d.%d" % (Gtk.get_major_version(),
                                Gtk.get_minor_version(),
                                Gtk.get_micro_version()))

        # (a) Create an undecorated dock
        Gtk.Window.__init__(self)
        self.set_name("bar")
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_decorated(False)
        self.connect("delete-event", Gtk.main_quit)

        # (b) Style it
        style_provider = Gtk.CssProvider()
        style_provider.load_from_data(stylesheet)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        hbox = Gtk.Box(spacing=10)
        hbox.set_homogeneous(False)

        label = Gtk.Label()
        label.set_text(message)

        #label.set_justify(Gtk.Justification.LEFT)

        hbox.pack_start(label, False, True, 0)

        button = Gtk.Button.new_with_mnemonic("_OK")
        button.connect("clicked", self.done)
        hbox.pack_end(button, False, False, 0)

        self.add(hbox)

        # the screen contains all monitors
        screen = self.get_screen()
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
        self.move(x, y)
        self.resize(width, bar_size)

        # it must be shown before changing properties
        self.show_all()
        print("Window shown")
        # (d) reserve space (a "strut") for the bar so it does not become obscured
        #     when other windows are maximized, etc
        # http://stackoverflow.com/questions/33719686  property_change not in gtk3.0
        # https://sourceforge.net/p/python-xlib/mailman/message/27574603
        display = Display()
        topw = display.create_resource_object('window',
                                              self.get_toplevel().get_window().get_xid())

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

        print("Running main loop")
        Gtk.main()

    def done(self, button):
        Gtk.main_quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display a notification bar')
    urgencies = ["low", "normal", "critical"]
    parser.add_argument('-u', '--urgency', choices=urgencies, help=f"Notification urgency {urgencies}",
                        default=urgencies[1])
    parser.add_argument('-m', '--message', type=str, help="Message to display")
    parser.add_argument('-b', '--button', nargs='+')
    parser.add_argument('-t', '--timeout', type=int, default=20)
    args = parser.parse_args()
    print(args)

    TestBar(args.message)
