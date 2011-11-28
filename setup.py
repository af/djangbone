from setuptools import setup

setup( name='djangbone',
    version = '0.0.2',
    description = 'Makes it easy for Django backends to talk to Backbone.js.',
    url = 'https://github/af/djangbone',

    author = 'Aaron Franks',
    author_email = 'aaron.franks+djangbone@gmail.com',

    keywords = ['django', 'backbone.js',],
    packages = ['djangbone',],
    classifiers = [
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
)
