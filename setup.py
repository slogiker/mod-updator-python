from setuptools import setup, find_packages

setup(
    name="minecraft-mod-updater",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "requests>=2.28.0",
    ],
    entry_points={
        "console_scripts": [
            "update-mod=mod_updater.cli:main",
        ],
    },
)
