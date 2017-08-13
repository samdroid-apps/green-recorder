import os
import configparser
import typing as T
from gettext import gettext as _

from gi.repository import Gtk, GLib


ConfigurationType = T.NewType(
    'Configuration', T.Dict[str, T.Union[str, bool, float]])


class DefaultsConfiguration():

    DEFAULTS = {
        'frame_rate': 30,
        'delay': 0,
        'folder': os.path.join(
            'file://',
            GLib.get_user_special_dir(GLib.USER_DIRECTORY_VIDEOS)),
        'command': '',
        'filename': '',

        'area': None,

        'video': True,
        'audio': 'default',
        'record_mouse': True,
        'follow_mouse': False,

        'format': 'webm',
        'codec_video': 'vp8',
        'codec_audio': 'vorbis',
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

    def copy(self) -> ConfigurationType:
        return {k: self[k] for k in self.DEFAULTS.keys()}


DEFAULTS = DefaultsConfiguration()


_FORMATS = [
    ('webm', _('WebM')),
    ('mkv', _('MKV (Matroska)'))]
# self._format_combo.append("avi", _("AVI (Audio Video Interleaved)"))
# self._format_combo.append("mp4", _("MP4 (MPEG-4 Part 14)"))
# self._format_combo.append("wmv", _("WMV (Windows Media Video)"))
# self._format_combo.append("gif", _("GIF (Graphics Interchange Format)"))
# self._format_combo.append("nut", _("NUT (NUT Recording Format)"))

FormatTestType = T.Callable[[str], bool]


def _only_with(*formats: T.List[str]) -> FormatTestType:
    return lambda fmt: fmt in formats


_AUDIO_CODECS = [
    ('opus', _('Opus'), _only_with('webm', 'mkv')),
    ('vorbis', _('Ogg Vorbis'), _only_with('webm', 'mkv')),
    ('mp3', _('MP3'), _only_with('mkv'))]
_VIDEO_CODECS = [
    ('vp8', _('VP8'), _only_with('webm', 'mkv')),
    ('vp9', _('VP9'), _only_with('webm', 'mkv')),
    ('theora', _('Ogg Theora'), _only_with('webm', 'mkv'))]


class PrefsView():

    def __init__(self, config, hide_head=False):
        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/today/sam/green-recorder/PrefsWindow.ui')
        self._config = config

        g = self._builder.get_object
        self.root = g('root_box')

        g('video').props.state = self._config['video']
        g('mouse').props.state = self._config['record_mouse']
        g('followmouse').props.state = self._config['follow_mouse']
        g('delay').props.value = self._config['delay']
        g('frames').props.value = self._config['frame_rate']
        g('audio').props.state = self._config['audio'] != 'none'
        g('filename').props.text = self._config['filename']
        g('command').props.text = self._config['command']
        g('folder').set_uri(self._config['folder'])

        self._format_combo = g('format_container')
        self._setup_container_formats()
        self._codec_audio = g('codec_audio')
        self._codec_video = g('codec_video')
        self._update_codecs()

        if hide_head:
            for name in ['record_audio', 'folder', 'filename']:
                row = g(f'{name}_row')
                row.props.visible = False
                row.props.no_show_all = True

                sep = g(f'{name}_border_bottom')
                if sep:
                    sep.props.visible = False
                    sep.props.no_show_all = True

        self._builder.connect_signals(self)

    def _setup_container_formats(self):
        for i, info in enumerate(_FORMATS):
            id_, name = info
            self._format_combo.append(id_, name)

            if i == 0:
                # Set one to active at the start so one is always active
                self._format_combo.set_active(0)

            if name == self._config['format']:
                self._format_combo.set_active(i)

    def _update_codecs(self):
        fmt = self._format_combo.get_active_id()
        self._update_codec(self._codec_audio, _AUDIO_CODECS,
                           fmt, self._config['codec_audio'])
        self._update_codec(self._codec_video, _VIDEO_CODECS,
                           fmt, self._config['codec_video'])

    def _update_codec(self, combo: Gtk.ComboBoxText, codecs: FormatTestType,
                      current_format: str, value: str):
        combo.remove_all()

        showing = [x for x in codecs if x[2](current_format)]

        for i, info in enumerate(showing):
            id_, name, test = info
            combo.append(id_, name)

            if i == 0:
                # Set one to active at the start so one is always active
                combo.set_active(0)

            if name == self._config['format']:
                combo.set_active(i)

    def handle_video_record_switch(self, switch, state):
        self._config['video'] = state

    def handle_audio_record_switch(self, switch, state):
        self._config['audio'] = 'default' if state else 'none'

    def handle_mouse_switch(self, switch, state):
        self._config['record_mouse'] = state

    def handle_follow_mouse_switch(self, switch, state):
        self._config['follow_mouse'] = state

    def handle_filename_changed(self, entry):
        self._config['filename'] = entry.props.text

    def handle_delay_changed(self, button):
        self._config['delay'] = button.props.value

    def handle_frames_changed(self, button):
        self._config['frame_rate'] = button.props.value

    def handle_command_changed(self, entry):
        self._config['command'] = entry.props.text

    def handle_folder_chosen(self, chooser):
        self._config['folder'] = chooser.get_uri()

    def handle_format_changed(self, combo):
        self._config['format'] = combo.get_active_id()
        self._update_codecs()

    def handle_codec_video_changed(self, combo):
        self._config['codec_video'] = combo.get_active_id()

    def handle_codec_audio_changed(self, combo):
        self._config['codec_audio'] = combo.get_active_id()


class PrefsWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title=_('Change Default Settings'))

        view = PrefsView(DEFAULTS).root
        view.props.margin = 18
        self.add(view)
