#!/usr/bin/env python

from setuptools import setup

VERSION = "2.0.35"


with open('README.rst') as f:
    LONG_DESCR = f.read()

data_files = []

setup(
    name='openscad_docsgen',
    version=VERSION,
    description='A processor to generate Markdown code documentation with images from OpenSCAD source comments.',
    long_description=LONG_DESCR,
    long_description_content_type='text/x-rst',
    author='Revar Desmera',
    author_email='revarbat@gmail.com',
    url='https://github.com/revarbat/openscad_docsgen',
    download_url='https://github.com/revarbat/openscad_docsgen/archive/refs/tags/v{}.zip'.format(VERSION),
    packages=['openscad_docsgen'],
    license='MIT License',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Manufacturing',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Topic :: Artistic Software',
        'Topic :: Multimedia :: Graphics :: 3D Modeling',
        'Topic :: Multimedia :: Graphics :: 3D Rendering',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    keywords='openscad documentation generation docsgen',
    install_requires=[
        'setuptools',
        'Pillow>=7.2.0',
        'PyYAML>=6.0',
        'openscad_runner>=1.0.12'
    ],
    data_files=data_files,
    entry_points = {
        'console_scripts': [
            'openscad-docsgen=openscad_docsgen:main',
            'openscad-mdimggen=openscad_docsgen.mdimggen:mdimggen_main',
        ],
    },
)

