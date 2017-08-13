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
import subprocess
import typing as T

from gi.repository import GLib, Gtk
from pydbus import SessionBus

from . import preferences


SelectAreaCallback = T.Callable[[T.Tuple[float, float, float, float]], None]


class Recorder():
    def start(self, desired_output: str, config: preferences.ConfigurationType):
        raise NotImplementedError()

    def stop(self) -> str:
        '''
        Stops the recording and returns a path to the video file
        '''
        raise NotImplementedError()

    def select_area(self, callback: SelectAreaCallback):
        raise NotImplementedError()


class XorgRecorder(Recorder):
    def start(self, desired_output: str, config: preferences.ConfigurationType):
        if config['area'] is not None:
            x, y, w, h = config['area']
            size = '{}x{}'.format(w, h)
            display = '{}+{},{}'.format(os.environ['DISPLAY'], x, y)

        command = ["ffmpeg", "-video_size", size]

        if config['record_mouse']:
            command.append("-draw_mouse")
            command.append("1")

        if config['follow_mouse']:
            command.append("-follow_mouse")
            command.append("centered")

        command.extend([
            "-framerate", config['frame_rate'],
            "-f", "x11grab", "-i", display,
            "-q", 1, desired_output,
            "-c:v", config['codec_video'],
            "-y"])

        self._process = subprocess.Popen(command)
        self._outfile = desired_output

    def stop(self) -> str:
        self._process.terminate()
        return self._outfile

    def select_area(self, callback: SelectAreaCallback):
        builder = Gtk.Builder()
        builder.add_from_resource('/today/sam/green-recorder/XorgAreaChoser.ui')
        window = builder.get_object('window')
        accept_button = builder.get_object('accept')

        window.show()
        accept_button.connect('clicked', self.handle_accept_clicked, callback)

    def _area_from_command(self, command):
        output = subprocess.check_output(
            [command + '| grep -e Width -e Height -e Absolute'],
            shell=True).decode()[:-1]

        return [int(l.split(':')[1]) for l in output.split('\n')]

    def handle_accept_clicked(self, button, callback):
        callback(self._area_from_command('xwininfo -name "Area Chooser"'))
        button.get_window().destroy()


class GnomeRecorder(Recorder):

    def __init__(self):
        self._screencast = SessionBus().get(
            'org.gnome.Shell.Screencast', '/org/gnome/Shell/Screencast')
        self._screenshot = SessionBus().get(
            'org.gnome.Shell.Screenshot', '/org/gnome/Shell/Screenshot')

    def start(self, desired_output: str, config: preferences.ConfigurationType):
        if config['codec_video'] == 'vp8':
            pipeline = '''
                vp8enc min_quantizer=10
                        max_quantizer=50
                        cq_level=13
                        cpu-used=5
                        deadline=1000000
                        threads=%T
                ! queue
                ! webmmux'''
        else:
            assert False

        options = {
            'framerate': GLib.Variant('i', config['frame_rate']),
            'draw-cursor': GLib.Variant('b', config['record_mouse']),
            'pipeline': GLib.Variant('s', pipeline)}
        if config['area'] is None:
            self._screencast.Screencast(desired_output, options)
        else:
            x, y, w, h = config['area']
            self._screencast.ScreencastArea(
                x, y, w, h,
                desired_output, options)
        self._outfile = desired_output

    def stop(self) -> str:
        self._screencast.StopScreencast()
        return self._outfile

    def select_area(self, callback: SelectAreaCallback):
        # TODO: get async DBus working - never block the mainloop
        res = self._screenshot.SelectArea()
        callback(res)


session = os.environ.get('XDG_SESSION_TYPE', 'xorg')
if 'wayland' == session:
    _recorder = GnomeRecorder()
elif 'xorg' in session:
    _recorder = XorgRecorder()
else:
    raise SystemError(f'No recorder found for session {session}')


def get_recorder():
    return _recorder
