import requests
import json
from pathlib import Path
from . import log
import logging
import click
import ipaddress

CONFIG_FILE = Path(__file__).parent/"config.json"


def validate_ip(ctx, param, value):
    if value is None:
        return value
    try:
        ip = ipaddress.ip_address(value)
        return str(ip)
    except ValueError:
        raise click.BadParameter(f'{value} is not a valid IP address')


@click.group()
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose mode.")
def cli(verbose) -> None:
    if verbose:
        log.logging_setup(level=log.logging.DEBUG)
    else:
        log.logging_setup(level=log.logging.INFO)


@cli.command()
@click.option('--ip', '-i', callback=validate_ip, default=None, help='保存远端的IP地址')
@click.option('--port', '-p', default=None, type=int, help='保存远端的端口号')
@click.option('--baud', '-b', default=None, type=int, help='保存远端串口的波特率')
@click.option('--com', '-c', default=None, type=int, help='保存远端串口的编号')
def config(ip, port, baud, com):
    config = {}
    if CONFIG_FILE.exists():
        with CONFIG_FILE.open("r") as f:
            config = json.load(f)

    if ip is not None:
        config["ip"] = ip
        logging.info(f"ip: {ip}")
    if port is not None:
        config["port"] = port
        logging.info(f"port: {port}")
    if baud is not None:
        config["baud"] = baud
        logging.info(f"baud: {baud}")
    if com is not None:
        config["com"] = com
        logging.info(f"baud: {baud}")

    logging.info(f"config: {config}")
    with CONFIG_FILE.open("w") as f:
        json.dump(config, f, indent=4)


@cli.command()
@click.argument('firmware', type=click.Path(exists=True, readable=True, dir_okay=False, file_okay=True))
@click.option('--com', '-c', default=None, type=int, help='指定烧录串口编号')
@click.option('--baud', '-b', default=None, type=int, help='指定烧录的波特率')
def flash(firmware, com, baud):
    """
    上传固件
    """
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        if 'ip' not in config or 'port' not in config:
            raise KeyError("Missing 'ip' or 'port' key in the config")
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        logging.error(f"Config error: {e}")
        return

    url = f"http://{config['ip']}:{config['port']}/upload"
    current = Path(".")/firmware
    with current.open("rb") as f:
        firmware_data = f.read()

    logging.info(f"firmware_size:{len(firmware_data)}")
    files = {'file': ('firmware.bin', firmware_data)}
    data = {}
    if com is not None:
        data['com'] = com
    elif 'com' in config:
        data['com'] = config['com']
    else:
        data['com'] = 3

    if baud is not None:
        data['baud'] = baud
    elif 'baud' in config:
        data['baud'] = config['baud']
    else:
        data['baud'] = 115200

    try:
        response = requests.post(url, files=files, data=data)
        status_code = response.status_code
        if status_code == 200:
            logging.info("Firmware data sent successfully.")
        else:
            logging.error(
                f"Failed to send firmware. Status code: {status_code}")
    except requests.RequestException as e:
        logging.error(f"HTTP request error: {e}")


if __name__ == "__main__":
    cli()
