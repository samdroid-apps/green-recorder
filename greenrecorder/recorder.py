import os
import datetime
import subprocess
import time

from . import screenrecorder
from . import preferences
from . import util


DISPLAY_SERVER = os.environ.get("XDG_SESSION_TYPE", "xorg")
if "wayland" in DISPLAY_SERVER:
    DISPLAY_SERVER = "gnomewayland"
else:
    DISPLAY_SERVER = "xorg"


class RecorderException(Exception):
    pass


class Recorder():

    def __init__(self, config: preferences.ConfigurationType):
        self._config = config
        self._video_recorder = None
        self._audio_recorder = None

        filename = config['filename'] or str(datetime.datetime.now())
        extension = config['format']
        basename = os.path.join(
            util.url_to_filepath(config['folder']),
            filename)
        self._output_fp = f'{basename}.{extension}'

        time.sleep(config['delay'])

        if config['video']:
            area = config['area']
            if "xorg" in DISPLAY_SERVER:
                self._video_recorder = screenrecorder.XorgRecorder()
            elif "gnomewayland" in DISPLAY_SERVER:
                self._video_recorder = screenrecorder.GnomeRecorder()
            else:
                raise RecorderException('Display server not supported')

            self._video_recorder.start(f'{basename}.video.{extension}', config)

        if config['audio'] != 'none':
            self._audio_recorder_file = f'{basename}.audio.{extension}'
            cmd = ['ffmpeg', '-f', 'pulse',
                   '-i', config['audio'],
                   '-strict', '-2',
                   self._audio_recorder_file,
                   '-y']
            self._audio_recorder = subprocess.Popen(cmd)

    def stop(self) -> str:
        '''
        Stops the recording and returns the file path
        '''
        # FIXME: this makes me feel bad
        time.sleep(1)

        stream_files = []
        if self._video_recorder is not None:
            stream_files.append(self._video_recorder.stop())
        if self._audio_recorder is not None:
            self._audio_recorder.terminate()
            stream_files.append(self._audio_recorder_file)

        # FIXME: wait for the files to stop being written to
        time.sleep(1)

        if len(stream_files) == 1:
            os.rename(stream_files[0], self._output_fp)
        else:
            cmd = ['ffmpeg']
            for f in stream_files:
                cmd.extend(['-i', f])
            cmd += ['-c', 'copy', self._output_fp, '-y']
            subprocess.check_call(cmd)

            for f in stream_files:
                os.remove(f)

        if self._config['command']:
            subprocess.Popen([self._config['command']], shell=True)

        return self._output_fp
