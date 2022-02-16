#!/usr/bin/python3 env

# reboots Windows on receiving a UDP 'restart' message, or the host's name
# various commands for Sharp and Illyama monitors and Optoma projectors over RS232

# Sharp commands..- power state deep sleep
# Header    MonitorID   Category    Code0   Code1   Length  Data-Control Data[0] Data[1] Checksum
# 0xA6      0x01        0x00        0x00    0x00    0x04    0x01         0x18    0x01    0xBB
# data[0] is set power command
# data[1] is state 0x2 == ON
# checksum is XOR of all bytes except checksum
# Illyama Power OFF string \xA6\x01\x00\x00\x00\x04\x01\x18\x01\xBB
# Illyama Power ON  string \xA6\x01\x00\x00\x00\x04\x01\x18\x02\xB8
# Sharp Format c1 c2 c3 c4 p1 p2 p3 p4
# Pwer On = POWR0001 / POWR0000 + return code x0d, x0A

import socket
import serial
import platform
from subprocess import run

PORT = 44444

platform = platform.system()


def setup_udp():
    hostname = socket.gethostbyaddr('localhost')[0]
    print(f'my name is {hostname}')

    udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        udp_sock.bind(('', PORT))

    except OSError as e:
        print(f"can't bind socket to port {PORT} : {e} ..Already in use?")

    finally:

        ip, port = udp_sock.getsockname()
        print(f"listening at {hostname}, ip {ip}, port {port}")

    return udp_sock, hostname


def setup_serial(device, baud=9600):
    try:
        _ser_sock = serial.Serial(device, baud)

        if not _ser_sock.isOpen():
            _ser_sock.open()

    except serial.SerialException as e:
        print(f'something went wrong opening serial port: {e}')

    return _ser_sock


def udp_listen(udp_sock):
    try:
        msg, pt = udp_sock.recvfrom(64)
        yield msg, pt

    except OSError as err:
        print(f'error on setup - is an instance already running? {err}')
        exit()


def do_reboot():
    if platform == "Windows":
        run(['shutdown', '/f', '/r', '/t', '0'])

    elif platform == "Linux":
        run(['sudo', 'shutdown', '-r', 'now'])


def screen_sleep(_ser, _model):

    if platform == 'Windows':
        if _model == 'illyama':
            _ser.write(b'\xA6\x01\x00\x00\x00\x04\x01\x18\x01\xBB')
        elif _model == 'sharp':
            _ser.write(b'POWR0000\r\n')

    elif platform == 'Linux':
        run(['vcgencmd', 'display_power', '0'])


def screen_wake(_ser, _model):

    if platform == 'Windows':
        if _model == 'illyama':
            _ser.write(b'\xA6\x01\x00\x00\x00\x04\x01\x18\x02\xB8')
        elif _model == 'sharp':
            _ser.write(b'POWR0001\r\n')

    elif platform == 'Linux':
        run(['vcgencmd', 'display_power', '1'])


if __name__ == '__main__':

    sock, host = setup_udp()

    if platform == 'Windows':
        ser = setup_serial('COM2')
    else:
        ser = setup_serial('/dev/ttyAMA0/')

    screen_type = 'illyama'     # or 'sharp'

    try:
        while True:
            message, sender = next(udp_listen(sock))
            print(f"received message {message} from {sender}")

            if message == b'restart' or message == host.encode():
                do_reboot()

            elif message == b'projOFF':
                ser.write(b'~0000 0\r')
                print(f'sent a {message.decode()} command to {ser.port}')

            elif message == b'projON':
                ser.write(b'~0000 1\r')
                print(f'sent a {message.decode()} command to {ser.port}')

            elif message == b'sleep':
                screen_sleep(ser, screen_type)

            elif message == b'wake':
                screen_wake(ser, screen_type)

            else:
                continue

    finally:

        sock.close()
        ser.flush()
        ser.close()
