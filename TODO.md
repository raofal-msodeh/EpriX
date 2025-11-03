# 📝 EpriX To-Do List

This document outlines the planned features, enhancements, and maintenance tasks for the EpriX project.

## 🚀 Major Features

*   [ ] **Full Web UI Implementation:** Complete the web interface for all packing/unpacking options, including advanced settings (e.g., ignore patterns, compression level).
*   [ ] **Dependency Management:** Create a `requirements.txt` or `pyproject.toml` file for proper dependency tracking and installation.
*   [ ] **Package Distribution:** Prepare the project for distribution on PyPI (Python Package Index).
*   [ ] **Configuration File Support:** Implement support for a configuration file (e.g., `eprix.conf`) to store default settings.

## ✨ Enhancements

*   [ ] **Progress Bar:** Add a visual progress bar for long-running pack/unpack operations in the CLI.
*   [ ] **Detailed Logging:** Improve logging verbosity and structure for better debugging.
*   [ ] **Error Handling:** Enhance error handling and user feedback for common issues (e.g., incorrect password, corrupted file).
*   [ ] **Performance Optimization:** Benchmark and optimize the compression and encryption routines.

## 🛠️ Maintenance

*   [ ] **Unit Tests:** Write comprehensive unit tests for all core modules (`crypto.py`, `compression.py`, `pack.py`, `unpack.py`).
*   [ ] **Code Documentation:** Add docstrings to all functions and classes following a standard format (e.g., Google or NumPy style).
*   [ ] **Cleanup Backup Files:** Remove all `.backup` files from the `static` directory.

## 💡 Ideas for Future Consideration

*   [ ] Support for cloud storage integration (S3, Google Cloud Storage).
*   [ ] Multi-threading/Multi-processing support for faster operations on large datasets.
*   [ ] Integration with a key management system (KMS).
