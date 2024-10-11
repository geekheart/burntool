import time
import struct
from . import CRC
import logging
from rich.progress import Progress

YMODEM_C_TIMEOUT = 5
YMODEM_ACK_TIMEOUT = 1.5
YMODEM_XMIT_TIMEOUT = 30

# Control Characters
SOH = 0x01
STX = 0x02
EOT = 0x04
ACK = 0x06
NAK = 0x15
C = ord('C')


def ymodem_wait_ack(serial_port):
    t0 = time.time()
    while True:
        if time.time() - t0 > YMODEM_ACK_TIMEOUT:
            return False  # Timeout
        if serial_port.in_waiting > 0:
            cc = serial_port.read(1)
            # time.sleep(0.01)
            if cc == bytes([ACK]):
                return True
            if cc == bytes([NAK]):
                return False


def ymodem_blk_timed_xmit(serial_port, blk):
    t0 = time.time()
    while time.time() - t0 < YMODEM_XMIT_TIMEOUT:
        serial_port.write(blk)
        ret = ymodem_wait_ack(serial_port)
        if ret is True:
            return True
    return False


def ymodem_xfer(serial_port, file_path, loaderboot):
    file_size = loaderboot['length']
    file_name = loaderboot['name']
    offset = loaderboot['offset']
    total_blk = (file_size + 1023) // 1024
    last_blk = file_size % 1024 if file_size % 1024 else 1024

    # Waiting for C
    t0 = time.time()
    while True:
        if serial_port.in_waiting > 0:
            cc = serial_port.read(1)
            if cc == bytes([C]):
                break
        if time.time() - t0 > YMODEM_C_TIMEOUT:
            return False  # Timeout

    logging.debug(f"Xfer {file_name} ({file_size} B, {total_blk} BLK)")

    # Block 0: File Info
    blkbuf = bytearray(133)
    blkbuf[0] = SOH
    blkbuf[1] = 0x00
    blkbuf[2] = 0xff
    blkbuf[3:3+len(file_name)] = file_name.encode()
    blkbuf[3+len(file_name)+1:3+len(file_name)+1 +
           len(hex(file_size))] = hex(file_size).encode()

    crc = CRC.calc_crc16(blkbuf[3:131])
    blkbuf[131:133] = struct.pack('>H', crc)

    ret = ymodem_blk_timed_xmit(serial_port, blkbuf)
    if ret is False:
        return False

    # Data Blocks: File Data
    with open(file_path, 'rb') as f, Progress() as progress:
        task = progress.add_task("[green]Transferring...", total=total_blk)
        f.seek(offset)
        for i_blk in range(1, total_blk + 1):
            blkbuf = bytearray(1029)
            blkbuf[0] = STX
            blkbuf[1] = i_blk % 0x100
            blkbuf[2] = 0xff - blkbuf[1]
            rlen = last_blk if i_blk == total_blk else 1024
            blkbuf[3:3+rlen] = f.read(rlen)

            crc = CRC.calc_crc16(blkbuf[3:1027])
            blkbuf[1027:1029] = struct.pack('>H', crc)

            ret = ymodem_blk_timed_xmit(serial_port, blkbuf)
            if ret is False:
                return False
            progress.update(task, advance=1)
    # EOT
    serial_port.write(bytes([EOT]))
    while ymodem_wait_ack(serial_port) is False:
        serial_port.write(bytes([EOT]))

    # Block 0: Finish Xmit
    blkbuf = bytearray(133)
    blkbuf[0] = SOH
    blkbuf[1] = 0x00
    blkbuf[2] = 0xff
    crc = CRC.calc_crc16(blkbuf[3:131])
    blkbuf[131:133] = struct.pack('>H', crc)
    ret = ymodem_blk_timed_xmit(serial_port, blkbuf)
    if ret is False:
        return False
    return True
