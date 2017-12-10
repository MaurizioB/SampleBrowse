import os, sys
from cx_Freeze import setup, Executable
parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir)
sys.path.insert(0,parent)
from samplebrowse.info import __version__

files = [
    ]
#, include_files = zip(files, files)
buildOptions = dict(packages = ['samplebrowse.utils', 'soundfile'], excludes = [], includes = ['atexit', 'soundfile', 'numpy.core._methods', 'numpy.lib.format'])
#macbuildOptions = {'iconfile': 'icons/bigglesworth_icon.icns', 'bundle_name': 'Bigglesworth'}
macbuildOptions = {}
#dmgOptions = {'applications_shortcut': True}

import sys
base = 'Win32GUI' if sys.platform=='win32' else None

executables = [
    Executable('SampleBrowse.py', base=base, icon=os.path.join(parent, 'setupscripts/icons/icon.ico'))
]
setup(name='SampleBrowse',
      version = '0.5.5',
      description = 'Audio sample browser and database',
      options = dict(build_exe = buildOptions, bdist_mac = macbuildOptions),
      executables = executables)
