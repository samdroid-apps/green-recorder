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
import urllib.parse
import datetime
import subprocess
import configparser
import typing as T
from gettext import gettext as _

from pydbus import SessionBus
from gi.repository import Gtk, Gdk, GLib, AppIndicator3, Gio

from . import screenrecorder
from . import about


class Configuration():

    DEFAULTS = {
        'frames': 30,
        'delay': 0,
        'folder': os.path.join(
            'file://',
            GLib.get_user_special_dir(GLib.USER_DIRECTORY_VIDEOS)),
        'command': '',
        'filename': '',
        'videocheck': True,
        'audiocheck': True,
        'mousecheck': True,
        'followmousecheck': False,
    }

    def __init__(self):
        directory = os.path.join(GLib.get_user_config_dir(), 'green-recorder/')
        if not os.path.exists(directory):
            os.makedirs(directory)
        self._file_path = os.path.join(directory, "config.ini")

        self._cp = configparser.ConfigParser()

        if os.path.isfile(self._file_path):
            self._cp.read(self._file_path)

        if not self._cp.has_section('Options'):
            self._cp.add_section('Options')
            self.save()

    def __setitem__(self, name: str, value: T.Union[str, bool, float]):
        self._cp.set('Options', name, str(value))
        self.save()

    def __getitem__(self, name: str):
        default = self.DEFAULTS[name]
        if not self._cp.has_option('Options', name):
            return default

        if isinstance(default, bool):
            return self._cp.getboolean('Options', name)
        if isinstance(default, (int, float)):
            return self._cp.getfloat('Options', name)
        return self._cp.get('Options', name)

    def save(self):
        with open(self._file_path, 'w') as f:
            self._cp.write(f)


config = Configuration()


def url_to_filepath(url: str):
    '''
    Takes a url (or filepath) and returns a file path
    '''
    res = urllib.parse.urlparse(url)
    assert (not res.scheme) or (res.scheme == 'file')
    return res.path


# Define a loop and connect to the session bus. This is for Wayland
# recording under GNOME Shell.
loop = GLib.MainLoop()
bus = SessionBus()

DISPLAY_SERVER = os.environ.get("XDG_SESSION_TYPE", "xorg")
if "wayland" in DISPLAY_SERVER:
    DISPLAY_SERVER = "gnomewayland"
else:
    DISPLAY_SERVER = "xorg"


def is_running_mate():
    return not subprocess.call("ps -cat | grep mate-panel", shell=True)


def send_notification(text: str, time: int = 5):
    notifications = bus.get('.Notifications')
    notifications.Notify('GreenRecorder', 0, 'green-recorder',
                         "Green Recorder", text, [], {}, time * 1000)


class PrefsWindow():

    def __init__(self):
        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/today/sam/green-recorder/PrefsWindow.ui')
        self._builder.connect_signals(self)

        self._window = self._builder.get_object('window')

        self._builder.get_object('video').props.state = config['videocheck']
        self._builder.get_object('mouse').props.state = config['mousecheck']
        self._builder.get_object('followmouse').props.state = config['followmousecheck']
        self._builder.get_object('delay').props.value = config['delay']
        self._builder.get_object('frames').props.value = config['frames']
        self._builder.get_object('audio').props.state = config['audiocheck']
        self._builder.get_object('filename').props.text = config['filename']
        self._builder.get_object('command').props.text = config['command']
        self._builder.get_object('folder').set_uri(config['folder'])

    def show(self):
        self._window.show()

    def handle_video_record_switch(self, switch, state):
        config['videocheck'] = state

    def handle_audio_record_switch(self, switch, state):
        config['audiocheck'] = state

    def handle_mouse_switch(self, switch, state):
        config['mousecheck'] = state

    def handle_follow_mouse_switch(self, switch, state):
        config['followmousecheck'] = state

    def handle_filename_changed(self, entry):
        config['filename'] = entry.props.text

    def handle_delay_changed(self, button):
        config['delay'] = button.props.value

    def handle_frames_changed(self, button):
        config['frames'] = button.props.value

    def handle_command_changed(self, entry):
        config['command'] = entry.props.text

    def handle_folder_chosen(self, chooser):
        config['folder'] = chooser.get_uri()


class AppWindow():

    def __init__(self, application):
        self._indicator = None
        self._areaaxis = None

        # Import the glade file and its widgets.
        builder = Gtk.Builder()
        builder.add_from_resource('/today/sam/green-recorder/AppWindow.ui')
        self._builder = builder

        # Create pointers.
        self._window = builder.get_object("window1")
        self._areachooser = builder.get_object("window2")
        self._folderchooser = builder.get_object("filechooserbutton1")
        self._filenameentry = builder.get_object("entry1")
        self._commandentry = builder.get_object("entry2")
        self._windowgrabbutton = builder.get_object("button4")
        self._areagrabbutton = builder.get_object("button5")
        self._videocheck = builder.get_object("checkbutton1")
        self._audiocheck = builder.get_object("checkbutton2")
        self._mousecheck = builder.get_object("checkbutton3")
        self._followmousecheck = builder.get_object("checkbutton4")
        self._delayvalue = builder.get_object('spinbutton2')
        self._audiosource = self._builder.get_object("audiosource")
        delayadjustment = builder.get_object("adjustment1")
        framesadjustment = builder.get_object("adjustment2")
        self._playbutton = builder.get_object("playbutton")
        self._formatchooser = self._builder.get_object("comboboxtext1")
        self._framesvalue = self._builder.get_object("spinbutton1")

        self._window.props.application = application
        self._window.show()

        # Get defaults from configuration file.
        delayadjustment.set_value(config['delay'])
        framesadjustment.set_value(config['frames'])
        FolderPath = config['folder']
        self._folderchooser.set_uri(urllib.parse.unquote(FolderPath))
        self._commandentry.set_text(config['command'])
        self._filenameentry.set_text(config['filename'])

        self._videocheck.set_active(config['videocheck'])
        self._audiocheck.set_active(config['audiocheck'])
        self._mousecheck.set_active(config['mousecheck'])
        self._followmousecheck.set_active(config['followmousecheck'])

        self._playbutton.set_sensitive(False)
        self._setup_audio_sources()
        self._setup_formats()

        builder.connect_signals(self)

    def show(self):
        self._window.show_all()

    def _setup_audio_sources(self):
        combo = self._builder.get_object("audiosource")

        # Audio input sources
        combo.append("default", _("Default PulseAudio Input Source"))
        names_output = subprocess.check_output(
            "pacmd list-sources | grep -e device.description", shell=True)
        names = names_output.decode().split("\n")[:-1]

        for i, name in enumerate(names):
            name = name.replace("\t\tdevice.description = ", "") \
                       .replace('"', '')

            combo.append(str(i), name)

        combo.set_active(0)

    def _setup_formats(self):
        formatchooser = self._builder.get_object("comboboxtext1")

        # Disable unavailable functions under Wayland.
        if "wayland" in DISPLAY_SERVER:
            self._windowgrabbutton.set_sensitive(False)
            self._areagrabbutton.set_sensitive(False)
            self._followmousecheck.set_sensitive(False)
            formatchooser.append("webm", "WebM (The Open WebM Format)")
        else:
            formatchooser.append(
                "mkv", _("MKV (Matroska multimedia container format)"))
            formatchooser.append("avi", _("AVI (Audio Video Interleaved)"))
            formatchooser.append("mp4", _("MP4 (MPEG-4 Part 14)"))
            formatchooser.append("wmv", _("WMV (Windows Media Video)"))
            formatchooser.append("gif", _("GIF (Graphics Interchange Format)"))
            formatchooser.append("nut", _("NUT (NUT Recording Format)"))
        formatchooser.set_active(0)

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
        self.stop_recording()

    def record(self):
        # Hide the window. Used flush() to avoid the interface waiting.
        self._window.hide()
        Gdk.flush()

        self._video_recorder = None
        self._audio_recorder = None

        if len(self._filenameentry.get_text()) < 1:
            filename = str(datetime.datetime.now())
        else:
            filename = self._filenameentry.get_text()
        extension = self._formatchooser.get_active_id()
        basename = url_to_filepath(os.path.join(
            self._folderchooser.get_uri(),
            filename))
        self._mixed_file_output = f'{basename}.{extension}'

        delay = str(self._delayvalue.get_value_as_int())
        subprocess.call(["sleep", delay])

        if self._videocheck.get_active():
            area = self._areaaxis
            options = {
                'format': self._formatchooser.get_active_id(),
                'mouse': self._mousecheck.get_active(),
                'follow_mouse': self._followmousecheck.get_active(),
                'frame_rate': self._framesvalue.get_value_as_int()}
            if "xorg" in DISPLAY_SERVER:
                self._video_recorder = screenrecorder.XorgRecorder()
            elif "gnomewayland" in DISPLAY_SERVER:
                self._video_recorder = screenrecorder.GnomeRecorder()
            else:
                send_notification('Your display server is not supported!')
                self._window.show()
                return

            self._video_recorder.start(
                area, f'{basename}.video.{extension}', **options)

        if self._audiocheck.get_active():
            self._audio_recorder_file = f'{basename}.audio.{extension}'
            cmd = ['ffmpeg', '-f', 'pulse',
                   '-i', self._audiosource.get_active_id(),
                   '-strict', '-2',
                   self._audio_recorder_file,
                   '-y']
            self._audio_recorder = subprocess.Popen(cmd)

        self._create_recorder_indicator()

    def stop_recording(self):
        subprocess.call(["sleep", "1"])  # Wait ffmpeg

        self._indicator.set_status(AppIndicator3.IndicatorStatus.PASSIVE)
        self._window.show()
        self._playbutton.set_sensitive(True)

        self._areaaxis = None

        stream_files = []
        if self._video_recorder is not None:
            stream_files.append(self._video_recorder.stop())
        if self._audio_recorder is not None:
            self._audio_recorder.terminate()
            stream_files.append(self._audio_recorder_file)

        # FIXME: why?
        subprocess.call(["sleep", "1"])

        if len(stream_files) == 1:
            os.rename(stream_files[0], self._mixed_file_output)
        else:
            cmd = ['ffmpeg']
            for f in stream_files:
                cmd.extend(['-i', f])
            cmd += ['-c', 'copy', self._mixed_file_output, '-y']
            subprocess.check_call(cmd)

            for f in stream_files:
                os.remove(f)

        if self._formatchooser.get_active_id() == "gif":
            send_notification(
                "Your GIF image is currently being processed, this may take a "
                "while according to your PC's resources.",
                5)

            subprocess.call(["mv", self._mixed_file_output,
                             self._mixed_file_output + ".tmp"])
            subprocess.call(["convert", "-layers", "Optimize",
                             self._mixed_file_output + ".tmp",
                             self._mixed_file_output])
            subprocess.call(["rm", self._mixed_file_output + ".tmp"])

        post_command = self._commandentry.get_text()
        if post_command:
            subprocess.Popen([post_command], shell=True)


    def handle_recordclicked(self, GtkButton):
        self.record()

    def _set_area_from_command(self, command):
        output = subprocess.check_output(
            [command + '| grep -e Width -e Height -e Absolute'],
            shell=True).decode()[:-1]

        self._areaaxis = [int(l.split(':')[1]) for l in output.split('\n')]

    def handle_selectwindow(self, GtkButton):
        self._set_area_from_command('xwininfo')
        send_notification("Your window position has been saved!", 3)

    def handle_selectarea(self, GtkButton):
        self._areachooser.set_title(_("Area Chooser"))
        self._areachooser.show()

    def handle_playbuttonclicked(self, GtkButton):
        subprocess.call(["xdg-open", self._mixed_file_output])

    def handle_areasettings(self, GtkButton):
        self._set_area_from_command('xwininfo -name "Area Chooser"')
        send_notification("Your area position has been saved!", 3)


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
        win = PrefsWindow()
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

.PrefsWindow frame > box > grid {
    background: white;
    padding: 12px 18px;
}

.PrefsWindow__header_label {
    font-weight: bold;
    margin-top: 18px;
    margin-bottom: 6px;
}
.PrefsWindow__header_label:first-child {
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
