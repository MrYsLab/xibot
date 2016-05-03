#!/usr/bin/python3

import kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.garden.knob import Knob

class MainWidget(Widget):
    pass

class XibotControlApp(App):
    def build(self):
        return MainWidget()


if __name__ == '__main__':
    XibotControlApp().run()