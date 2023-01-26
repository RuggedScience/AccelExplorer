import sys
from cx_Freeze import setup, Executable


base = "Win32GUI" if sys.platform == "win32" else None

build_exe_options = {
    "packages": ["ebmlite"],
    "zip_include_packages": ["PySide6"],
    "include_files": [("plugins", "plugins")],
    "include_msvcr": True,
    "excludes": [
        "tkinter",
        "wheel",
        "setuptools",
    ],
}

bdist_msi_options = {
    "summary_data": {"author": "Rugged Science"},
    "initial_target_dir": "[ProgramFiles64Folder]RuggedScience\\AccelExplorer",
    "install_icon": "./icons/icon.ico",
}

accel_exe = Executable(
    script="AccelExplorer.py",
    base=base,
    target_name="AccelExplorer",
    icon="./icons/icon.ico",
    shortcut_name="AccelExplorer",
    shortcut_dir="StartMenuFolder",
)

setup(
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=[accel_exe],
)
