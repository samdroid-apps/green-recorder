project('green-recorder', 'c')

app_data_dir = join_paths([get_option('datadir'), 'green-recorder'])

subdir('po')
subdir('data')

py3_mod = import('python3')
py3 = py3_mod.find_python()

py3_version = py3_mod.language_version()
# Required for type annotations
if py3_version.version_compare('< 3.5')
  error('Python 3.5+ is required')
endif

# Get the python sitepackages directory with this dodgy thing
r = run_command(py3, '-c', 'from distutils.sysconfig import get_python_lib; print(get_python_lib())')
if r.returncode() != 0
    error('Cannot find python install dir')
endif
python_dir = r.stdout().strip()
install_subdir('greenrecorder', install_dir: python_dir)

conf_data = configuration_data()
conf_data.set(
    'RESOURCE_PATH',
    join_paths([
        get_option('prefix'),
        app_data_dir,
        'today.sam.green-recorder.gresource',
    ]))
configure_file(input : 'green-recorder.in',
               output : 'green-recorder',
               install_dir : 'bin',
               configuration : conf_data)
