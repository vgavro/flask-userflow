from setuptools import setup, find_packages

requires = [
    'flask>=0.9',
    'itsdangerous>=0.17',
    'flask-login>=0.4',
    'flask-principal>=0.3.3',
    'bcrypt',
    'pytz',
    'ua_parser',
    'marshmallow',
    'authomatic',
    'flask_emails',
]

test_requires = [
    'pytest',
    'pytest-cov',
    'pytest-flake8',
    'flask-sqlalchemy',
]

setup(
    name='flask-userflow',
    version='0.0.1',
    description='http://github.com/vgavro/flask_userflow',
    long_description='',
    classifiers=[
        "Programming Language :: Python",
        "Framework :: Pyramid",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
    ],
    author='Victor Gavro',
    author_email='vgavro@gmail.com',
    url='http://github.com/vgavro/flask_userflow',
    keywords='',
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=requires,
    tests_require=test_requires,
    setup_requires=['pytest-runner']
)
