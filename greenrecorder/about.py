from gi.repository import Gtk


class AboutWindow():
    def __init__(self):
        self._builder = Gtk.Builder()
        self._builder.add_from_resource('/today/sam/green-recorder/AboutWindow.ui')
        self._window = self._builder.get_object('window')

    def show(self):
        self._window.show()
