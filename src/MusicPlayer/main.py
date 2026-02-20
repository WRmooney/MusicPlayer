import kivy
kivy.require('2.3.1') # replace with your current kivy version !

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.properties import NumericProperty, ReferenceListProperty, ObjectProperty
from kivy.vector import Vector
from kivy.clock import Clock
from random import randint
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button

class MusicMenu(BoxLayout):
    pass

class MusicPlayerApp(App):
    def build(self):
        return MusicMenu()


if __name__ == '__main__':
    MusicPlayerApp().run()