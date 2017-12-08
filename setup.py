#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from os import path
from setuptools import setup, find_packages
#from src.info import __version__, __codeurl__

_path = path.abspath(path.dirname(__file__))
with open(path.join(_path, 'README.rst')) as f:
    long_desc = f.read()

info = {}
with open(path.join(_path, 'samplebrowse/info.py')) as f:
    exec(f.read(), info)


setup(
    name="SampleBrowse",
    version=info['__version__'],
    description="SampleBrowse is an audio sample browser and manager",
    long_description=long_desc, 
    author="Maurizio Berti",
    author_email="maurizio.berti@gmail.com",
    url=info["__codeurl__"],
    classifiers=[
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Development Status :: 4 - Beta",
        "Environment :: X11 Applications :: Qt",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python",
        "Topic :: Utilities"
    ],
    packages=['samplebrowse'],
    include_package_data=True, 
    scripts=[
        "SampleBrowse", 
#        "SampleBrowse.py", 
    ],
)
