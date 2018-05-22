"""
Implements the serial communication protocoll,
which is used by the Ligawo HDR Switch 4x1
"""


import serial
import time

# What we found so far:
#
# A packet is always 13 byes long.
#
# bytes[0:2] Something like begin packet,
# bytes[12]  Most likely a checksum
#
#  CHECK = bytes[0] + bytes[1] - SUM_2^11(bytes)
#
# seems to be it.
#

GET_SELECTED_INPUT = b'\xA5\x5B\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\xFC'
GET_SELECTED_AUDIO = b'\xA5\x5B\x01\x0C\x01\x00\x00\x00\x00\x00\x00\x00\xF2'

SELECT_INPUT_0 = b'\xA5\x5B\x02\x03\x01\x00\x01\x00\x00\x00\x00\x00\xF9'
SELECT_INPUT_1 = b'\xA5\x5B\x02\x03\x02\x00\x01\x00\x00\x00\x00\x00\xF8'
SELECT_INPUT_2 = b'\xA5\x5B\x02\x03\x03\x00\x01\x00\x00\x00\x00\x00\xF7'
SELECT_INPUT_3 = b'\xA5\x5B\x02\x03\x04\x00\x01\x00\x00\x00\x00\x00\xF6'

SELECT_AUDIO_MODE_0 = b'\xA5\x5B\x03\x02\x01\x00\x01\x00\x00\x00\x00\x00\xF9'
SELECT_AUDIO_MODE_1 = b'\xA5\x5B\x03\x02\x02\x00\x01\x00\x00\x00\x00\x00\xF8'
SELECT_AUDIO_MODE_2 = b'\xA5\x5B\x03\x02\x03\x00\x01\x00\x00\x00\x00\x00\xF7'
SELECT_AUDIO_MODE_3 = b'\xA5\x5B\x03\x02\x04\x00\x01\x00\x00\x00\x00\x00\xF6'

GET_INPUT_STATE_0 = b'\xA5\x5B\x01\x04\x01\x00\x00\x00\x00\x00\x00\x00\xFA'
GET_INPUT_STATE_1 = b'\xA5\x5B\x01\x04\x02\x00\x00\x00\x00\x00\x00\x00\xF9'
GET_INPUT_STATE_2 = b'\xA5\x5B\x01\x04\x03\x00\x00\x00\x00\x00\x00\x00\xF8'
GET_INPUT_STATE_3 = b'\xA5\x5B\x01\x04\x04\x00\x00\x00\x00\x00\x00\x00\xF7'

GET_OUTPUT_STATE = b'\xA5\x5B\x01\x05\x01\x00\x00\x00\x00\x00\x00\x00\xF9'

GET_AUTO_SWITCH_STATE = b'\xA5\x5B\x01\x0D\x00\x00\x00\x00\x00\x00\x00\x00\xF2'

SET_AUTO_SWITCH_ON = b'\xA5\x5B\x02\x05\x0F\x00\x00\x00\x00\x00\x00\x00\xEA'
SET_AUTO_SWITCH_OFF = b'\xA5\x5B\x02\x05\xF0\x00\x00\x00\x00\x00\x00\x00\x09'

# Some constants
INPUT_0 = 0
INPUT_1 = 1
INPUT_2 = 2
INPUT_3 = 3

AUDIO_MODE_AUTO = 0
AUDIO_MODE_STEREO = 1
AUDIO_MODE_5_1 = 2
AUDIO_MODE_7_1 = 3

class ChecksumError(ValueError):
    pass

def _request(conn, payload):
    """
    Query HDMI switch via serial interface.

    :param conn: A serial connection
    :type conn: serial.Serial

    :param payload: The payload bytes to transmit
    :type payload: bytes
    """
    conn.write(payload[:1])
    time.sleep(0.001)
    conn.write(payload[1:])

    return conn.read(response_len)


def _checksum(packet):
    """
    Calculate the packet's checksum

    :param packet: The packet to check
    :type packet: bytes

    :rtype: int
    """
    return packet[0] + packet[1] - sum(packet[2:12])


def _validate_packet(packet):
    """
    Check if the packet's checksum is valid

    :param packet: The packet to check
    :type packet: bytes

    :rtype: bool
    """
    if len(packet) != 13:
        return False

    return _checksum(packet) == packet[-1]


def _decode_index(packet):
    """Decode integer index value of response packet."""
    return packet[6] - 1


def _decode_bool(packet):
    """Decode boolean value"""
    return packet[6] == 0x00


def select_source(conn, source_id):
    """
    Select the input.

    :param conn: The serial connection
    :type conn: serial.Serial

    :param source_id: The HDMI input 0..3
    :type: int, 0..3
    """
    if source_id < 0 or source_id > 3:
        raise IndexError("source_id out of bounds")

    # Set the required source
    payload = [SELECT_INPUT_0,
               SELECT_INPUT_1,
               SELECT_INPUT_2,
               SELECT_INPUT_3][source_id]

    packet = _request(conn, payload)

    if not _validate_packet(packet):
        raise ChecksumError()


def get_selected_source(conn):
    """Retrieve the selected source id. Zero indexed."""
    packet = _request(conn, GET_INPUT_PAYLOAD)
    if not _validate_packet(packet):
        raise ChecksumError()

    return _decode_index(packet)


def select_audio_mode(conn, audio_mode):
    """
    Set the audio mode. You can select between
    Auto, Stereo, 5.1 and 7.1

    :param conn: The serial connection
    :type conn: serial.Serial

    :param audio_mode: The desired audio mode
    :type audio_mode: int, 0..3
    """
    if audio_mode < 0 or audio_mode > 3:
        raise IndexError("invalid audio mode; must be in 0..3")

    payload = [SELECT_AUDIO_MODE_0,
               SELECT_AUDIO_MODE_1,
               SELECT_AUDIO_MODE_2,
               SELECT_AUDIO_MODE_3][audio_mode]

    packet = _request(conn, payload)

    if not _validate_packet(packet):
        raise ChecksumError()


def get_selected_audio_mode(conn):
    """Get the selected audio mode"""
    response = _request(conn, GET_AUDIO_PAYLOAD);
    if not _validate_packet(packet):
        raise ChecksumError()

    return _decode_index(packet)


def set_auto_switch(conn, enabled):
    """Enable or disable autoswitching."""
    payload = SET_AUTO_SWITCH_OFF
    if enabled:
        payload = SET_AUTO_SWITCH_ON

    if not _validate_packet(_request(conn, payload)):
        raise ChecksumError()


def enable_auto_switch(conn):
    """Enable auto source select"""
    return set_auto_switch(conn, True)


def disable_auto_switch(conn):
    """Disable auto source select"""
    return set_auto_switch(conn, False)


def get_auto_switch_state(conn):
    """Get the current auto switch enabled / disabled state"""
    packet = _request(conn, GET_AUTO_SWITCH_STATE)
    if not _validate_packet(packet):
        raise ChecksumError()

    return _decode_bool(packet)


def get_source_connection_state(conn):
    """
    Retrieve connected state.

    :param conn: The serial connection
    :type conn: serial.Serial

    :rtype: list of bool
    """
    packets = [_request(conn, GET_INPUT_STATE_0),
               _request(conn, GET_INPUT_STATE_1),
               _request(conn, GET_INPUT_STATE_2),
               _request(conn, GET_INPUT_STATE_3)]

    validation = [_validate_packet(p) for p in packets]
    if False in validation:
        return []

    return [_decode_bool(p) for p in packets]
