Conda environment for Backend-niceGUI

Create the environment (Windows PowerShell):

```powershell
conda env create -f environment.yml
conda activate backend-nicegui
```

Or using `mamba` if installed:

```powershell
mamba env create -f environment.yml
mamba activate backend-nicegui
```

Run the app (example):

```powershell
python main.py
```

If VS Code doesn't auto-detect the interpreter, open the Command Palette and select `Python: Select Interpreter`, then choose `backend-nicegui`.
