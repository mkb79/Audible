from os import path
import re
from setuptools import setup, find_packages


dirname = path.abspath(path.dirname(__file__))

description = 'Interface for internal Audible API'

try:
    with open(path.join(dirname, 'README.md')) as f:
        long_description = f.read()
except:
    long_description = description

with open(path.join(dirname, 'audible/__init__.py')) as f:
    data = f.read()
version = re.search('VERSION(.*?)\((.*?)\)', data).group(2).split(", ")
version = ".".join(map(str, version))

setup(
    name='audible',
    version=version,
    packages=find_packages(exclude=["tests", "*.tests", "*.tests.*", "tests.*"]),
    description=description,
    url='https://github.com/mkb79/audible',
    license='AGPL',
    author='mkb79',
    author_email='mkb79@hackitall.de',
    classifiers=[
         'Development Status :: 3 - Alpha',
         'Intended Audience :: Developers',
         'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
         'Programming Language :: Python :: 3',
         'Programming Language :: Python :: 3.6'
    ],
    install_requires=open('requirements.txt').readlines(),
    python_requires='>=3.6',
    keywords='Audible, API',
    include_package_data=True,
    long_description=long_description,
    long_description_content_type='text/markdown',
)
