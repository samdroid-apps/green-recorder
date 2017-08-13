#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Copyright FOSS Project <https://foss-project.com>, 2017.
# Copyright Sam Parkinson <sam@sam.today>, 2017.
#
# Green Recorder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Green Recorder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Green Recorder.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import signal
import subprocess
import typing as T
from gettext import gettext as _

from pydbus import SessionBus
from gi.repository import Gtk, Gdk, GLib, AppIndicator3, Gio

from . import about
from . import preferences
from .preferences import DEFAULTS
from . import util
from . import recorder


# Define a loop and connect to the session bus. This is for Wayland
# recording under GNOME Shell.
loop = GLib.MainLoop()
bus = SessionBus()


def is_running_mate():
    return not subprocess.call("ps -cat | grep mate-panel", shell=True)


def send_notification(text: str, time: int = 5):
    notifications = bus.get('.Notifications')
    notifications.Notify('GreenRecorder', 0, 'green-recorder',
                         "Green Recorder", text, [], {}, time * 1000)


class AppWindow():

    def __init__(self, application):
        self._indicator = None
        self._areaaxis = None
        self._config = DEFAULTS.copy()

        # Import the glade file and its widgets.
        builder = Gtk.Builder()
        builder.add_from_resource('/today/sam/green-recorder/AppWindow.ui')
        self._builder = builder

        # Create pointers.
        self._window = builder.get_object("window")
        self._areachooser = builder.get_object("window2")
        self._playbutton = builder.get_object("playbutton")
        self._filename_entry = builder.get_object('filename')
        self._folder_entry = builder.get_object('folder')
        self._select_entire = builder.get_object('select_entire')
        self._select_window = builder.get_object('select_window')
        self._select_area = builder.get_object('select_area')

        self._window.props.application = application
        self._window.show()

        # Get defaults from DEFAULTSuration file.
        self._folder_entry.set_uri(DEFAULTS['folder'])
        self._filename_entry.set_text(DEFAULTS['filename'])

        self._playbutton.set_sensitive(False)
        self._setup_audio_sources()
        self._setup_advanced()

        builder.connect_signals(self)

    def show(self):
        self._window.show_all()

    def _setup_audio_sources(self):
        combo = self._builder.get_object('audio_combo')
        combo.append('none', _('No Audio'))
        combo.append('default', _('Default Audio Input'))

        names_output = subprocess.check_output(
            'pacmd list-sources | grep -e device.description', shell=True)
        names = names_output.decode().split("\n")[:-1]
        if names:
            for i, name in enumerate(names):
                name = name.replace("\t\tdevice.description = ", "") \
                           .replace('"', '')
                combo.append(str(i), name)

        combo.set_active(1)

    def _setup_advanced(self):
        container = self._builder.get_object('advanced_container')
        prefs = preferences.PrefsView(self._config, hide_head=True)
        container.add(prefs.root)

    def _create_recorder_indicator(self):
        # Create the app indicator widget.
        if is_running_mate():
            self._indicator = AppIndicator3.Indicator.new(
                "Green Recorder", 'green-recorder',
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        else:
            self._indicator = AppIndicator3.Indicator.new(
                "Green Recorder", '/usr/share/pixmaps/green-recorder.png',
                AppIndicator3.IndicatorCategory.SYSTEM_SERVICES)
        self._indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        menu, button = self._create_indicator_menu()
        self._indicator.set_menu(menu)
        # Make middle-click stops the recording process.
        self._indicator.set_secondary_activate_target(button)

    def _create_indicator_menu(self):
        # Here menu items are defined and built. Used global on
        # stop_recordingbutton to pass it as a Gtk.Widget to the indicator to be
        # able to stop recording using middle click on the icon directly.
        menu = Gtk.Menu()
        stop_recordingbutton = Gtk.MenuItem('Stop Recording')
        stop_recordingbutton.connect(
            'activate', self.handle_stop_recording_activate)
        menu.append(stop_recordingbutton)
        menu.show_all()
        return menu, stop_recordingbutton

    def handle_stop_recording_activate(self, menu_item):
        self._indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
        self._window.show()
        self._playbutton.set_sensitive(True)

        self._recorded_fp = self._recorder.stop()
        self._update_file_warning()

    def record(self):
        # Hide the window. Used flush() to avoid the interface waiting.
        self._window.hide()
        Gdk.flush()

        self._recorder = recorder.Recorder(self._config)
        self._create_recorder_indicator()

    def handle_recordclicked(self, GtkButton):
        self.record()

    def _set_area_from_command(self, command):
        output = subprocess.check_output(
            [command + '| grep -e Width -e Height -e Absolute'],
            shell=True).decode()[:-1]

        self._config['area'] = [int(l.split(':')[1]) for l in output.split('\n')]

    def handle_select_entire(self, button: Gtk.ToggleButton):
        if not button.props.active:
            return
        self._select_area.props.active = False
        self._select_window.props.active = False

        self._config['area'] = None

    def handle_select_area(self, button: Gtk.ToggleButton):
        if not button.props.active:
            return
        self._select_entire.props.active = False
        self._select_window.props.active = False

        self._areachooser.show()

    def handle_select_window(self, button: Gtk.ToggleButton):
        if not button.props.active:
            return
        self._select_entire.props.active = False
        self._select_area.props.active = False

        self._set_area_from_command('xwininfo')

    def handle_playbuttonclicked(self, GtkButton):
        subprocess.call(["xdg-open", self._recorded_fp])

    def handle_areasettings(self, GtkButton):
        self._set_area_from_command('xwininfo -name "Area Chooser"')
        send_notification("Your area position has been saved!", 3)

    def handle_folder_chosen(self, chooser):
        self._config['folder'] = chooser.get_uri()
        self._update_file_warning()

    def handle_filename_entry_change(self, entry: Gtk.Entry):
        self._config['filename'] = entry.props.text
        self._update_file_warning()

    def _update_file_warning(self):
        path = os.path.join(
            util.url_to_filepath(self._folder_entry.get_uri()),
            self._config['filename'] + '.' + self._config['format'])
        self._filename_entry.props.secondary_icon_name = (
            'dialog-warning-symbolic' if os.path.isfile(path) else None)

    def handle_audio_changed(self, combo: Gtk.ComboBoxText):
        self._config['audio'] = combo.get_active_id()


class Application(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(
            self, application_id='today.sam.green-recorder')
        GLib.set_application_name(_("Green Recorder"))
        GLib.set_prgname('green-recorder')

    def do_activate(self):
        window = AppWindow(self)
        window.show()

    def _build_app_menu(self):
        action_entries = [
            ('about', self.handle_about),
            ('preferences', self.handle_preferences),
            ('quit', self.quit),
        ]

        for action, callback in action_entries:
            simple_action = Gio.SimpleAction.new(action, None)
            simple_action.connect('activate', callback)
            self.add_action(simple_action)

        builder = Gtk.Builder.new_from_resource(
            '/today/sam/green-recorder/gtk/menus.ui')
        self._menu = builder.get_object('app-menu')
        self.props.app_menu = self._menu

    def handle_preferences(self, action, param):
        win = preferences.PrefsWindow()
        win.show()

    def handle_about(self, action, param):
        win = about.AboutWindow()
        win.show()

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self._build_app_menu()


# Load CSS for Area Chooser.
style_provider = Gtk.CssProvider()
css = b'''
#AreaChooser {
    background-color: rgba(255, 255, 255, 0);
    border: 1px solid red;
}

.SettingsRow__row {
    background: white;
    padding: 12px 18px;
}

.SettingsRow__header {
    font-weight: bold;
    margin-top: 18px;
    margin-bottom: 6px;
}
.SettingsRow__header:first-child {
    margin-top: 0;
}
'''
style_provider.load_from_data(css)
Gtk.StyleContext.add_provider_for_screen(
    Gdk.Screen.get_default(),
    style_provider,
    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = Application()
    app.run(sys.argv)
