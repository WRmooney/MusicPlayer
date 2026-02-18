import kivy
kivy.require('2.3.1') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget


class MusicMenu(Widget):
    pass


class MusicPlayerApp(App):
    def build(self):
        return MusicMenu()


if __name__ == '__main__':
    MusicPlayerApp().run()