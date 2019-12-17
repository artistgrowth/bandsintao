import os
import re

from setuptools import setup

NAME = "bandsintao"


def requirements(filename):
    try:
        from pip.req import parse_requirements
    except ImportError:
        # Handle newer versions of pip >= 10, they moved this function completely
        from pip._internal.req import parse_requirements
    requirement_file = os.path.join(os.getcwd(), "requirements", filename)
    # Each object returned from `parse_requirements` will have a `Requirment` property
    # whose string representation will be in the format needed to articulate requirements within
    # requirements.txt files, e.g. 'beautifulsoup4==4.5.1', 'requests>=2.7.0,<3.0'
    return [str(r.req) for r in parse_requirements(requirement_file, session=False)]


if os.path.exists("README.md"):
    with open("README.md") as f:
        long_description = f.read()
else:
    long_description = "See http://pypi.python.org/pypi/{}".format(NAME)

regex = re.compile(r"^__(\w+)__\s*=\s*\"(.+)\"$", re.IGNORECASE)

meta = {}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), "{}/__init__.py".format(NAME))) as fh:
    for line in fh:
        line = line.strip()
        match = regex.match(line)
        if match:
            meta.update((match.groups(),))

setup(
    name=NAME,
    version=meta["version"],
    url=meta["homepage"],
    author=meta["author"],
    author_email=meta["contact"],
    description="Python client library to consume the Bandsintown API",
    long_description=long_description,
    keywords="Bandsintown performance concerts music " + meta["author"],
    license="MIT",
    packages=[
        NAME,
    ],
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Other/Nonlisted Topic",
    ],
    install_requires=requirements("default.txt"),
    test_suite="nose.collector",
    tests_require=requirements("test.txt"),
)
