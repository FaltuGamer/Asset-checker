# Asset Checker

A lightweight tool for checking linked material and texture dependencies in 3D assets.

## Requirements

- Python 3
- Tkinter for the graphical interface (included with most Windows Python installations)

No third-party Python packages are required.

## Graphical interface

Run:

```powershell
python asset_checker_gui.py
```

Choose a folder containing assets, then select **Run Scan**.

## Command line

Scan the current directory:

```powershell
python asset_checker.py
```

Or specify a directory:

```powershell
python asset_checker.py "C:\path\to\assets"
```

The checker scans `.obj` and `.gltf` files, follows OBJ material-library references, and checks referenced texture files. `House.fbx` is included as a sample asset but is not scanned by the checker.
