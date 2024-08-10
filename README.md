# 基于BurnTool的自动下载脚本

## 安装流程

安装本python包
```shell
pip install .
```

安装com0com。在com0com文件夹下

## 使用教程

1. 创建服务端。 windows 系统下
```shell
Usage: bts [OPTIONS]

Options:
  -v, --verbose       打开调试的log
  -p, --port INTEGER  开启服务的端口号
```

2. 配置客户端。linux 系统下
wsl用户使用ip为127.0.0.1。 
```shell
Usage: btc config [OPTIONS]

Options:
  -i, --ip TEXT       保存远端的IP地址
  -p, --port INTEGER  保存远端的端口号
  -b, --baud INTEGER  保存远端串口的波特率
  -c, --com INTEGER   保存远端串口的编号
```

3. 烧录固件。linux 系统下

```shell
Usage: btc flash [OPTIONS] FIRMWARE

  上传固件

Options:
  -c, --com INTEGER   指定烧录串口编号
  -b, --baud INTEGER  指定烧录的波特率

```

