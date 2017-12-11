import os, sys, site, shutil
from cx_Freeze import setup, Executable
parent = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.path.pardir)
sys.path.insert(0,parent)
from samplebrowsesrc.info import __version__

files = [
    ]
#, include_files = zip(files, files)
buildOptions = dict(packages = ['samplebrowsesrc.utils', 'soundfile'], excludes = [], includes = ['atexit', 'soundfile', 'numpy.core._methods', 'numpy.lib.format'])
#macbuildOptions = {'iconfile': 'icons/bigglesworth_icon.icns', 'bundle_name': 'Bigglesworth'}
macbuildOptions = {}
#dmgOptions = {'applications_shortcut': True}

import sys
base = 'Win32GUI' if sys.platform=='win32' else None
#print(os.path.join(parent, 'setupscripts/icons/icon.ico'))
executables = [
    Executable(script='SampleBrowse.py', base=base, icon='setupscripts/icons/icon.ico'),
    Executable(script='SampleBrowse.py', targetName='SampleBrowseDebug.exe', base=None, icon='setupscripts/icons/icon.ico')
]

setup(name='samplebrowsesrc',
      version = __version__,
      description = 'Audio sample browser and database',
      options = dict(build_exe = buildOptions, bdist_mac = macbuildOptions),
      executables = executables)

pyver = sys.version_info
buildDir = 'build/exe.win32-{}.{}/'.format(pyver.major, pyver.minor)
for p in site.getsitepackages():
    if os.path.isfile(os.path.join(p, 'soundfile.py')):
        break
else:
    print('PySoundFile module not found?')
    exit()

try:
    if not os.path.isfile(os.path.join(buildDir, 'soundfile.py')):
        shutil.copy(os.path.join(p, 'soundfile.py'), buildDir)
    if not os.path.isdir(os.path.join(buildDir, '_soundfile_data')):
        shutil.copytree(os.path.join(p, '_soundfile_data'), os.path.join(buildDir, '_soundfile_data'))
except Exception as e:
    print('Problem copying soundfile dependencies:', e)
