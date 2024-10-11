import logging
import click

from .ws63flash import Ws63BurnTools
from .fwpkg import Fwpkg


@click.command()
@click.option('--verbose', '-v', is_flag=True, default=False, help='打印一些调试信息.')
@click.option('--port', '-p', type=str, default="", help='指定串口号.')
@click.option('--baudrate', '-b', default=921600, type=int, help='设置串口波特率.')
@click.option('--show', '-s', is_flag=True, default=False, help='仅展示固件信息.')
@click.argument('firmware_file', type=click.Path(exists=True), required=True)
def flash_firmware(verbose, port, baudrate, show, firmware_file):
    """
    烧录ws63固件
    """
    # 配置日志
    logger = logging.getLogger()
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # 烧录工具
    if show:
        fwpkg = Fwpkg(firmware_file)
        fwpkg.show()
    else:
        if port:
            tools = Ws63BurnTools(port, baudrate)
            tools.flash(firmware_file)
        else:
            logger.error("Please specify a serial port with -p or --port")


if __name__ == "__main__":
    flash_firmware()
