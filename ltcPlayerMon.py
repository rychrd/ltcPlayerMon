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
    _ser_sock = None
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


def sys_reboot():
    if platform == "Windows":
        run(['shutdown', '/f', '/r', '/t', '0'])

    elif platform == "Linux":
        run(['sudo', 'shutdown', '-r', 'now'])


def kill_player():
    if platform == 'Linux':
        run(['sudo', 'killall', 'ltcVid*'])


def screen_sleep(_ser, _display):
    if _display == 'illyama':
        _ser.write(b'\xA6\x01\x00\x00\x00\x04\x01\x18\x01\xBB')

    elif _display == 'sharp':
        _ser.write(b'POWR0000\r\n')

    elif _display == 'custom' and platform == 'Linux':
        run(['vcgencmd', 'display_power', '0'])

    elif _display == 'proj':
        ser.write(b'~0000 0\r')
        print(f'sent a {message.decode()} command to {ser.port}')

    else:
        print(f"can't control screen with this OS {platform} and display combo {_display}")


def screen_wake(_serial, _display):

    if _display == 'illyama':
        _serial.write(b'\xA6\x01\x00\x00\x00\x04\x01\x18\x02\xB8')

    elif _display == 'sharp':
        _serial.write(b'POWR0001\r\n')

    elif _display == 'proj':
        ser.write(b'~0000 1\r')
        print(f'sent a {message.decode()} command to {ser.port}')

    elif _display == 'custom' and platform == 'Linux':
        run(['vcgencmd', 'display_power', '1'])

    else:
        print(f"can't control screen with this OS {platform} and screen type {_display}")


if __name__ == '__main__':

    sock, host = setup_udp()

    if platform == 'Windows':
        ser = serial.Serial('COM2', 9600)   # setup_serial('COM2')
    else:
        ser = serial.Serial('/dev/ttyAMA0', 9600)

    display = 'illyama'     # or 'sharp' or 'proj'

    try:
        while True:
            message, sender = next(udp_listen(sock))
            print(f"received message '{message.decode()}' from {sender}")

            if message == b'restart' or message == host.encode():
                sys_reboot()

            elif message == b'kill':
                kill_player()

            elif message == b'projOFF' and display == 'proj':
                ser.write(b'~0000 0\r')
                print(f'sent a {message.decode()} command to {ser.port}')

            elif message == b'projON' and display == 'proj':
                ser.write(b'~0000 1\r')
                print(f'sent a {message.decode()} command to {ser.port}')

            elif message == b'sleep':
                screen_sleep(ser, display)

            elif message == b'wake':
                screen_wake(ser, display)

            else:
                continue

    finally:

        sock.close()
        ser.flush()
        ser.close()
