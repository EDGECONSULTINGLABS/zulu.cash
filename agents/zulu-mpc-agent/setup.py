"""Setup configuration for ZULU MPC Agent."""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding='utf-8').split('\n')
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="zulu-mpc-agent",
    version="0.1.0",
    author="Edge Consulting Labs",
    author_email="info@edgeconsultinglabs.com",
    description="Privacy-preserving voice AI agent with MPC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/edgeconsultinglabs/zulu-mpc-agent",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'zulu=cli:cli',
        ],
    },
    include_package_data=True,
    package_data={
        'agent_core': [
            'prompts/*.md',
        ],
    },
)
