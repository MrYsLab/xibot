"""
Copyright (c) 2015 Alan Yorinks All rights reserved.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU  General Public
License as published by the Free Software Foundation; either
version 3 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public
License along with this library; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
"""

import time
from tkinter import *
from tkinter import font
from tkinter import ttk

import umsgpack
import zmq
from xideco.xidekit.xidekit import XideKit


# noinspection PyMethodMayBeStatic,PyUnresolvedReferences,PyUnusedLocal
class Xitk(XideKit):
    """
    A tkinter robot controller for XideKit based robots
    """

    def __init__(self, subscribed=None, router_ip_address=None, subscriber_port='43125',
                 publisher_port='43124'):
        """
        Create the GUI and its widgets and then start up the main loop
        :param subscribed: Topics to subscribe to. Must be in a list
        :param router_ip_address: Xideco Router Ip Address
        :param subscriber_port: Xideco Router subscriber port
        :param publisher_port: Xideco Router publisher port
        """

        super().__init__(router_ip_address, subscriber_port, publisher_port)

        # subscribe to all topics specified
        if subscribed is None:
            subscribed = ['reporter']
        for x in subscribed:
            self.set_subscriber_topic(x)

        # setup root window
        self.root = Tk()
        self.root.rowconfigure(0, weight=1)
        self.root.columnconfigure(0, weight=1)

        # keep the window a fixed size
        self.root.wm_resizable(0, 0)

        self.root.title("XiBot Controller")

        # create tk variables

        # left panel variables
        self.left_motor_encoder = IntVar()
        self.left_motor_encoder.set(0)
        self.right_motor_encoder = IntVar()
        self.right_motor_encoder.set(0)

        # push button
        self.push_button = StringVar()
        self.push_button.set('Off')

        # bumper states
        self.left_bumper = StringVar()
        self.left_bumper.set('Off')

        self.right_bumper = StringVar()
        self.right_bumper.set('Off')

        # accelerometer values
        self.x_axis = StringVar()
        self.x_axis.set('0')

        self.y_axis = StringVar()
        self.y_axis.set('0')

        self.z_axis = StringVar()
        self.z_axis.set('0')

        self.axis_units = StringVar()
        self.axis_units.set('Raw')

        self.accel_bumper = StringVar()
        self.accel_bumper.set("False")

        self.accel_orientation = StringVar()
        self.accel_orientation.set("Flat")

        # center panel variables
        self.forward_speed = StringVar()
        self.forward_speed.set("0")

        self.show_forward_speed = StringVar()
        self.show_forward_speed.set("0")

        self.turn_speed = StringVar()
        self.turn_speed.set("0")

        self.show_forward_speed = StringVar()
        self.show_forward_speed.set("0")

        self.show_turn_speed = StringVar()
        self.show_turn_speed.set("0")

        # right panel variables
        self.robot_number = StringVar()
        self.robot_number.set('1')

        self.encoder_counter = IntVar()
        self.encoder_counter.set(0)

        self.line_follower_1 = IntVar()
        self.line_follower_1.set(0)

        self.line_follower_2 = IntVar()
        self.line_follower_2.set(0)

        self.line_follower_3 = IntVar()
        self.line_follower_3.set(0)

        # motor control selection and count target if using encoder count values
        self.encoder_stop_state = IntVar()
        self.encoder_stop_state.set(0)

        # stop type 0=coast, 1 = brake
        self.stop_type = StringVar()
        self.stop_type.set('coast')

        # tone parameters
        self.freq = IntVar()
        self.freq.set(1000)

        self.duration = IntVar()
        self.duration.set(500)

        # current state of the LED
        self.led_state = 0

        # create content window into which everything else is placed
        self.content = ttk.Frame(self.root, padding=12, height=480, width=640)
        self.content.grid(column=0, row=0, sticky=(N, S, E, W))
        self.content.rowconfigure(0, weight=1)

        self.content.columnconfigure(0, weight=1)
        self.content.columnconfigure(1, weight=1)

        # get all the images

        self.spin_left_image = PhotoImage(file="../xitk/images/spin_left.gif")
        self.spin_right_image = PhotoImage(file="../xitk/images/spin_right.gif")
        self.stop_image = PhotoImage(file="../xitk/images/stop3.gif")
        self.right_image = PhotoImage(file="../xitk/images/right.gif")
        self.left_image = PhotoImage(file="../xitk/images/left.gif")
        self.forward_image = PhotoImage(file="../xitk/images/forward.gif")
        self.reverse_image = PhotoImage(file="../xitk/images/reverse.gif")

        # a reference to encoder_count_spinbox in the right panel
        self.spinbox = None
        self.encoder_check_button = None

        # create the GUI content frames
        self.create_left_frame()
        self.create_center_frame()
        self.create_right_frame()

        self.spinbox.config(state=DISABLED)

        # bind the key presses

        self.root.bind("<KeyPress>", self.keyboard)
        self.root.bind("<KeyRelease>", self.stop_pressed)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.root.after(5, self.get_message)

        self.root.mainloop()

    def on_closing(self):
        """
        Destroy the window
        :return:
        """
        self.root.destroy()

    def create_left_frame(self):
        """
        Create the left panel of the GUI
        :return: 
        """
        app_highlight_font = font.Font(family='Helvetica', size=10, weight='bold')

        style = ttk.Style()
        style.configure("BW.TLabel", foreground="black", background="white")

        # create the left frame
        left_frame = ttk.Labelframe(self.content, borderwidth=5, text="Sensors")
        left_frame.grid(column=0, row=0, sticky=(N, S, E, W))

        left_frame.rowconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        left_frame.columnconfigure(0, weight=1)
        left_frame.columnconfigure(1, weight=1)

        left_underline_font = font.Font(family='Helvetica', size=10, weight='bold')

        # add the widgets

        encoder_section_label = ttk.Label(left_frame, text="Wheel Encoder Counts", font=left_underline_font)
        encoder_section_label.grid(column=0, row=0, sticky=(W, E), padx=(10, 1), pady=(0, 5))

        left_motor_label = ttk.Label(left_frame, text="Left Motor:")
        left_motor_label.grid(column=0, row=1, sticky=W, padx=(10, 1), pady=(1, 1))
        left_motor_value = ttk.Label(left_frame, width=8, textvariable=self.left_motor_encoder,
                                     relief="sunken", style="BW.TLabel")
        left_motor_value.grid(column=0, row=1, sticky=W, pady=(1, 1), padx=(105, 5))

        right_motor_label = ttk.Label(left_frame, text="Right Motor:")
        right_motor_label.grid(column=0, row=2, sticky=W, padx=(10, 1))
        right_motor_value = ttk.Label(left_frame, width=8, textvariable=self.right_motor_encoder,
                                      relief="sunken", style="BW.TLabel")
        right_motor_value.grid(column=0, row=2, sticky=W, padx=(105, 1))

        clear_counters_button = ttk.Button(left_frame, text="Reset Encoder Counters",
                                           command=self.reset_encoder_counters)
        clear_counters_button.grid(column=0, row=3, padx=10, pady=(30, 20))

        separator = ttk.Separator(left_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=4, sticky=(E, W))

        push_button_label = ttk.Label(left_frame, text="Push Button:")
        push_button_label.grid(column=0, row=5, sticky=W, padx=(10, 5), pady=(20, 20))
        push_button_value = ttk.Label(left_frame, width=8, textvariable=self.push_button,
                                      relief="sunken", style="BW.TLabel")
        push_button_value.grid(column=0, row=5, sticky=W, pady=(10, 5), padx=(105, 20))

        separator = ttk.Separator(left_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=6, sticky=(E, W))

        left_bumper_label = ttk.Label(left_frame, text="Left Bumper:")
        left_bumper_label.grid(column=0, row=7, sticky=W, padx=(10, 5), pady=(15, 10))
        left_bumper_value = ttk.Label(left_frame, width=8, textvariable=self.left_bumper,
                                      relief="sunken", style="BW.TLabel")
        left_bumper_value.grid(column=0, row=7, sticky=W, pady=(10, 5), padx=(105, 20))

        right_bumper_label = ttk.Label(left_frame, text="Right Bumper:")
        right_bumper_label.grid(column=0, row=8, sticky=W, padx=(10, 5), pady=(1, 20))
        right_bumper_value = ttk.Label(left_frame, width=8, textvariable=self.right_bumper,
                                       relief="sunken", style="BW.TLabel")
        right_bumper_value.grid(column=0, row=8, sticky=W, pady=(1, 20), padx=(105, 20))

        separator = ttk.Separator(left_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=9, sticky=(E, W))

        accelerometer_section_label = ttk.Label(left_frame, text="Accelerometer", font=left_underline_font)
        accelerometer_section_label.grid(column=0, row=10, sticky=(W, E), padx=(10, 1), pady=(5, 10))

        accel_bumper_label = ttk.Label(left_frame, text="Bumped:")
        accel_bumper_label.grid(column=0, row=11, sticky=W, padx=(10, 5), pady=(1, 5))
        accel_bumper_value = ttk.Label(left_frame, width=8, textvariable=self.accel_bumper,
                                       relief="sunken", style="BW.TLabel")
        accel_bumper_value.grid(column=0, row=11, sticky=W, pady=(1, 5), padx=(105, 10))

        accel_orientation_label = ttk.Label(left_frame, text="Orientation:")
        accel_orientation_label.grid(column=0, row=12, sticky=W, padx=(10, 5), pady=(1, 30))
        accel_orientation_value = ttk.Label(left_frame, width=8, textvariable=self.accel_orientation,
                                            relief="sunken", style="BW.TLabel")
        accel_orientation_value.grid(column=0, row=12, sticky=W, pady=(1, 30), padx=(105, 20))

        x_axis_label = ttk.Label(left_frame, text="X Axis:")
        x_axis_label.grid(column=0, row=13, sticky=W, padx=(10, 5), pady=(1, 5))
        x_axis_value = ttk.Label(left_frame, width=8, textvariable=self.x_axis,
                                 relief="sunken", style="BW.TLabel")
        x_axis_value.grid(column=0, row=13, sticky=W, pady=(1, 5), padx=(105, 20))

        y_axis_label = ttk.Label(left_frame, text="Y Axis:")
        y_axis_label.grid(column=0, row=14, sticky=W, padx=(10, 5), pady=(1, 5))
        y_axis_value = ttk.Label(left_frame, width=8, textvariable=self.y_axis,
                                 relief="sunken", style="BW.TLabel")
        y_axis_value.grid(column=0, row=14, sticky=W, pady=(1, 5), padx=(105, 20))

        z_axis_label = ttk.Label(left_frame, text="Z Axis:")
        z_axis_label.grid(column=0, row=15, sticky=W, padx=(10, 5), pady=(1, 5))
        z_axis_value = ttk.Label(left_frame, width=8, textvariable=self.z_axis,
                                 relief="sunken", style="BW.TLabel")
        z_axis_value.grid(column=0, row=15, sticky=W, pady=(1, 5), padx=(105, 20))

        axis_units_label = ttk.Label(left_frame, text="Axis Units:")
        axis_units_label.grid(column=0, row=16, sticky=W, padx=(10, 5), pady=(20, 10))
        axis_units_combo_box = ttk.Combobox(left_frame, state='readonly', textvariable=self.axis_units)
        axis_units_combo_box.grid(column=0, row=16, sticky=W, pady=(20, 10), padx=(105, 20))

        axis_units_combo_box['values'] = ('Raw', 'Gs', 'Angle')
        axis_units_combo_box.current(0)

        separator = ttk.Separator(left_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=17, sticky=(E, W))

        line_follower_label = ttk.Label(left_frame, text="  Line Followers", font=app_highlight_font)
        line_follower_label.grid(column=0, row=18, sticky=(W, E), padx=(5, 5), pady=(5, 10))

        line_follower1_label = ttk.Label(left_frame, text="Follower 1:")
        line_follower1_label.grid(column=0, row=19, sticky=W, padx=(30, 5), pady=(1, 5))

        line_follower1_value = ttk.Label(left_frame, width=8, textvariable=self.line_follower_1,
                                         relief="sunken", style="BW.TLabel")
        line_follower1_value.grid(column=0, row=19, sticky=W, pady=(1, 5), padx=(105, 20))

        line_follower2_label = ttk.Label(left_frame, text="Follower 2:")
        line_follower2_label.grid(column=0, row=20, sticky=W, padx=(30, 5), pady=(1, 5))

        line_follower2_label = ttk.Label(left_frame, width=8, textvariable=self.line_follower_2,
                                         relief="sunken", style="BW.TLabel")
        line_follower2_label.grid(column=0, row=20, sticky=W, pady=(1, 5), padx=(105, 20))

        line_follower3_label = ttk.Label(left_frame, text="Follower 3:")
        line_follower3_label.grid(column=0, row=21, sticky=W, padx=(30, 30), pady=(1, 30))
        line_follower3_label = ttk.Label(left_frame, width=8, textvariable=self.line_follower_3,
                                         relief="sunken", style="BW.TLabel")
        line_follower3_label.grid(column=0, row=21, sticky=W, pady=(1, 30), padx=(105, 20))

    def create_center_frame(self):
        """
        Create the center panel of the GUI
        :return:
        """

        # create the center frame
        center_frame = ttk.Labelframe(self.content, borderwidth=5, relief="raised", text="Robot Motion")
        center_frame.grid(column=1, row=0, sticky=(N, S, E, W))

        center_frame.rowconfigure(0, weight=1)
        center_frame.rowconfigure(1, weight=1)
        center_frame.rowconfigure(2, weight=1)
        center_frame.rowconfigure(3, weight=1)
        center_frame.rowconfigure(4, weight=1)
        center_frame.rowconfigure(5, weight=1)
        center_frame.columnconfigure(0, weight=1)
        center_frame.columnconfigure(1, weight=1)
        center_frame.columnconfigure(2, weight=1)
        center_frame.columnconfigure(3, weight=1)
        center_frame.columnconfigure(4, weight=1)
        center_frame.columnconfigure(5, weight=1)

        style = ttk.Style()
        style.configure("BW.TLabel", foreground="black", background="white")

        # create widgets
        forward_button = ttk.Button(center_frame, image=self.forward_image)
        forward_button.bind("<Button-1>", self.forward_pressed)
        forward_button.bind("<ButtonRelease-1>", self.button_released)

        reverse_button = ttk.Button(center_frame, image=self.reverse_image)
        reverse_button.bind("<Button-1>", self.reverse_pressed)
        reverse_button.bind("<ButtonRelease-1>", self.button_released)

        left_button = ttk.Button(center_frame, image=self.left_image)
        left_button.bind("<Button-1>", self.left_pressed)
        left_button.bind("<ButtonRelease-1>", self.button_released)

        right_button = ttk.Button(center_frame, image=self.right_image)
        right_button.bind("<Button-1>", self.right_pressed)
        right_button.bind("<ButtonRelease-1>", self.button_released)

        stop_button = ttk.Button(center_frame, image=self.stop_image)
        stop_button.bind("<Button-1>", self.stop_pressed)
        stop_button.bind("<ButtonRelease-1>", self.stop_pressed)

        spin_right_button = ttk.Button(center_frame, image=self.spin_right_image)
        spin_right_button.bind("<Button-1>", self.spin_right_pressed)
        spin_right_button.bind("<ButtonRelease-1>", self.button_released)

        spin_left_button = ttk.Button(center_frame, image=self.spin_left_image)
        spin_left_button.bind("<Button-1>", self.spin_left_pressed)
        spin_left_button.bind("<ButtonRelease-1>", self.button_released)

        forward_speed_scale = ttk.Scale(center_frame, orient=HORIZONTAL, length=150, from_=0.0, to=100.0,
                                        command=self.forward_scale_update, value=0, variable=self.forward_speed)
        forward_speed_label = ttk.Label(center_frame, text="Forward Speed")
        forward_speed_value = ttk.Label(center_frame, width=4, textvariable=self.show_forward_speed, style="BW.TLabel")

        turn_speed_scale = ttk.Scale(center_frame, orient=HORIZONTAL, length=150, from_=0.0, to=100.0,
                                     command=self.turn_scale_update, value=0, variable=self.turn_speed)

        turn_speed_label = ttk.Label(center_frame, text="Turning  Speed")
        turn_speed_value = ttk.Label(center_frame, width=4, textvariable=self.show_turn_speed, style="BW.TLabel")

        stop_button.grid(column=3, row=2)
        spin_right_button.grid(column=4, row=0, pady=20, padx=(2, 30))
        spin_left_button.grid(column=2, row=0, pady=10, padx=(30, 2))
        forward_button.grid(column=3, row=1, pady=40)
        reverse_button.grid(column=3, row=3, pady=(40, 40))
        left_button.grid(column=2, row=2, sticky=W, padx=(30, 1))
        right_button.grid(column=4, row=2, sticky=E, padx=(1, 30))

        forward_speed_scale.grid(column=3, row=4, pady=(1, 10), padx=10)
        forward_speed_label.grid(column=2, row=4, pady=(1, 10), sticky=E)
        forward_speed_value.grid(column=4, row=4, pady=(1, 10), padx=(5, 0), sticky=W)

        turn_speed_scale.grid(column=3, row=5, pady=(1, 60), padx=10)
        turn_speed_label.grid(column=2, row=5, pady=(1, 60), sticky=E)
        turn_speed_value.grid(column=4, row=5, pady=(1, 60), padx=(5, 0), sticky=W)

    def create_right_frame(self):
        """
        Create the right panel of the GUI
        :return:
        """

        app_highlight_font = font.Font(family='Helvetica', size=10, weight='bold')

        # create the frame
        right_frame = ttk.Labelframe(self.content, borderwidth=5, relief="raised",
                                     text="Robot Selection / Stop Control / Line Followers")
        right_frame.grid(column=2, row=0, sticky=(N, S, E, W))
        right_frame.rowconfigure(0, weight=1)

        # add the widgets

        robot_number_label = ttk.Label(right_frame, text="  Select Robot Number:", font=app_highlight_font)
        robot_number_label.grid(column=0, sticky=(N, W), padx=(10, 20), pady=10)
        robot_number1_button = ttk.Radiobutton(right_frame, text="Robot 1",
                                               variable=self.robot_number, value='1')
        robot_number1_button.grid(column=0, row=1, sticky=(N, W), padx=(30, 30), pady=(5, 30))
        robot_number2_button = ttk.Radiobutton(right_frame, text="Robot 2",
                                               variable=self.robot_number, value='2')
        robot_number2_button.grid(column=0, row=1, sticky=(N, W), padx=(110, 30), pady=(5, 30))
        robot_number3_button = ttk.Radiobutton(right_frame, text="Robot 3",
                                               variable=self.robot_number, value='3')

        robot_number3_button.grid(column=0, row=1, sticky=(N, W), padx=(190, 10), pady=(5, 30))

        separator = ttk.Separator(right_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=2, sticky=(E, W, N))

        encoder_stop_type_label = ttk.Label(right_frame, text="  Stop Type", font=app_highlight_font)
        encoder_stop_type_label.grid(column=0, row=3, sticky=(W, N), padx=(10, 60), pady=(5, 10))

        coast_radio_button = ttk.Radiobutton(right_frame, text="Coast",
                                             variable=self.stop_type, value='coast')

        coast_radio_button.grid(column=0, row=4, sticky=(W, N), padx=(70, 90))

        brake_radio_button = ttk.Radiobutton(right_frame, text="Brake",
                                             variable=self.stop_type, value='brake')
        brake_radio_button.grid(column=0, row=4, sticky=(W, N), padx=(150, 30))

        encoder_stop_option_label = ttk.Label(right_frame, text="  Stop Option", font=app_highlight_font)
        encoder_stop_option_label.grid(column=0, row=5, sticky=W, padx=(10, 60), pady=(10, 10))

        self.encoder_check_button = ttk.Checkbutton(right_frame,
                                                    text='Stop Motors On Encoder Count Of: ',
                                                    variable=self.encoder_stop_state,
                                                    onvalue=1, offvalue=0,
                                                    command=self.encoder_stop_check,
                                                    )

        self.encoder_check_button.grid(column=0, row=6, sticky=(W, E), padx=30, pady=(1, 0))

        self.spinbox = encoder_count_spinbox = Spinbox(right_frame, from_=1, to=10000,
                                                       textvariable=self.encoder_counter)

        encoder_count_spinbox.grid(column=0, row=7, sticky=(W, E, N), padx=(30, 40), pady=(0, 20))

        separator = ttk.Separator(right_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=8, sticky=(E, W))

        toggle_led_button = ttk.Button(right_frame, text="Toggle LED")
        toggle_led_button.grid(column=0, row=9, sticky=(E, W), padx=(60, 60), pady=20)
        toggle_led_button.bind("<Button-1>", self.toggle_led)

        separator = ttk.Separator(right_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=13, sticky=(E, W))

        play_tone_button = ttk.Button(right_frame, text="Play Tone")
        play_tone_button.grid(column=0, row=14, sticky=(E, W), padx=(60, 60), pady=(20, 10))

        play_tone_button.bind("<Button-1>", self.play_tone)
        # play_tone_button.bind("<ButtonRelease-1>", self.release_ignore)

        play_tone_freq_label = ttk.Label(right_frame, text="  Frequency:")
        play_tone_freq_label.grid(column=0, row=15, sticky=(W, N), padx=(60, 30))

        freq_spinbox = Spinbox(right_frame, from_=500, to=5000, textvariable=self.freq, width=5)

        freq_spinbox.grid(column=0, row=15, sticky=(W, E, N), padx=(150, 100))

        duration_label = ttk.Label(right_frame, text="  Duration:")
        duration_label.grid(column=0, row=16, sticky=W, padx=(60, 30), pady=(10, 10))

        duration_spinbox = Spinbox(right_frame, from_=500, to=5000, textvariable=self.duration, width=5)

        duration_spinbox.grid(column=0, row=16, sticky=(W, E), padx=(150, 100), pady=10)

        separator = ttk.Separator(right_frame, orient=HORIZONTAL)
        separator.grid(column=0, row=17, sticky=(E, W))

        info1 = ttk.Label(right_frame, font=app_highlight_font, text="  Keyboard Usage:")
        info1.grid(column=0, row=18, pady=(30, 0), padx=(10, 170), sticky=(W, E, N))

        info2 = ttk.Label(right_frame, font=app_highlight_font, text="  1. Arrow keys for direction.  ")
        info2.grid(column=0, row=20, pady=(5, 0), padx=30, sticky=(W, E, N))

        info3 = ttk.Label(right_frame, font=app_highlight_font, text="  2. Space Bar to stop.  ")
        info3.grid(column=0, row=21, pady=(0, 5), padx=30, sticky=(W, E, N))

        info4 = ttk.Label(right_frame, font=app_highlight_font, text="  3. 'q'  to spin left.  ")
        info4.grid(column=0, row=22, pady=(0, 5), padx=30, sticky=(W, E, N))

        info5 = ttk.Label(right_frame, font=app_highlight_font, text="  4. 'p' to spin right.  ")
        info5.grid(column=0, row=23, pady=(0, 70), padx=30, sticky=(W, E, N))

    def get_message(self):
        """
        This method is called from the tkevent loop "after" call. It will poll for new zeromq messages
        :return:
        """
        try:
            data = self.subscriber.recv_multipart(zmq.NOBLOCK)
            self.incoming_message_processing(data[0].decode(), umsgpack.unpackb(data[1]))
            time.sleep(.001)
            self.root.after(1, self.get_message)

        except zmq.error.Again:
            try:
                time.sleep(.001)
                self.root.after(1, self.get_message)

            except KeyboardInterrupt:
                self.root.destroy()
                self.publisher.close()
                self.subscriber.close()
                self.context.term()
                sys.exit(0)
        except KeyboardInterrupt:
            self.root.destroy()
            self.publisher.close()
            self.subscriber.close()
            self.context.term()
            sys.exit(0)

    def incoming_message_processing(self, topic, payload):
        """
        Process incoming messages. Currently, the only topic expected is reporter.
        If others are expected, modify this method.
        :param topic: message topic
        :param payload: message payload
        :return:
        """

        if topic == 'reporter':
            # get info_type
            info_type = payload['info_type']
            if info_type == 'left_bumper':
                self.left_bumper.set(payload['state'])
            elif info_type == 'right_bumper':
                self.right_bumper.set(payload['state'])
            elif info_type == 'push_button':
                self.push_button.set(payload['state'])
            elif info_type == 'ir1':
                self.line_follower_1.set(payload['data'])
            elif info_type == 'ir2':
                self.line_follower_2.set(payload['data'])
            elif info_type == 'ir3':
                self.line_follower_3.set(payload['data'])
            elif info_type == 'accel_axis':
                if self.axis_units.get() == 'Raw':
                    self.x_axis.set(payload['raw_x'])
                    self.y_axis.set(payload['raw_y'])
                    self.z_axis.set(payload['raw_z'])
                elif self.axis_units.get() == 'Gs':
                    self.x_axis.set(payload['xg'])
                    self.y_axis.set(payload['yg'])
                    self.z_axis.set(payload['zg'])
                else:
                    self.x_axis.set(payload['angle_x'])
                    self.y_axis.set(payload['angle_y'])
                    self.z_axis.set(payload['angle_z'])
            elif info_type == 'accel_pl':
                self.accel_orientation.set(payload['state'])
            elif info_type == 'accel_tap':
                self.accel_bumper.set(payload['state'])
            elif info_type == 'encoders':
                self.left_motor_encoder.set(self.left_motor_encoder.get() + payload['left'])
                self.right_motor_encoder.set(self.right_motor_encoder.get() + payload['right'])

                check_state = self.encoder_stop_state.get()
                # if the stop motors on ... is checked in the right panel, when the valid is achieved,
                # a stop command is sent to the robot, the spin box is disabled.

                # This is effectively a one shot and the check box needs to be selected again, which will
                # automatically set the counts to zero
                if check_state != 0:
                    stop = False
                    if self.left_motor_encoder.get() >= self.encoder_counter.get():
                        stop = True
                    if self.right_motor_encoder.get() >= self.encoder_counter.get():
                        stop = True
                    if stop:
                        message = {"command": "stop", "stop_type": self.stop_type.get()}
                        self.publish_payload(message, 'robot' + self.robot_number.get())
                        self.encoder_stop_state.set(0)
                        self.spinbox.configure(state=DISABLED)
                        self.left_motor_encoder.set(0)
                        self.right_motor_encoder.set(0)
            else:
                print('unknown info type')

    def keyboard(self, event):
        """
        Key press/release event distributor
        :param event:
        :return:
        """

        key_sym = {"Up": self.forward_pressed, "Down": self.reverse_pressed, "Right": self.right_pressed,
                   "Left": self.left_pressed, "space": self.stop_pressed, "p": self.spin_left_pressed,
                   "q": self.spin_right_pressed}

        if event.keysym in key_sym:
            command = key_sym[event.keysym]
            command(event)
        else:
            pass

    def button_released(self, event):
        """
        A gui button has been released. Send a message to stop the robot
        :return:
        """

        self.stop_pressed(event)

    def reset_encoder_counters(self):
        """
        Button press handler to reset counters
        :return:
        """
        self.left_motor_encoder.set(0)
        self.right_motor_encoder.set(0)

    def forward_pressed(self, event):
        """
        Move robot forward
        :return:
        """
        self.move(self.robot_number.get(), "forward", self.show_forward_speed.get())

    def reverse_pressed(self, event):
        """
        Move robot in reverse
        :return:
        """
        self.move(self.robot_number.get(), "reverse", self.show_forward_speed.get())

    def left_pressed(self, event):
        """
        Move robot left
        :return:
        """
        self.move(self.robot_number.get(), "left", self.show_turn_speed.get())

    def right_pressed(self, event):
        """
        Move robot right
        :return:
        """
        self.move(self.robot_number.get(), "right", self.show_turn_speed.get())

    def stop_pressed(self, event):
        """
        Stop robot
        :return:
        """
        # message = {"robot": self.robot_number.get(), "stop_type": self.stop_type.get()}
        message = {"command": "stop", "stop_type": self.stop_type.get()}

        # self.publish_payload(message, 'stop')
        self.publish_payload(message, 'robot' + self.robot_number.get())

        # print(message)

    def spin_left_pressed(self, event):
        """
        Spin robot to the left
        :return:
        """
        self.move(self.robot_number.get(), "spin_left", self.show_turn_speed.get())

    def spin_right_pressed(self, event):
        """
        Spin robot to the right
        :return:
        """
        self.move(self.robot_number.get(), "spin_right", self.show_turn_speed.get())

    def forward_scale_update(self, event):
        """
        Updates speed setting
        :param event:
        :return:
        """
        value = event.split('.')
        self.show_forward_speed.set(value[0])

    def turn_scale_update(self, event):
        """
        Updates speed setting
        :param event:
        :return:
        """
        value = event.split('.')
        self.show_turn_speed.set(value[0])

    def encoder_stop_check(self):
        check_state = self.encoder_stop_state.get()

        if check_state == 0:
            self.spinbox.configure(state=DISABLED)
        else:
            self.spinbox.configure(state=NORMAL)

            self.left_motor_encoder.set(0)
            self.right_motor_encoder.set(0)

    def play_tone(self, event):
        message = {"command": "play_tone", "freq": self.freq.get(),
                   "duration": self.duration.get()}
        self.publish_payload(message, 'robot' + self.robot_number.get())

    def toggle_led(self, event):
        if self.led_state == 0:
            self.led_state = 1
        elif self.led_state == 1:
            self.led_state = 0
        else:
            print('unknown led state')

        message = {"command": "set_led", "state": self.led_state}
        self.publish_payload(message, 'robot' + self.robot_number.get())

    def move(self, robot_id, direction, speed):
        message = {"command": "move_robot", "direction": direction, "speed": speed}
        self.publish_payload(message, 'robot' + robot_id)


if __name__ == "__main__":
    gui = Xitk()
