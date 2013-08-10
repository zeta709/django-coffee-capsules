import os
from setuptools import setup

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-coffee-capsules',
    version='0.1',
    packages=['coffee_capsules'],
    include_package_data=True,
    license='BSD',
    description=('A application which helps you'
                 ' to organize a group buy of coffee capsules'
                 ' with friends or colleagues.'),
    long_description=README,
    url='',
    author='zeta709',
    author_email='zeta709@gmail.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
    ],
)
