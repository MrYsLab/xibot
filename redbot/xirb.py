#!/usr/bin/env python3

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

import sys
import asyncio

import umsgpack
import zmq
from pymata_aio.pymata_core import PymataCore
from xideco.xidekit.xidekit import XideKit

# noinspection PyUnresolvedReferences,PyUnresolvedReferences
from redbot_controller import RedBotController


# noinspection PyPep8Naming,PyPep8,PyUnresolvedReferences
class XIRB(XideKit):
    """
    This class is the RedBot controller class
    """
    def __init__(self, **kwargs):
        """
        This method sets up all provided parameters. The default values assume that this class will be run
        on the same computer as the Xideco Router, xirt.

        Start xirt before invoking this class.
        :param kwargs: see prop_defaults below

        It creates an instance of pymata_core and an instance of the redbot controller
        """

        print('\nXiBot RedBot Controller - xirb')
        prop_defaults = {
            "subscribed": None, "robot_id": '1',
            "router_ip_address": None, "subscriber_port": '43125', "publisher_port": '43124',
            "arduino_com_port": None, "arduino_wait_time": 2, "arduino_ip_address": None,
            "arduino_ip_port": 2000, "handshake": "*HELLO*", "sleep_tune": 0.0001, "log_output": False
        }

        # setup all of the properties
        for (prop, default) in prop_defaults.items():
            setattr(self, prop, kwargs.get(prop, default))


        # initialize the XideKit parent class
        super(XIRB, self).__init__(self.router_ip_address, self.subscriber_port, self.publisher_port)

        # if not topics are provided
        if self.subscribed is None:
            self.subscribed = ['robot' + str(self.robot_id)]

        # if not the default topic, the topics are passed in as a list
        for x in self.subscribed:
            self.set_subscriber_topic(x)

        # instatiate pymata_core

        self.board = PymataCore(self.arduino_wait_time, self.sleep_tune, self.log_output,
                                self.arduino_com_port, self.arduino_ip_address,
                                self.arduino_ip_port, self.handshake)

        self.loop = asyncio.get_event_loop()

        # instantiate the low level controller
        self.rb_control = RedBotController(self.board, robot_id=self.robot_id, robot_message_handler=self)

        # run the controller
        self.loop.run_until_complete(self.rb_control.init_red_board())

    def receive_loop(self):
        """
        This is the receive loop for zmq messages. It is written as "non-asyncio" so that it can be called
        directly without having to worry about the asyncio event loop.
        :return: Never Returns
        """


        while True:
            # retrieve the next XiBot message
            next_message = self.loop.run_until_complete(self.get_next_message())

            # Process a message when returned
            if next_message:
                self.loop.run_until_complete(self.incoming_message_processing(next_message[0], next_message[1]))

            # retrieve the accelerometer data within this loop
            self.loop.run_until_complete(self.rb_control.get_accel_data())

    async def get_next_message(self):
        """
        This method uses an async future to retrieve the next message from the network.
        :return: If not message is available, None is returned, else the message is returned as a list containing
        the topic and payload.
        """
        # create an asyncio Future
        future = asyncio.Future()

        try:
            # get the next available message
            data = self.subscriber.recv_multipart(zmq.NOBLOCK)

            # get the topic and unpack the payload
            topic = data[0].decode()
            payload = umsgpack.unpackb(data[1])

            # place them into a list
            message = [topic, payload]

            # place the message in the future result
            future.set_result(message)

            # wait until the future reports that it is complete and then return the topic, payload list
            while not future.done():
                await asyncio.sleep(.01)
            return future.result()
        except zmq.error.Again:
            # if no message is available, zmq throws the Again exception, so just return None
            return None

    async def incoming_message_processing(self, topic, payload):
        """
        This is the incoming message processor. It dereferences the command field from the payload and dispatches
        the appropriate method to handle the command.
        :param topic: topic string
        :param payload: message data
        :return:
        """

        # extract the command from the payload
        command = payload['command']

        if command == 'move_robot':
            await self.do_motion(payload['direction'], payload['speed'])
        elif command == 'stop':
            await self.process_stop(payload['stop_type'])
        elif command == 'play_tone':
            await self.rb_control.play_tone(payload['freq'], payload['duration'])
        elif command == 'set_led':
            await self.rb_control.set_led(payload['state'])
        else:
            print('unknown command')
        asyncio.sleep(.01)

    async def do_motion(self, operation, speed):
        """
        Select motors to run either forward or reverse with the specified motor speed.
        :param operation: forward or reverse direction
        :param speed: motor speed
        :return:
        """

        if operation == 'forward':
            operation = self.rb_control.FORWARD
            await (self.rb_control.motor_control(self.rb_control.LEFT_MOTOR,
                                                 operation, int(speed)))
            await(self.rb_control.motor_control(self.rb_control.RIGHT_MOTOR,
                                                operation, int(speed)))

        elif operation == 'reverse':
            operation = self.rb_control.REVERSE
            await(self.rb_control.motor_control(self.rb_control.LEFT_MOTOR,
                                                operation, int(speed)))
            await(self.rb_control.motor_control(self.rb_control.RIGHT_MOTOR,
                                                operation, int(speed)))
        elif operation == 'spin_left':
            await(self.rb_control.motor_control(self.rb_control.LEFT_MOTOR,
                                                self.rb_control.FORWARD, int(speed)))
            await(self.rb_control.motor_control(self.rb_control.RIGHT_MOTOR,
                                                self.rb_control.REVERSE, int(speed)))
        elif operation == 'spin_right':
            await(self.rb_control.motor_control(self.rb_control.RIGHT_MOTOR,
                                                self.rb_control.FORWARD, int(speed)))
            await(self.rb_control.motor_control(self.rb_control.LEFT_MOTOR,
                                                self.rb_control.REVERSE, int(speed)))
        elif operation == 'left':
            await(self.rb_control.motor_control(self.rb_control.LEFT_MOTOR,
                                                self.rb_control.FORWARD, int(speed)))
        elif operation == 'right':
            await(self.rb_control.motor_control(self.rb_control.RIGHT_MOTOR,
                                                self.rb_control.FORWARD, int(speed)))
        else:
            print('unknown motion operation')
            return

    async def process_stop(self, stop_type):
        """
        Stop the motors.
        :param stop_type: Use either braking or coasting
        :return:
        """
        if stop_type == 'brake':
            await(self.rb_control.motor_control(self.rb_control.RIGHT_MOTOR,
                                                self.rb_control.BRAKE, 0))
            await(self.rb_control.motor_control(self.rb_control.LEFT_MOTOR,
                                                self.rb_control.BRAKE, 0))
        elif stop_type == 'coast':
            await(self.rb_control.motor_control(self.rb_control.RIGHT_MOTOR,
                                                self.rb_control.COAST, 0))
            await(self.rb_control.motor_control(self.rb_control.LEFT_MOTOR,
                                                self.rb_control.COAST, 0))

if __name__ == '__main__':
    my_robot = None

    if len(sys.argv) == 1:
        my_robot = XIRB()
    elif len(sys.argv) == 2:
        my_robot = XIRB(arduino_ip_address=sys.argv[1])
    elif len(sys.argv) == 3:
        my_robot = XIRB(arduino_ip_address=sys.argv[1], router_ip_address=sys.argv[2])

    my_robot.receive_loop()

