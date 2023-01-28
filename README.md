# AccelExplorer

AccelExplorer is a tool for exploring and creating new "views" of acceleration data.
The tool ships with some standard functions for generating FFTs, PSDs, and SRSs, but can be extended with [plugins](docs/plugins.md) to support automatic parsing of different files as well as new view and filter functions.

The latest release can be found [HERE](https://github.com/RuggedScience/AccelExplorer/releases/latest)

<img src="docs/Images/AccelExplorerScreenshot.png" alt="AccelExplorer Screenshot" width="600"/>

## Features
- Drag and Drop files.
- Drag and drop data between views. ***Views must have same underlying data type (e.g. Time or Numeric data).***
- Resample data when combining data from multiple views. ***Uses linear interpolation to create missing points.***
- Built-in functions for generating FFTs, PSDs, SRSs, and some basic filtering.
- Export generated data to CSV files.
- Rename views and series.
- Change color of individual series.
- Undo / Redo when modifying data.
- Parse many different CSV format types. ***Manual entry required for unknown format types.***
- Plugin system for expanding functionality.

