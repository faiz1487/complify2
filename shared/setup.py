from setuptools import find_packages, setup

setup(
    name="shared",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy>=2.0",
        "psycopg2-binary>=2.9",
        "redis>=5.0",
        "boto3>=1.35",
        "pydantic-settings>=2.6",
    ],
)
