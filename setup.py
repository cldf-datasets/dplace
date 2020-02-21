from setuptools import setup


setup(
    name='cldfbench_dplacetrees',
    py_modules=['cldfbench_dplacetrees'],
    include_package_data=True,
    zip_safe=False,
    entry_points={
        'cldfbench.dataset': [
            'dplacetrees=cldfbench_dplacetrees:Dataset',
        ]
    },
    install_requires=[
        'cldfbench',
        'python-nexus>=2.0.1',
    ],
    extras_require={
        'test': [
            'pytest-cldf',
        ],
    },
)
