# setup.py - Script de instalación (opcional)
"""
Setup script para el sistema de scraping PYME Canarias
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="canarias-pyme-scraper",
    version="1.0.0",
    author="Sistema de Scraping",
    description="Sistema modular de scraping para documentación PYME en Canarias",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=[
        "beautifulsoup4==4.12.2",
        "requests==2.31.0", 
        "scrapy==2.11.0",
        "lxml==4.9.3",
        "python-dateutil==2.8.2",
        "nltk==3.8.1",
        "fake-useragent==1.4.0",
        "urllib3==2.0.7",
        "tqdm==4.66.1",
        "colorama==0.4.6",
    ],
    entry_points={
        "console_scripts": [
            "canarias-scraper=main:main",
        ],
    },
)