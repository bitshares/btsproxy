from setuptools import setup

setup(
    name="btsproxy",
    version="0.1",
    packages=['btsproxy'],
    include_package_data=True,
    zip_safe=True,

    install_requires=[
        'tornado>=5.0',
    ],

    entry_points={
        'console_scripts': [
            'btsproxy = btsproxy.main:main',
        ],
    },
)

