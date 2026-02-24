from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="self-improving-loop",
    version="0.1.0",
    author="Self-Improving Loop Contributors",
    author_email="maintainers@example.com",
    description="让 AI Agent 自动进化 - 完整的自我改进闭环",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yangfei222666-9/self-improving-loop",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        # 核心依赖很少，保持轻量
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "telegram": [
            # Telegram 通知是可选的
        ],
    },
    entry_points={
        "console_scripts": [
            "self-improving-loop=self_improving_loop.cli:main",
        ],
    },
    keywords="ai agent evolution self-improving rollback adaptive machine-learning",
    project_urls={
        "Bug Reports": "https://github.com/yangfei222666-9/self-improving-loop/issues",
        "Source": "https://github.com/yangfei222666-9/self-improving-loop",
        "Documentation": "https://github.com/yangfei222666-9/self-improving-loop#readme",
    },
)
