# PyInstaller hook for yaml module

from PyInstaller.utils.hooks import collect_all

# Collect all yaml/PyYAML modules
datas, binaries, hiddenimports = collect_all('yaml')

# Add additional hidden imports
hiddenimports += [
    'yaml',
    'yaml.loader',
    'yaml.dumper',
    'yaml.constructor',
    'yaml.representer',
    'yaml.resolver',
    'yaml.scanner',
    'yaml.parser',
    'yaml.composer',
    'yaml.emitter',
    'yaml.serializer',
    'yaml.nodes',
    'yaml.events',
    'yaml.tokens',
    'yaml.error',
    '_yaml',
]
