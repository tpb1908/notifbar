#!/usr/bin/env python
from typing import Optional, List
from threading import Thread, Event
import os
import argparse
from warnings import warn
import gi
from dbus import SessionBus

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
gi.require_version('Notify', '0.7')
from gi.repository.GdkPixbuf import Pixbuf
from gi.repository import Gtk, Gdk, GObject
from Xlib.display import Display
from Xlib import X
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import dbus.service

GObject.threads_init()


class ActionInvoker(dbus.service.Object):
    NOTIFICATIONS_DBUS_INTERFACE = 'org.freedesktop.Notifications'
    NOTIFICATIONS_DBUS_OBJECT_PATH = '/org/freedesktop/Notifications'

    def __init__(self):
        # bus_name = dbus.service.BusName(self.NOTIFICATIONS_DBUS_INTERFACE, bus=dbus.SessionBus())
        # dbus.service.Object.__init__(self, bus_name, self.NOTIFICATIONS_DBUS_OBJECT_PATH)
        super().__init__(
            object_path=self.NOTIFICATIONS_DBUS_OBJECT_PATH,
            bus_name=dbus.service.BusName(
                name=self.NOTIFICATIONS_DBUS_INTERFACE,
                bus=SessionBus(mainloop=DBusGMainLoop())
            )
        )

    @dbus.service.signal(NOTIFICATIONS_DBUS_INTERFACE, signature='us')
    def ActionInvoked(self, id_in, action_key_in):
        print(f"ActionInvoked {id_in} {action_key_in}")
        pass

    @dbus.service.signal(NOTIFICATIONS_DBUS_INTERFACE, signature='uu')
    def NotificationClosed(self, id_in, reason_in):
        pass

    @dbus.service.signal(NOTIFICATIONS_DBUS_INTERFACE, signature='u')
    def CloseNotification(self, id_in):
        pass


stylesheet = b"""
window#bar {
  background-color: darkred;
}

GtkWidget { padding-left: 0; padding-right: 0; padding: 0; margin: 0;}
"""

bar_size = 35


# Dock bar implementation modified from https://gist.github.com/johnlane/351adff97df196add08a
class TestBar(Gtk.Window):

    def __init__(self, notification: int, summary: str, body: str, application: str, icon_path: Optional[str] = None,
                 timeout: Optional[int] = -1, actions: Optional[List[List]] = None, dismiss: bool = False):
        # Set up empty window and add style
        Gtk.Window.__init__(self)

        # No need to provide a mainloop, as we are only sending

        # Version information
        print("Gtk %d.%d.%d" % (Gtk.get_major_version(),
                                Gtk.get_minor_version(),
                                Gtk.get_micro_version()))
        self.notification = notification
        self.body = body
        self.summary = summary
        self.application = application
        self.icon_path = icon_path
        self.timeout = timeout
        self.actions = actions
        self.dismiss = dismiss

        self.set_name("bar")
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.set_decorated(False)
        self.connect("delete-event", Gtk.main_quit)

        # style_provider = Gtk.CssProvider()
        # style_provider.from_data(stylesheet)
        # Gtk.StyleContext.add_provider_for_screen(
        #     Gdk.Screen.get_default(),
        #     style_provider,
        #     Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Layout container
        self.hbox = Gtk.Box(spacing=5)
        self.hbox.set_homogeneous(False)

        message_str = "<big>{}</big>".format(self.application)

        if icon_path is not None:
            if self._try_init_icon():
                message_str = ""  # Application displayed with icon

        self.message = Gtk.Label()

        if self.body is None:
            message_str += "<b>{}</b>".format(self.summary)
        else:
            message_str += "<b>{}</b>\n{}".format(self.summary, self.body)
        self.message.set_markup(message_str)
        self.hbox.pack_start(self.message, False, True, 0)

        self._init_action_buttons()
        button = Gtk.Button.new_with_mnemonic("_OK")
        button.connect("clicked", self.done)
        self.hbox.pack_end(button, False, False, 0)

        self.add(self.hbox)

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
        print(f"Window shown. Size {self.get_size()}")
        print(f"Window shown. Size {self.get_size()}")
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

        self.invoker = ActionInvoker()

        print(f"Timeout {self.timeout}")
        self.timer = Event()
        if self.timeout > 0:
            seconds = timeout / 1000
            def sleep_then_quit():
                self.timer.wait(seconds)
                self.quit()

            Thread(target=sleep_then_quit).start()

        print("Running main loop")

        Gtk.main()

    def _try_init_icon(self) -> bool:
        liststore = Gtk.ListStore(Pixbuf, str)
        iconview = Gtk.IconView.new()
        iconview.set_model(liststore)
        iconview.set_pixbuf_column(0)
        iconview.set_text_column(1)
        iconview.set_selection_mode(Gtk.SelectionMode.NONE)
        iconview.set_item_orientation(Gtk.Orientation.HORIZONTAL)
        iconview.set_item_padding(0)
        # TODO: Deal with errors
        ap = os.path.abspath(self.icon_path)
        print(f"Loading icon from {ap}")
        # TODO: Icon dimensions should be configurable
        try:
            liststore.append([Pixbuf.new_from_file_at_scale(ap, width=24,
                                                            height=24,
                                                            preserve_aspect_ratio=True), self.application])
        except Exception as e:
            warn(f"Could not load icon {self.icon_path} abspath {ap}. Exception: {e}")
            return False

        self.hbox.pack_start(iconview, False, False, 0)
        return True

    def _init_action_buttons(self):
        for action in self.actions:
            if len(action) != 2:
                warn(f"Action {action} invalid format. Should be two parts")
            button = Gtk.Button(label=action[1])
            button.connect("clicked", self.invoke_action)
            self.hbox.pack_end(button, False, False, 0)
        pass

    def done(self, button):
        print(f"Button {button.get_label()} clicked")
        self.quit()

    def invoke_action(self, button):

        for action in self.actions:
            if button.get_label() == action[1]:
                DBusGMainLoop(set_as_default=True)
                self.invoker.ActionInvoked(self.notification, action[0])

                print(f"Button pressed. Label {button.get_label()}")
                self.quit()
                return

        # I don't think this will happen, but working off the label strings seems fragile
        warn(f"No matching action found for button label {button.get_label()}. Actions {self.actions}")

    def quit(self):
        self.timer.set()
        if self.dismiss:
            print(f"Dismissing notification {self.notification}")
            DBusGMainLoop(set_as_default=True)
            self.invoker.CloseNotification(self.notification)
            #self.invoker.NotificationClosed(self.notification, 2)  # closed by user
        Gtk.main_quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Display a notification bar')
    urgencies = ["low", "normal", "critical"]
    parser.add_argument('-u', '--urgency', choices=urgencies, help=f"Notification urgency {urgencies}",
                        default=urgencies[1])
    parser.add_argument('-n', '--notification', type=int, help="Notification id")
    parser.add_argument('-s', '--summary', type=str, help="Message summary string (may be markup)")


    # Convert empty strings to None, rather than checking each one later
    def nullable_string(val: str) -> str:
        print(f"Checking nullable string: {val}")
        if not val.strip():
            return None
        return val


    parser.add_argument('-b', '--body', type=nullable_string, help="Message body (may be markup)")
    parser.add_argument('-a', '--application', type=nullable_string)
    # Notification actions used rather than i3-bar buttons
    # parser.add_argument('-b', '--button', nargs='+')
    parser.add_argument('-t', '--expire-time', type=int, default=-1, dest='timeout')
    parser.add_argument('-i', '--icon', type=nullable_string, required=False, default=None, help="Path to icon")
    parser.add_argument('-e', '--action', dest="actions", action='append', nargs=2, metavar=('identifier', 'name'),
                        help="Identifier and name for actions", default=[])
    parser.add_argument('-d', '--dismiss', type=bool, default=False, help="Dismiss notification once viewed")
    # Arguments not needed for now
    # http://www.galago-project.org/specs/notification/0.9/x211.html
    # parser.add_argument('-c', '--category')
    # Also hints
    # http://www.galago-project.org/specs/notification/0.9/x344.html

    args = parser.parse_args()
    print(args)

    TestBar(args.notification, args.summary, args.body, args.application, args.icon, args.timeout, args.actions, args.dismiss)
