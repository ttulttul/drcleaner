# DR Cleaner

A tool for reformatting Markdown documents to consolidate sources and generate proper APA citations using the Perplexity AI API.

## Overview

DR Cleaner scans Markdown documents for source references in the format `([Text](URL))`, extracts unique URLs, generates APA citations for each URL using the Perplexity AI API, and reformats the document with numbered references and a consolidated Sources section.

## Features

- Extracts source references from Markdown documents
- Generates APA citations using Perplexity AI
- Replaces inline references with numbered links
- Creates a consolidated Sources section
- Handles rate limiting for API calls

## Requirements

- Python 3.12 or higher
- Perplexity AI API key (required for API calls)
- python-dotenv (for loading environment variables from .env file)

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Run the setup script to create a virtual environment and install dependencies:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

## Usage

```bash
python drcleaner.py input.md output.md -k your_perplexity_api_key
```

Or set the environment variable and run:

```bash
export PERPLEXITY_API_KEY=your_perplexity_api_key
python drcleaner.py input.md output.md
```

Alternatively, you can create a `.env` file in the project root with your API key:

```
PERPLEXITY_API_KEY=your_perplexity_api_key
```

Then simply run:

```bash
python drcleaner.py input.md output.md
```

Note: The PERPLEXITY_API_KEY is required for generating APA citations. The script uses the python-dotenv package to load this key from your environment or .env file.

### Command Line Arguments

- `input_file`: Path to the input Markdown file
- `output_file`: Path to save the reformatted Markdown file
- `-k, --api-key`: Perplexity API Key (optional if PERPLEXITY_API_KEY environment variable is set)
- `-v, --verbose`: Increase output verbosity (INFO level)

## Example

Input Markdown:
```markdown
# My Document

This is a paragraph with a source reference ([Example Source](https://example.com)).

Here's another paragraph with a different source ([Another Source](https://example.org)).
```

Output Markdown:
```markdown
# My Document

This is a paragraph with a source reference [1](#source-1).

Here's another paragraph with a different source [2](#source-2).

# Sources

<a id="source-1"></a>1. Example, A. (2023). Example Source. Example.com. https://example.com

<a id="source-2"></a>2. Author, B. (2023). Another Source. Example.org. https://example.org
```

## Running Tests

To run all tests:

```bash
python tests/run_tests.py
```

To run a specific test file:

```bash
python -m unittest tests/test_drcleaner.py
python -m unittest tests/test_integration.py
```

Note: Integration tests require a valid PERPLEXITY_API_KEY to be set in your environment or .env file. Tests will be skipped if the API key is not available.

## License

[License information]
