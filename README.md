# AccelExplorer

AccelExplorer is a tool for exploring and creating "views" of acceleration data.
The tool ships with some standard functions for generating FFTs, PSDs, and SRSs, but can be extended with [plugins](docs/plugins.md) to support automatic parsing of different files as well as new view and filter functions.

The latest release can be found [HERE](https://github.com/RuggedScience/AccelExplorer/releases/latest)

<img src="docs/Images/AccelExplorerScreenshot.png" alt="AccelExplorer Screenshot" width="600"/>

## Features
- Drag and Drop files.
- Drag and drop data between views. *Views must have same underlying data type (e.g. Time or numeric data).*
- Resample data when combining data from multiple views. *Uses linear interpolation to create missing points.*
- Built-in functions for generating FFTs, PSDs, SRSs, and some basic filtering.
- Export generated data to CSV files.
- Rename views and series.
- Change color of individual series.
- Undo / Redo when modifying data.
- Parse different CSV file formats. *Manual entry required for unknown format types.*
- Plugin system for expanding functionality.

## Parsing CSVs

To automatically parse files, a plugin must be created for that specific file format. For examples on this, see [parser plugins](./plugins/parsers/).

If no plugin is found that can parse the file, the manual parser dialog will be shown asking for the below information.

<img src="docs/Images/ParserDialogScreenshot.png" alt="Parser Dialog Screenshot"/>

***NOTE:*** *Only CSV files can be parsed using the parser dialog. For any other file types a plugin MUST be created. See [endaqparser.py](./plugins/parsers/endaqparser.py) for an example.*

### Header Row
The line number within the CSV file that contains the column names or headers of the data. You can manually enter this number or click the line within the text viewer at the bottom of the dialog. After selecting a header row you will see the parsed columns on the right change to the names that were found.

### Y-Axis
The text that will be displayed for the Y-Axis on the view's chart.

### X-Axis
The column within the CSV file that contains the X-Axis data. Usually this would be the first column and would contain the time component from the accelerometer data. If there is no time component column but the sample rate is known, select "Sample Rate" and manually enter the sample rate. This will be used to generate a time component.

### Type
The type of data the X-Axis column contains. If the data is not time based, select "Number". Otherwise, select the type of time data that this column contains. 

***NOTE:*** *This box is only enabled if an [X-Axis](#x-axis) column is specified.*

### Sample Rate
The sample rate of the data. This is only required if the [X-Axis](#x-axis) is set to "Sample Rate".

### Columns
The columns that should be included in the view. Any unchecked columns will not be parsed.

## Running From Source
- Prerequisites:
    - Python 3.7 or later installed and on PATH

- Get the Code:
    ``` console
    git clone https://github.com/RuggedScience/AccelExplorer
    cd AccelExplorer
    ```
- Create virtual environment (optional):
    ```console
    python3 -m venv env
    ```
    - Activate Virtual Environment:
        - Windows (Powershell):
            ```console
            .\env\scripts\Activate.ps1
            ```
        - Windows (CMD):
            ```console
            .\env\scripts\activate.bat
            ```
        - Linux:
            ```console
            source ./env/bin/activate
            ```
- Install requirements:
    ``` console
    python3 -m pip install --upgrade pip wheel
    python3 -m pip install -r requirements.txt
    ```
- Run AccelExplorer
    ```
    python3 main.py
    ```

## Freezing to Executable
AccelExplorer can be built into an executable and installer using [cx_Freeze](https://cx-freeze.readthedocs.io/en/latest/). Currently only building to an executable or MSI has been tested and verified. cx_Freeze supports other [commands](https://cx-freeze.readthedocs.io/en/latest/setup_script.html#commands) but these have not been tested. 

Prerequisites:
- All steps in [Running From Source](#running-from-source) already completed
- Install Dependencies:
    ```console
    python3 -m pip install cx_freeze setuptools_scm
    ```
- Build Executable
    ```console
    python3 setup.py build
    ```
- Build MSI Installer
    ```console
    python3 setup.py bdist_msi
    ```