#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='AutoBurn',
    version='0.3.0',
    author='kirto',
    author_email='sky.kirto@qq.com',
    description="A tools for Burn",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires='>=3.6',
    include_package_data=True,
    install_requires=[
        'click',
        'pyserial',
    ],
    entry_points='''
        [console_scripts]
        burn=AutoBurn.autoBurn:flash_firmware
    ''',
)
