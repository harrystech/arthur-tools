from setuptools import find_packages, setup


setup(
    name="log_processing",
    version="1.3.0",
    author="Harry's Data Engineering and Contributors",
    license="MIT",
    url="https://github.com/harrystech/arthur-tools",
    packages=find_packages(),
    entry_points={
        "console_scripts": [
            "show_log_examples = log_processing.parse:main",
            "search_log = log_processing.compile:main",
            "config_log = log_processing.config:main",
            "upload_log = log_processing.upload:main"
        ]
    }
)
