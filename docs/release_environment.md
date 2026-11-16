# Analysis and release environment

The original Phase 3 environment record reports Python 3.12.6 on Windows 11, NumPy 2.5.4 for core calculations, NumPy 2.5.3 for figure generation, and Matplotlib 3.10.8 for figures. The frozen F3B requirements specify NumPy 2.5.4, pandas 2.3.3, pyDIFI 8.1.5, geomaglib 1.2.4, ppigrf 1.1.0, Matplotlib 3.10.8, and requests 2.34.2. This public summary omits local executable paths; the source `F3A_environment.json` SHA-256 remains recorded in `phase3/F3B_checksums.sha256` but that source metadata file is not redistributed because it names a private machine path.

The release validation used a clean Python 3.12 virtual environment with the exact `requirements.txt` pins. See `docs/RELEASE_REPORT.md` for test outcomes.

