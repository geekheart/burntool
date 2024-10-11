import struct
import time
from . import CRC
from .pymodem import ymodem_xfer
import serial
from .fwpkg import Fwpkg
import math
import logging
from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler()]
)

RESET_TIMEOUT = 10

UART_READ_TIMEOUT = 5

CMD_HANDSHAKE = 0
CMD_DOWNLOAD = 1
CMD_RST = 2

AVAIL_BAUD = [
    115200,
    230400,
    460800,
    500000,
    576000,
    921600,
    1000000,
    1152000,
    1500000,
    2000000,
]

WS63E_FLASHINFO = [
    {
        "cmd": 0xf0,
        "data": [0x00, 0xc2, 0x01, 0x00, 0x08, 0x01, 0x00, 0x00],
        "length": 8
    },
    {
        "cmd": 0xd2,
        "data": [0x00, 0x00, 0x00, 0x00,  # ADDR
                 0x00, 0x00, 0x00, 0x00,  # ILEN
                 0xFF, 0xFF, 0xFF, 0xFF,  # ERAS
                 0x00, 0xFF],  # CONST
        "length": 14
    },
    {
        "cmd": 0x87,
        "data": [0x00, 0x00],
        "length": 2
    }
]


class Ws63BurnTools:
    def __init__(self, com, baudrate) -> None:
        self.com = com
        self.baudrate = baudrate

    def set_com(self, com):
        self.com = com

    def set_baudrate(self, baudrate):
        self.baudrate = baudrate

    def ws63_send_cmddef(self, cmddef):
        total_bytes = cmddef['length'] + 10
        buf = bytearray(total_bytes+12)

        struct.pack_into('<I', buf, 0, 0xdeadbeef)

        struct.pack_into('<H', buf, 4, total_bytes)

        buf[6] = cmddef['cmd']
        buf[7] = cmddef['cmd'] ^ 0xFF

        buf[8:8 + cmddef['length']] = cmddef['data']

        crc = CRC.calc_crc16(buf[:total_bytes - 2])
        struct.pack_into('<H', buf, 8 + cmddef['length'], crc)
        logging.debug("> " + ' '.join(f'{x:02x}' for x in buf))

        written = 0
        while written < total_bytes:
            wrote = self.ser.write(buf[written:total_bytes])
            if wrote <= 0:
                raise IOError("Error while writing to fd")
            written += wrote

        logging.debug("> " + ' '.join(f'{x:02x}' for x in buf))

    def uart_read_until_magic(self):
        buf = bytearray(1024 + 12)
        MAGIC = b'\xef\xbe\xad\xde'
        i = 0
        framelen = 0
        st = 0
        t0 = time.time()

        while True:
            # Abort if timeout is reached
            if time.time() - t0 > UART_READ_TIMEOUT:
                logging.error("uart_read_until_magic: Timeout")
                return -1  # Timeout error

            try:
                # Read one byte
                len_read = self.ser.read(1)
            except serial.SerialTimeoutException:
                continue
            except serial.SerialException as e:
                logging.error(f"uart_read_until_magic: {e}")
                return -1

            if not len_read:
                continue

            # Update last valid char timer
            t0 = time.time()

            byte = len_read[0]
            buf[i] = byte

            # FSM states
            if st == 0:
                # Look for magic sequence
                if MAGIC[i] == buf[i]:
                    i += 1
                    if i >= 4:
                        st = 1
                    continue
                else:
                    i = 0

            elif st == 1:
                if i == 5:  # Bytes 4:5 define framelen
                    framelen = struct.unpack('<H', buf[4:6])[0]
                elif i == framelen - 1:  # Reached end of frame
                    break
                i += 1
                continue

        # Check CRC
        logging.debug("\n< " + ' '.join(f"{x:02x}" for x in buf[:i+1]))

        crc_received = struct.unpack('<H', buf[framelen-2:framelen])[0]
        crc_calculated = CRC.calc_crc16(buf[:framelen-2])

        if crc_received != crc_calculated:
            logging.warning("Warning: bad CRC from frame!")
            return -1

        return 0

    def flash(self, name):
        self.ser = serial.Serial(self.com, 115200, timeout=1)
        self.ser.setRTS(False)
        self.fwpkg = Fwpkg(name)
        loaderboot = None
        for bin_info in self.fwpkg.bin_infos:
            if bin_info['type'] == 0:
                loaderboot = bin_info
                break
        if not loaderboot:
            logging.error("Required loaderboot not found in fwpkg!")
            return

        # Display bin information
        self.fwpkg.show()

        # Stage 1: Flash loaderboot
        logging.info("Waiting for device reset...")
        t0 = time.time()
        while True:
            if time.time() - t0 > RESET_TIMEOUT:
                logging.warning("Timeout while waiting for device reset")
                return
            WS63E_FLASHINFO[CMD_HANDSHAKE]["data"][0:4] = self.baudrate.to_bytes(
                4, 'little')
            # Handshake with device
            self.ws63_send_cmddef(WS63E_FLASHINFO[CMD_HANDSHAKE])
            # Read response and check for ACK
            data = self.ser.read_all()
            ack = b"\xEF\xBE\xAD\xDE\x0C\x00\xE1\x1E"
            if ack in data:
                self.ser.baudrate = self.baudrate
                logging.info("Establishing ymodem session...")
                break
        time.sleep(0.5)
        # Entered YModem mode, transfer loaderboot
        logging.info(f"Transferring {loaderboot['name']}...")
        ret = ymodem_xfer(self.ser, name, loaderboot)
        if ret is False:
            logging.error(f"Error transferring {loaderboot['name']}")
            return

        self.uart_read_until_magic()

        # Stage 2: Transfer other files
        for bin_info in self.fwpkg.bin_infos:
            if bin_info['type'] != 1:
                continue
            logging.info(f"Transferring {bin_info['name']}...")
            eras_size = math.ceil(bin_info['length'] / 8192.0) * 0x2000
            WS63E_FLASHINFO[CMD_DOWNLOAD]["data"][0:4] = bin_info['burn_addr'].to_bytes(
                4, 'little')
            WS63E_FLASHINFO[CMD_DOWNLOAD]["data"][4:8] = bin_info['length'].to_bytes(
                4, 'little')
            WS63E_FLASHINFO[CMD_DOWNLOAD]["data"][8:12] = int(
                eras_size).to_bytes(4, 'little')
            self.ws63_send_cmddef(WS63E_FLASHINFO[CMD_DOWNLOAD])
            self.uart_read_until_magic()
            ret = ymodem_xfer(self.ser, name, bin_info)
            if ret is False:
                logging.error(f"Error transferring {bin_info['name']}")
                return
            time.sleep(0.1)
        logging.info("Done. Reseting device...")
        self.ws63_send_cmddef(WS63E_FLASHINFO[CMD_RST])
        self.uart_read_until_magic()
        self.ser.close()


if __name__ == "__main__":
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    tools = Ws63BurnTools("COM4", 921600)
    tools.flash("ws63-liteos-app_all_v1.10.T5.fwpkg")
