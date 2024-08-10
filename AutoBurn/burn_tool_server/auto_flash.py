import serial
import subprocess
import logging
import time
import os
from pathlib import Path
import threading
import serial.tools.list_ports
import serial

CONFIG_ROOT_PATH: str = Path(".")
CONFIG_BURNTOOL: str = CONFIG_ROOT_PATH / "BurnTool/BurnTool.exe"


def flash(com: int, bin: str,
          baud: int = 115200,
          times: int = 2,
          forceread: int = 10,
          erasemode: int = 0,
          timeout: int = 0,
          console: bool = False,
          clearlog: bool = False,
          onlyeraseall: bool = False,
          onlyburn: list = [],
          reset: bool = True):
    if not os.path.exists(bin):
        return
    bin = os.path.abspath(bin)
    ser = serial.Serial(
        port=f"COM{com}",  # 串口号，根据实际情况修改
        baudrate=baud,  # 波特率，根据实际情况修改
        timeout=1  # 超时时间，根据实际情况修改
    )

    try:
        if ser.isOpen():
            logging.info(f"Serial{com} port is open.")
            # 设置 RTS 为高电平
            ser.setRTS(True)
            time.sleep(1)
            logging.info("device is reset")

        else:
            logging.info("Serial port is not open.")

    finally:
        # 关闭串口
        ser.close()

    burn_tool_path = os.path.join(CONFIG_ROOT_PATH, CONFIG_BURNTOOL)
    burn_tool_path = os.path.realpath(burn_tool_path)
    cmd: list[str] = [burn_tool_path, f"-com:{com}", f"-bin:{bin}"]

    if baud != 115200:
        cmd.append(f"-signalbaud:{baud}")
    if times != 2:
        cmd.append(f"-{times}ms")
    if forceread != 10:
        cmd.append(f"-forceread:{forceread}")
    if erasemode != 0:
        cmd.append(f"-erasemode:{erasemode}")
    if timeout != 0:
        cmd.append(f"-timeout:{timeout}")
    if console:
        cmd.append("-console")
    if clearlog:
        cmd.append("-clearlog")
    if onlyeraseall:
        cmd.append("-onlyeraseall")
    if onlyburn != []:
        onlyburn = [f"-onlyburn:{i}" for i in onlyburn]
        cmd.extend(onlyburn)
    if reset:
        cmd.append("-reset")

    cmd_str: str = " ".join(cmd)
    logging.info(f"cmd:{cmd_str}")
    # 调用外部程序
    logging.info(f"cmd:{cmd}")
    output = subprocess.run(cmd)
    if output.returncode == 1:
        logging.info("Retry...")
        time.sleep(1)  # 等待一秒
        subprocess.run(cmd)

    logging.info("serial close")


def auto_flash_task(port_list, baudrate, bin):
    if not os.path.exists(bin):
        return
    flash(int(port_list[1][3:]), bin, baudrate)


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    com0com = []
    for port in ports:
        if "com0com" in port.description:
            com0com.append(port.device)

    return com0com


def serial_forwarding_task(port_list, baudrate, com):
    # 配置虚拟串口
    port_host = serial.Serial(port_list[0], baudrate=115200, timeout=1)
    port_device = serial.Serial(com, baudrate=115200, timeout=1)

    key_words = b'\xef\xbe\xad\xde\x12\x00\xf0\x0f'
    boot_words = b'boot.'
    reset = False
    recv_data = b""
    send_data = b""
    # 进行数据转发和 RTS 控制
    while True:
        if port_host.in_waiting > 0:
            send_data = port_host.read(port_host.in_waiting)
            port_device.write(send_data)
            if key_words in send_data and not reset:
                # 控制 RTS 信号
                reset = True
                print("reset")
                port_device.setRTS(True)
                time.sleep(0.5)  # 短暂保持 RTS 信号
                port_device.setRTS(False)

        if port_device.in_waiting > 0:
            if boot_words in recv_data:
                port_device.baudrate = baudrate
                port_host.baudrate = baudrate
            recv_data = port_device.read(port_device.in_waiting)
            port_host.write(recv_data)


def auto_flash(com, bin, baud):
    port_list = list_serial_ports()
    # 创建线程
    auto_flash_thread = threading.Thread(
        target=auto_flash_task, args=(port_list, baud, bin))
    serial_forwarding_thread = threading.Thread(
        target=serial_forwarding_task, args=(port_list, baud, com))

    # 设置守护线程
    auto_flash_thread.setDaemon(True)
    serial_forwarding_thread.setDaemon(True)

    # 启动线程
    auto_flash_thread.start()
    serial_forwarding_thread.start()

    # 等待线程结束
    auto_flash_thread.join()


if __name__ == "__main__":
    logger: logging.Logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    auto_flash("COM4", "bin/ws63-liteos-app_all-T7.fwpkg", 1000000)
