import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name="sumo",
    version="0.1",
    author="Robert Kovacs",
    author_email="robert@dynamita.com",
    description=("Sumo Python interface."),
    license="Proprietary",
    keywords="Dynamita Sumo simulation",
    url="http://dynamita.com",
    packages=find_packages(),
    long_description=read('README'),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "License :: Proprietary",
    ],
)
