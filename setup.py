import os
import sys
import codecs
import subprocess
from setuptools import setup

if sys.version_info < (3, 6, 0):
    raise RuntimeError("ib_insync requires Python 3.6 or higher")

here = os.path.abspath(os.path.dirname(__file__))

def git_pep440_version(path):
    def git_command(args):
        prefix = ['git', '-C', path]
        return subprocess.check_output(prefix + args).decode().strip()
    version_full = git_command(['describe', '--tags', '--dirty=.dirty'])
    version_tag = git_command(['describe', '--tags', '--abbrev=0'])
    version_tail = version_full[len(version_tag):]
    return version_tag + version_tail.replace('-', '.dev', 1).replace('-', '+', 1)

__version__ = git_pep440_version(here)

with open(os.path.join(here, 'ib_insync', 'version.py'), "w") as vf:
    print(f"__version__ = {__version__}", file=vf)

with codecs.open(os.path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='ib_insync',
    version=__version__,
    description='Python sync/async framework for Interactive Brokers API',
    long_description=long_description,
    url='https://github.com/erdewit/ib_insync',
    author='Ewald R. de Wit',
    author_email='ewald.de.wit@gmail.com',
    license='BSD',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Office/Business :: Financial :: Investment',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3 :: Only',
    ],
    keywords='ibapi tws asyncio jupyter interactive brokers async',
    packages=['ib_insync'],
    install_requires=['eventkit', 'nest_asyncio']
)
