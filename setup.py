from cx_Freeze import setup, Executable

build_exe_options = {
    "bin_includes": [
        "libssl.so",
        "libz.so"
    ],
    "bin_path_includes": [
         "/usr/lib/x86_64-linux-gnu"
    ],
    "include_files": [
        ("client/dist", "client"),
        "LICENSE",
        "templates",
        "readme.md"
    ],
    "packages": [
        "appdirs",
        "asyncio",
        "bcrypt",
        "cffi",
        "idna",
        "gzip",
        "motor",
        "numpy",
        "packaging",
        "uvloop",
        "ssl"
    ]
}

options = {
    "build_exe": build_exe_options
}

executables = [
    Executable('run.py', base="Console")
]

classifiers=[
    "Programming Language :: Python :: 3.6",
    "Programming Language :: Python :: 3.7"
]

setup(name="virtool", executables=executables, options=options, classifiers=classifiers)
