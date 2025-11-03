# EpriX: Advanced Data Packing and Unpacking Tool

[![GitHub license](https://img.shields.io/github/license/Alqudimi/EpriX?style=for-the-badge)](LICENSE)
[![GitHub repo size](https://img.shields.io/github/repo-size/Alqudimi/EpriX?style=for-the-badge)](https://github.com/Alqudimi/EpriX)
[![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/Alqudimi/EpriX?style=for-the-badge)](https://github.com/Alqudimi/EpriX)
[![GitHub last commit](https://img.shields.io/github/last-commit/Alqudimi/EpriX?style=for-the-badge)](https://github.com/Alqudimi/EpriX/commits/main)

## 🌟 Overview

**EpriX** is a powerful and versatile Python-based tool designed for secure and efficient data packing and unpacking. It offers both a robust **Command-Line Interface (CLI)** for scripting and automation, and a **Web Interface** for easy, browser-based operations.

The core functionality includes:
*   **Multi-Layer Encryption:** Secure your data with advanced cryptographic techniques.
*   **Efficient Compression:** Reduce file size before packing.
*   **Flexible Deployment:** Use it as a standalone CLI tool or deploy the web service (likely using FastAPI, based on the project structure).

## 🚀 Features

| Feature | CLI Support | Web UI Support | Description |
| :--- | :---: | :---: | :--- |
| **Data Packing** | ✅ | ✅ | Compresses and encrypts a directory into a single package file. |
| **Data Unpacking** | ✅ | ✅ | Decrypts and decompresses a package file back into its original directory structure. |
| **Multi-Layer Crypto** | ✅ | ❌ | Utilizes advanced, multi-stage encryption for maximum security. |
| **File Detection** | ✅ | ❌ | Intelligent handling of different file types during packing/unpacking. |
| **Ignore Files** | ✅ | ❌ | Supports ignoring specific files or patterns (e.g., using a `.eprixignore` file). |

## 🛠️ Installation

### Prerequisites

*   Python 3.8+

### Using Pip (Recommended)

Since this is a project structure, the assumption is it will be packaged.

```bash
pip install eprix
```

*(Note: Replace with actual installation steps once the project is packaged and published on PyPI.)*

### From Source

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Alqudimi/EpriX.git
    cd EpriX
    ```
2.  **Install dependencies:**
    ```bash
    # Assuming dependencies are listed in a requirements.txt (to be created)
    pip install -r requirements.txt
    ```
3.  **Run the CLI:**
    ```bash
    python -m EpriX --help
    ```

## 💻 Usage

### Command-Line Interface (CLI)

The main entry point is the `EpriX` command (or `python -m EpriX`).

#### Pack a Directory

```bash
EpriX pack <source_directory> <output_file> --password <your_secret_key>
```

#### Unpack a File

```bash
EpriX unpack <package_file> <destination_directory> --password <your_secret_key>
```

### Web Interface

The project includes a web router (`router.py`) and static HTML files, suggesting a web service deployment.

1.  **Run the web server:**
    ```bash
    # This command is an assumption based on common Python web frameworks (e.g., Uvicorn for FastAPI)
    uvicorn EpriX.router:app --host 0.0.0.0 --port 8000
    ```
2.  **Access the UI:** Open your browser and navigate to `http://127.0.0.1:8000`.

## 📂 Project Structure

```
EpriX/
├── EpriX/
│   ├── __init__.py
│   ├── __main__.py          # CLI entry point
│   ├── cli.py               # Command-line interface logic
│   ├── compression.py       # Compression/decompression utilities
│   ├── crypto.py            # Multi-layer encryption/decryption logic
│   ├── filedetect.py        # File type detection
│   ├── ignore.py            # Logic for handling ignore patterns
│   ├── pack.py              # Core packing implementation
│   ├── router.py            # Web interface (FastAPI) router
│   ├── serialization.py     # Data serialization utilities
│   ├── static/              # HTML templates and static assets
│   └── unpack.py            # Core unpacking implementation
├── README.md                # This file
├── LICENSE                  # Project license file
└── CONTRIBUTING.md          # Contribution guidelines (to be created)
```

## 🤝 Contributing

We welcome contributions! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to submit bug reports, feature requests, and pull requests.

## 📜 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

| Role | Name | GitHub | Email |
| :--- | :--- | :--- | :--- |
| **Developer** | Abdulaziz Alqudimi | [![GitHub](https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white)](https://github.com/Alqudimi) | [![Email](https://img.shields.io/badge/Email-D14836?style=for-the-badge&logo=gmail&logoColor=white)](mailto:eng7mi@gmail.com) |

Project Repository: [https://github.com/Alqudimi/EpriX](https://github.com/Alqudimi/EpriX)
