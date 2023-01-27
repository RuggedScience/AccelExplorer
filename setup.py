import distutils
import sys
from cx_Freeze import setup, Executable

name = "AccelExplorer"
icon = "./icons/icon.ico"

# str(uuid.uuid3(uuid.NAMESPACE_DNS, "accelexplorer.ruggedsci.com")).upper()
upgrade_code = "{8A7E17D0-AC31-355D-9FA5-7634479984CF}"


base = "Win32GUI" if sys.platform == "win32" else None
install_dir = (
    "ProgramFiles64Folder"
    if distutils.util.get_platform() == "win-amd64"
    else "ProgramFilesFolder"
)


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

# Used to create a "Rugged Science" folder in the Start Menu
# https://learn.microsoft.com/en-us/windows/win32/msi/directory-table
directory_table = [
    ("ProgramMenuFolder", "TARGETDIR", "."),
    ("RsProgramMenuFolder", "ProgramMenuFolder", "Rugged Science"),
]

msi_data = {"Directory": directory_table}

bdist_msi_options = {
    "data": msi_data,
    "upgrade_code": upgrade_code,
    "summary_data": {"author": "Rugged Science"},
    "initial_target_dir": f"[{install_dir}]RuggedScience\\{name}",
    "install_icon": icon,
}

executable = Executable(
    script="main.py",
    base=base,
    target_name=name,
    icon=icon,
    shortcut_name=name,
    shortcut_dir="RsProgramMenuFolder",
)

setup(
    options={
        "build_exe": build_exe_options,
        "bdist_msi": bdist_msi_options,
    },
    executables=[executable],
)
