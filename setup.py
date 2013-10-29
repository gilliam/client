from setuptools import setup, find_packages

setup(
    name="gilliam-cli",
    version="0.1.0",
    packages=find_packages(),
    scripts=['bin/gilliam-cli'],
    author="Johan Rydberg",
    author_email="johan.rydberg@gmail.com",
    description="Command-line client for Gilliam",
    license="Apache 2.0",
    keywords="app platform",
    url="https://github.com/gilliam/",
    install_requires=[
        'PyYAML==3.10',
        'docopt==0.6.0',
        'requests>=2.0',
        'python-dateutil==2.1',
        "gilliam-py",
        "shortuuid"
        ]
)
