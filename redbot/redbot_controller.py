"""
Copyright (c) 2016 Alan Yorinks All rights reserved.

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
import asyncio
import math

from pymata_aio.constants import Constants
from pymata_aio.pymata_core import PymataCore

from .redbot_accel import RedBotAccel


# noinspection PyPep8
class RedBotController:
    pins = {"LEFT_BUMPER": 3, "RIGHT_BUMPER": 11, "BUTTON_SWITCH": 12, "BUZZER": 9, "IR_SENSOR_1": 3,
            "IR_SENSOR_2": 6, "IR_SENSOR_3": 7, "LEFT_ENCODER": 16, "RIGHT_ENCODER": 10,
            "LEFT_MOTOR_CONTROL_1": 2, "LEFT_MOTOR_CONTROL_2": 4, "LEFT_MOTOR_SPEED": 5,
            "RIGHT_MOTOR_CONTROL_1": 7, "RIGHT_MOTOR_CONTROL_2": 8, "RIGHT_MOTOR_SPEED": 6,
            "LED": 13}

    PORTRAIT_U = 0
    PORTRAIT_D = 1
    LANDSCAPE_R = 2
    LANDSCAPE_L = 3
    LOCKOUT = 0x40

    data_start = 2

    # motor control designator
    LEFT_MOTOR = 0
    RIGHT_MOTOR = 1

    # motor control command
    FORWARD = 0
    REVERSE = 1
    COAST = 2
    BRAKE = 3
    client_ready = False
    accel = None
    lbump_wait = False
    rbump_wait = False

    def __init__(self, board, robot_id=None, robot_message_handler=None):
        """
        Set up data members of this class
        :param board: pymata_core instance
        :param robot_id: robot id
        :param robot_message_handler: the instantiator (XIRB)
        """
        self.socket = None
        self.board = board
        self.accel_read_enable = False
        self.robot_id = robot_id
        self.robot_message_handler = robot_message_handler
        self.encoder_count = True

    async def init_red_board(self):
        """
        Initialize the redboard for all inputs and outputs
        :return:
        """
        await self.board.start_aio()

        # instantiate the redbot accelerometer class
        self.accel = RedBotAccel(self.board, 0x1d, 2, 0)

        #  ir sensors
        await self.board.set_pin_mode(self.pins["IR_SENSOR_1"], Constants.ANALOG, self.ir1_callback,
                                      Constants.CB_TYPE_ASYNCIO)
        await self.board.set_pin_mode(self.pins["IR_SENSOR_2"], Constants.ANALOG, self.ir2_callback,
                                      Constants.CB_TYPE_ASYNCIO)
        await self.board.set_pin_mode(self.pins["IR_SENSOR_3"], Constants.ANALOG, self.ir3_callback,
                                      Constants.CB_TYPE_ASYNCIO)

        # board LED
        await self.board.set_pin_mode(self.pins["LED"], Constants.OUTPUT)

        # motors
        await self.board.set_pin_mode(self.pins["LEFT_MOTOR_CONTROL_1"], Constants.OUTPUT)
        await self.board.set_pin_mode(self.pins["LEFT_MOTOR_CONTROL_2"], Constants.OUTPUT)
        await self.board.set_pin_mode(self.pins["RIGHT_MOTOR_CONTROL_1"], Constants.OUTPUT)
        await self.board.set_pin_mode(self.pins["RIGHT_MOTOR_CONTROL_2"], Constants.OUTPUT)

        await self.board.set_pin_mode(self.pins["LEFT_MOTOR_SPEED"], Constants.PWM)

        # set speed to zero
        await self.board.analog_write(self.pins["LEFT_MOTOR_SPEED"], 0)

        await self.board.set_pin_mode(self.pins["RIGHT_MOTOR_SPEED"], Constants.PWM)

        # set speed to zero
        await self.board.analog_write(self.pins["RIGHT_MOTOR_SPEED"], 0)

        # initialize digital inputs that require pull-ups enabled
        await self.board.set_pin_mode(self.pins["BUTTON_SWITCH"], Constants.INPUT, self.button_callback,
                                      Constants.CB_TYPE_ASYNCIO)
        await self.board.digital_write(self.pins["BUTTON_SWITCH"], 1)

        # initialize bumper pins
        await self.board.set_pin_mode(self.pins["LEFT_BUMPER"], Constants.INPUT,
                                      self.left_bumper_callback, Constants.CB_TYPE_ASYNCIO)
        await self.board.digital_write(self.pins["LEFT_BUMPER"], 1)

        await self.board.set_pin_mode(self.pins["RIGHT_BUMPER"], Constants.INPUT, self.right_bumper_callback,
                                      Constants.CB_TYPE_ASYNCIO)
        await self.board.digital_write(self.pins["RIGHT_BUMPER"], 1)
        await self.accel.start()

        # enable encoders
        await self.board.encoder_config(self.pins["LEFT_ENCODER"], self.pins["RIGHT_ENCODER"],
                                        self.encoder_callback, Constants.CB_TYPE_ASYNCIO, True)
        return True

    async def motor_control(self, motor, command, speed=None):
        """
        This is the motor controller. Controls the selected motor to move in the specified direction or to
        stop using the specified stopping method.
        :param motor: Left or right
        :param command: motion or halt
        :param speed: motor speed
        :return:
        """
        if motor == self.LEFT_MOTOR:
            if command == self.BRAKE:
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_1"], 1)
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_2"], 1)
                self.encoder_count = False
                return
            elif command == self.FORWARD:
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_1"], 1)
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_2"], 0)
                self.encoder_count = True

            elif command == self.REVERSE:  # must be
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_1"], 0)
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_2"], 1)
                self.encoder_count = True

            else:  # default is coast
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_1"], 0)
                await self.board.digital_write(self.pins["LEFT_MOTOR_CONTROL_2"], 0)
                self.encoder_count = False
                return
            # set speed for forward and reverse if specified
            if speed:
                await self.board.analog_write(self.pins["LEFT_MOTOR_SPEED"], speed)
        else:
            if command == self.BRAKE:
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_1"], 1)
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_2"], 1)
                await self.board.analog_write(self.pins["LEFT_MOTOR_SPEED"], 0)
                await self.board.analog_write(self.pins["RIGHT_MOTOR_SPEED"], 0)
                self.encoder_count = False
                return
            elif command == self.FORWARD:
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_1"], 1)
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_2"], 0)
                self.encoder_count = True

            elif command == self.REVERSE:  # must be
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_1"], 0)
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_2"], 1)
                self.encoder_count = True

            else:  # default is coast
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_1"], 0)
                await self.board.digital_write(self.pins["RIGHT_MOTOR_CONTROL_2"], 0)
                await self.board.analog_write(self.pins["LEFT_MOTOR_SPEED"], 0)
                await self.board.analog_write(self.pins["RIGHT_MOTOR_SPEED"], 0)
                self.encoder_count = False
                return
            # set speed for forward and reverse if specified
            if speed:
                await self.board.analog_write(self.pins["RIGHT_MOTOR_SPEED"], speed)

    async def get_accel_data(self):
        """
        This method polls accelerometer
        :return:
        """
        # see if data is available, and if not come back later
        avail = await self.accel.available()
        if not avail:
            return

        await self.accel.read(self.accel_axis_callback)
        await self.accel.read_portrait_landscape(self.accel_pl_callback)
        await self.accel.read_tap(self.accel_tap_callback)

    async def left_bumper_callback(self, data):
        """
        This is the callback used by pymata_core to indicate a change in the bumper state.
        :param data: data[0] = pin number and data[1] is the value
        :return:
        """
        # switch is active low

        # build  message
        if data[1] == 0:
            state = 'Bumped'
        else:
            state = 'Off'
        message = {'robot_id': self.robot_id, 'info_type': 'left_bumper', 'state': state}
        self.robot_message_handler.publish_payload(message, 'reporter')

    async def right_bumper_callback(self, data):
        """
        This is the callback used by pymata_core to indicate a change in the bumper state.
        :param data: data[0] = pin number and data[1] is the value
        :return:
        """
        # switch is active low

        # build  message
        if data[1] == 0:
            state = 'Bumped'
        else:
            state = 'Off'
        message = {'robot_id': self.robot_id, 'info_type': 'right_bumper', 'state': state}
        self.robot_message_handler.publish_payload(message, 'reporter')

    async def ir1_callback(self, data):
        """
        This is the callback used by pymata_core to indicate a change in the line follower value.
        :param data: data[0] = pin number and data[1] is the value
        :return:
         """

        # build  message

        message = {'robot_id': self.robot_id, 'info_type': 'ir1', 'data': data[1]}
        self.robot_message_handler.publish_payload(message, 'reporter')

    async def ir2_callback(self, data):
        """
        This is the callback used by pymata_core to indicate a change in the line follower value.
        :param data: data[0] = pin number and data[1] is the value
        :return:
         """
        # build  message

        message = {'robot_id': self.robot_id, 'info_type': 'ir2', 'data': data[1]}
        self.robot_message_handler.publish_payload(message, 'reporter')

    async def ir3_callback(self, data):
        """
        This is the callback used by pymata_core to indicate a change in the line follower value.
        :param data:
        :return:
        """
        # build  message

        message = {'robot_id': self.robot_id, 'info_type': 'ir3', 'data': data[1]}
        self.robot_message_handler.publish_payload(message, 'reporter')

    async def button_callback(self, data):
        """
        This is callback to indicate a change in the user button state
        :param data:
        :return:
        """
        # switch is active low

        # build  message
        if data[1] == 0:
            state = 'On'
        else:
            state = 'Off'
        message = {'robot_id': self.robot_id, 'info_type': 'push_button', 'state': state}
        self.robot_message_handler.publish_payload(message, 'reporter')

    async def play_tone(self, frequency, duration):
        """
        This the tone handler
        :param frequency: frequency in hz
        :param duration: duration in ms.
        :return:
        """
        await self.board.play_tone(self.pins["BUZZER"], Constants.TONE_TONE, frequency, duration)

    async def set_led(self, state):
        """
        Set the state of the LED on the redboard
        :param state:
        :return:
        """
        await self.board.digital_write(self.pins["LED"], state)

    async def accel_axis_callback(self, data):
        """
        This is the callback routine to retrieve the accelerometer axis data
        :param data: [x,y,z] in raw form
        :return: raw data, angle data and Gs
        """

        datax = str(float("{0:.2f}".format(data[3])))
        datay = str(float("{0:.2f}".format(data[4])))
        dataz = str(float("{0:.2f}".format(data[5])))

        x = data[0]
        y = data[1]
        z = data[2]

        angle_xz = 180 * math.atan2(x, z) / math.pi
        angle_xz = str(float("{0:.2f}".format(angle_xz)))

        angle_xy = 180 * math.atan2(x, y) / math.pi
        angle_xy = str(float("{0:.2f}".format(angle_xy)))

        angle_yz = 180 * math.atan2(y, z) / math.pi
        angle_yz = str(float("{0:.2f}".format(angle_yz)))

        x = str(data[0])
        y = str(data[1])
        z = str(data[2])

        message = {'robot_id': self.robot_id, 'info_type': 'accel_axis', "xg": datax, "yg": datay, "zg": dataz,
                   "raw_x": x, "raw_y": y, "raw_z": z,
                   "angle_x": angle_xz, "angle_y": angle_xy, "angle_z": angle_yz}

        self.robot_message_handler.publish_payload(message, 'reporter')

    async def accel_pl_callback(self, data):
        """
        Return the updated portrait/landscape orientation
        :param data: orientation value
        :return:
        """

        if data == 0x40:
            port_land = 'Flat'
        elif data == 0:
            port_land = 'Tilt Left'
        elif data == 1:
            port_land = 'Tilt Right'
        elif data == 2:
            port_land = 'Tilt Up'
        else:
            port_land = 'Tilt Down'

        message = {'robot_id': self.robot_id, 'info_type': 'accel_pl', 'state': port_land}
        self.robot_message_handler.publish_payload(message, 'reporter')

    async def accel_tap_callback(self, data):
        """
        Process the tap update.
        :param data:
        :return: True if tapped, and False if not
        """
        if data:
            message = {'robot_id': self.robot_id, 'info_type': 'accel_tap', 'state': 'True'}
            self.robot_message_handler.publish_payload(message, 'reporter')

            await asyncio.sleep(1)

            message = {'robot_id': self.robot_id, 'info_type': 'accel_tap', 'state': 'False'}
            self.robot_message_handler.publish_payload(message, 'reporter')

    async def encoder_callback(self, data):
        """
        This method returns the number of ticks from the encoders.
        :param data: data[0] = left encoder data, data[1] = right encoder data.
        :return:
        """
        if data[0] == 0 and data[1] == 0:
            pass
        else:
            if self.encoder_count:
                message = {'robot_id': self.robot_id, 'info_type': 'encoders', 'left': data[0], 'right': data[1]}
                self.robot_message_handler.publish_payload(message, 'reporter')


if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    my_core = PymataCore()

    rbc = RedBotController(my_core)
    loop.run_until_complete(rbc.init_red_board())
    asyncio.ensure_future(rbc.motor_control(0, 1, 60))
    asyncio.ensure_future(rbc.motor_control(1, 1, 60))

    while True:
        loop.run_until_complete(rbc.get_accel_data())
        loop.run_until_complete(asyncio.sleep(.1))

    loop.run_forever()
