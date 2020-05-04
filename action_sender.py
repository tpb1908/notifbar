#!/usr/bin/env python3

import zmq
import sys


if __name__ == "__main__":
    args = sys.argv
    if len(args) != 2:
        print(f"Must provide 1 argument (integer)")
    else:
        action = args[1]
        if not action.isdigit():
            print(f"Argument must be positive integer. Found {action}")
        else:
            print(f"Digit {int(action)}")
            context = zmq.Context()
            zmq_socket = context.socket(zmq.PUSH)
            zmq_socket.bind("tcp://127.0.0.1:5557")
            zmq_socket.send_string(action)