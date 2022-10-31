# Jigsaw Dataset

<p align="center"><img src="splash.png"></p>

## Requirements
- [Blender 3.3+](https://www.blender.org/)
- A Python installation is **NOT** required as there is a version embedded within Blender

## Usage

To execute the script, replace `blender` with the path to your `blender.exe` in your Blender installation in the following command. If you do not wish, or cannot, install Blender with your current setup, Blender portable works just as well.

`blender Jigsaw.blend --background --python generate.py`

Alternatively, you may want to edit the `run.sh` script provided to point to your Blender path.

The script will output files relative to the current working directory (where the command was executed from) so please ensure there is appropriate disk space and permissions.
