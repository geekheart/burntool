import serial
import subprocess
import logging
import time
import os
from pathlib import Path
import threading
import serial.tools.list_ports
import serial
import queue

CONFIG_ROOT_PATH: str = Path(".")
CONFIG_BURNTOOL: str = CONFIG_ROOT_PATH / "BurnTool/BurnTool.exe"

stop_flag = threading.Event()
result_queue = queue.Queue()


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
    subprocess.run(cmd)
    logging.info("serial close")


def auto_flash_task(port_list, baudrate, bin):
    if not os.path.exists(bin):
        stop_flag.set()
        result_queue.put((False, "bin not exist"))
        return
    try:
        flash(int(port_list[1][3:]), bin, baudrate)
    except Exception as e:
        stop_flag.set()
        result_queue.put((False, e))
        return
    stop_flag.set()
    result_queue.put((True, "Success flash"))


def list_serial_ports():
    ports = serial.tools.list_ports.comports()
    com0com = []
    for port in ports:
        if "com0com" in port.description:
            com0com.append(port.device)

    return com0com


def serial_forwarding_task(port_host, port_device, baudrate):
    key_words = b'\xef\xbe\xad\xde\x12\x00\xf0\x0f'
    boot_words = b'boot.'
    reset = False
    recv_data = b""
    send_data = b""
    # 进行数据转发和 RTS 控制
    while stop_flag.is_set() is False:
        try:
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
        except Exception as e:
            stop_flag.set()
            result_queue.put((False, e))
    stop_flag.clear()


def auto_flash(com, bin, baud):
    port_list = list_serial_ports()

    try:
        port_host = serial.Serial(port_list[0], baudrate=115200, timeout=1)
    except Exception as e:
        return False, "serial open fail" + str(e)
    try:
        port_device = serial.Serial(com, baudrate=115200, timeout=1)
    except Exception as e:
        port_host.close()
        return False, "serial open fail" + str(e)

    logging.info("serial open")

    # 创建线程
    auto_flash_thread = threading.Thread(
        target=auto_flash_task, args=(port_list, baud, bin))
    serial_forwarding_thread = threading.Thread(
        target=serial_forwarding_task, args=(port_host, port_device, baud))

    # 设置守护线程
    serial_forwarding_thread.setDaemon(True)
    auto_flash_thread.setDaemon(True)

    # 启动线程
    serial_forwarding_thread.start()
    auto_flash_thread.start()
    # 等待线程结束

    result = result_queue.get(block=True)
    port_host.close()
    port_device.close()
    print(result)
    return result


if __name__ == "__main__":
    logger: logging.Logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    auto_flash("COM4", "bin/ws63-liteos-app_all-T7.fwpkg", 1000000)
