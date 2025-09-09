# GCLI: AI-Powered GitHub CLI

GCLI is a command-line tool designed to streamline your GitHub workflow. It combines secure authentication via Descope with a local AI model (via Ollama) to automatically generate conventional commit messages, helping you work faster and more efficiently.

## Table of Contents

- [Why GCLI?](#why-gcli)
- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [1. Authenticate](#1-authenticate)
  - [2. Initialize a Repository](#2-initialize-a-repository)
  - [3. Commit Changes](#3-commit-changes)
  - [4. Check Status](#4-check-status)
  - [5. View Issues](#5-view-issues)
- [Contributing](#contributing)
- [License](#license)

---

## Why GCLI?

In a typical Git workflow, context-switching is common: you write code, stage files, think of a commit message, push changes, and then maybe go to GitHub to create a repository. GCLI brings all these steps into a single, unified interface.

- **Reduce Cognitive Load**: Stop thinking about the perfect commit message. Let the AI do the heavy lifting so you can stay focused on your code.
- **Enforce Consistency**: By automatically generating messages in the Conventional Commits format, GCLI helps maintain a clean and readable version history across your projects.
- **All-in-One Tool**: From repository creation to the final push, GCLI handles the entire workflow without you ever needing to leave the terminal.

---

## Features

| Feature                   | Description                                                                                             |
| ------------------------- | ------------------------------------------------------------------------------------------------------- |
| **Secure Authentication** | Log in securely using Descope with OTP or Magic Links.                                                  |
| **AI-Powered Commits**    | Automatically generate conventional commit messages from your staged changes with `gcli commit --auto`. |
| **Intelligent Fallback**  | If the local AI is unavailable, a rule-based fallback creates a sensible commit message.                |
| **Repo Management**       | Initialize local and remote GitHub repositories with a single `init` command.                           |
| **Status Dashboard**      | Get a quick overview of your authentication and repository status with `gcli status`.                   |
| **Issue Viewer**          | Quickly view open issues for any public repository directly in your terminal.                           |

---

## Installation

### Prerequisites

- Python 3.11+
- Git installed on your system.
- (Optional but recommended) Ollama installed and running for AI features.

### Steps

1.  **Clone the repository (or create the files):**
    Ensure you have the `gcli` directory, `setup.py`, and `README.md` in the same folder.

2.  **Install the package:**
    Navigate to the root directory (where `setup.py` is located) and run the following command. The `.` installs the package from the current directory in "editable" mode (`-e`), which is great for development.

    ```bash
    pip install -e .
    ```

3.  **Verify Installation:**
    You should now be able to run the `gcli` command from anywhere.
    ```bash
    gcli --help
    ```

---

## Configuration

For the AI commit feature, you need to have a local Ollama model running.

1.  **Start the Ollama server:**

    ```bash
    ollama serve
    ```

2.  **Pull a model:**
    A small, fast model is recommended for quick commit message generation.

    ```bash
    ollama pull llama3.2:1b
    ```

3.  **(Optional) Set a Preferred Model:**
    GCLI defaults to `llama3.2:1b`. To set a different preferred model, you can manually edit the config file located at `~/.github-cli/config.json`:
    ```json
    {
      "preferred_model": "your-model-name:latest"
    }
    ```

---

## Usage

### 1. Authenticate

First, link your Descope and GitHub accounts. This is a one-time setup.

```bash
gcli auth
```

Follow the on-screen prompts to authenticate via your email.

### 2. Initialize a Repository

Create a new repository on GitHub and set it as the remote for your local directory.

- **Create a public repo:**

  ```bash
  gcli init my-new-project --description "This is my awesome new project."
  ```

- **Create a private repo:**
  ```bash
  gcli init my-secret-project --private
  ```

### 3. Commit Changes

Use the `--auto` flag to generate a commit message automatically. GCLI will show you the generated message and ask for confirmation before committing.

- **Stage your files:**

  ```bash
  git add .
  ```

- **Generate a commit message and push:**
  ```bash
  gcli commit --auto
  ```

You can also provide a message manually, just like with `git commit`:

```bash
gcli commit "feat: add user login form"
```

### 4. Check Status

View your current authentication and repository status.

```bash
gcli status
```

### 5. View Issues

Check the latest issues for any public GitHub repository.

```bash
gcli issue PyGithub/PyGithub --limit 5 --label "bug"
```

---

## Contributing

Contributions are welcome! If you have suggestions for improvements or find a bug, please feel free to open an issue or submit a pull request.

1.  **Fork the Project**
2.  **Create your Feature Branch** (`git checkout -b feature/AmazingFeature`)
3.  **Commit your Changes** (`git commit -m 'feat: Add some AmazingFeature'`)
4.  **Push to the Branch** (`git push origin feature/AmazingFeature`)
5.  **Open a Pull Request**

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
