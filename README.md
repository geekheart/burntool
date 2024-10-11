# WS63自动下载脚本

之前版本由于没弄清楚协议内容，导致使用官方的烧录工具和 com0com ，间接实现。

本脚本是通过解析 ws63 的烧录时序，通过 pyserial 实现烧录功能。

该脚本通过烧录器的 RTS 接到 RESET 引脚可以实现全自动烧录。

## 安装流程

1. clone 本仓库
```shell
git clone https://github.com/geekheart/burntool.git
```

2. 安装本仓库的 python 包
```shell
cd burntool
pip install .
```

## 使用教程

1. burn --help
```shell
Usage: burn [OPTIONS] FIRMWARE_FILE

  烧录ws63固件

Options:
  -v, --verbose           打印一些调试信息.
  -p, --port TEXT         指定串口号.
  -b, --baudrate INTEGER  设置串口波特率.
  -s, --show              仅展示固件信息.
  --help                  Show this message and exit.
```

2. 烧录固件 

```shell
# linux
burn XXXXX.fwpkg -p /dev/ttyUSBx
# windows
burn XXXXX.fwpkg -p COMx
```

3. 仅展示固件信息
```shell
burn XXXXX.fwpkg -s
```

## 参考资料

[https://github.com/goodspeed34/ws63flash](https://github.com/goodspeed34/ws63flash)