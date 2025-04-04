import re
import google.generativeai as genai
import os
import argparse
import time
from collections import OrderedDict

# --- Configuration ---
GEMINI_MODEL_NAME = "gemini-1.5-pro-latest"  # Or specific model like "gemini-2.5-pro" when available
API_REQUEST_DELAY = 1  # Seconds to wait between API calls (adjust if needed for rate limits)
APA_PROMPT_TEMPLATE = "Visit this web link and generate an appropriate APA style reference line for it in markdown format: {}"
SOURCE_PATTERN = re.compile(r'\(\[([^\]]+)\]\(([^\)]+)\)\)') # Pattern: ([Display Text](URL))

# --- Helper Functions ---

def configure_gemini(api_key):
    """Configures the Gemini API client."""
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(GEMINI_MODEL_NAME)
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")
        return None

def get_apa_citation(model, url):
    """Calls Gemini API to get an APA citation for a URL."""
    if not model:
        return "[Gemini API not configured]"
    prompt = APA_PROMPT_TEMPLATE.format(url)
    print(f"  Generating APA for: {url[:60]}...")
    try:
        # Configuration for web page access (if needed by the model/API)
        # Note: As of late 2023/early 2024, direct web browsing might be implicit
        # or require specific tools/function calling setup depending on the API version.
        # This basic call assumes the model can access the URL based on the prompt.
        safety_settings = [ # Adjust safety settings if needed
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        ]

        response = model.generate_content(
            prompt,
            safety_settings=safety_settings
            # Add generation_config or tool_config if needed for web browsing
            )

        # Handle potential blocks or errors in response
        if response.parts:
             citation = response.text.strip()
             # Basic cleanup: remove potential markdown list markers if Gemini adds them
             if citation.startswith(("- ", "* ")):
                 citation = citation[2:]
             if citation and citation[0].isdigit() and citation[1] == '.' and citation[2] == ' ':
                 citation = citation[3:] # Remove "1. " style numbering if present
             return citation
        elif response.prompt_feedback and response.prompt_feedback.block_reason:
             print(f"    WARN: Citation generation blocked for {url}. Reason: {response.prompt_feedback.block_reason}")
             return f"[APA generation blocked for URL: {url}]"
        else:
             print(f"    WARN: Received empty or unexpected response for {url}. Full response: {response}")
             return f"[APA generation failed for URL: {url}]"

    except Exception as e:
        print(f"    ERROR: Failed to get APA citation for {url}: {e}")
        return f"[APA generation error for URL: {url}]"
    finally:
        time.sleep(API_REQUEST_DELAY) # Prevent hitting rate limits

def reformat_markdown(input_filename, output_filename, api_key):
    """Reads markdown, extracts sources, generates citations, and reformats."""

    print(f"Processing {input_filename}...")

    model = configure_gemini(api_key)
    if not model:
        print("Exiting due to Gemini API configuration error.")
        return

    try:
        with open(input_filename, 'r', encoding='utf-8') as f_in:
            content = f_in.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {input_filename}")
        return
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    # Find all source references: ([Text](URL))
    matches = list(SOURCE_PATTERN.finditer(content))
    if not matches:
        print("No source patterns found in the document.")
        # Optionally write the original content if no changes needed
        # with open(output_filename, 'w', encoding='utf-8') as f_out:
        #     f_out.write(content)
        # print(f"Original content written to {output_filename} as no sources were found.")
        return # Or proceed to just write the original content

    print(f"Found {len(matches)} potential source references.")

    # Store unique URLs and their first appearance order
    unique_sources = OrderedDict()
    for match in matches:
        url = match.group(2)
        if url not in unique_sources:
            unique_sources[url] = {'apa': None, 'number': None}

    print(f"Found {len(unique_sources)} unique URLs. Generating APA citations via Gemini API...")

    # Assign numbers and generate APA citations for unique URLs
    current_number = 1
    for url in unique_sources.keys():
        unique_sources[url]['number'] = current_number
        apa_citation = get_apa_citation(model, url)
        unique_sources[url]['apa'] = apa_citation if apa_citation else f"[Failed to generate APA for {url}]"
        current_number += 1

    print("APA citation generation complete.")
    print("Replacing inline references...")

    # Replace inline references with numbered links (iterate backwards!)
    modified_content = content
    for match in reversed(matches):
        url = match.group(2)
        if url in unique_sources:
            number = unique_sources[url]['number']
            citation_link = f'[{number}](#source-{number})'
            # Replace the specific match span
            start, end = match.span()
            modified_content = modified_content[:start] + citation_link + modified_content[end:]
        else:
            # This case should theoretically not happen with the current logic
            print(f"Warning: URL '{url}' from match not found in unique_sources map during replacement.")

    print("Building final Sources section...")

    # --- Handle potential pre-existing "Sources:" section ---
    # Basic removal: find the last occurrence of a line starting with "# Sources" or "**Sources:**"
    # and remove everything after it. This might be too aggressive if "Sources" appears elsewhere.
    # A safer approach might be to look specifically at the end of the document.
    # For this script, we'll just append, assuming the input format doesn't conflict badly.
    # Example of a simple removal (use with caution):
    # sources_header_match = re.search(r'^# Sources\s*$|^(\*\*Sources:\*\*)\s*$', modified_content, re.MULTILINE | re.IGNORECASE)
    # if sources_header_match:
    #      print("Found existing sources section, removing...")
    #      modified_content = modified_content[:sources_header_match.start()]

    # Remove trailing whitespace before adding the new section
    modified_content = modified_content.rstrip()

    # Create the Sources section
    sources_list_md = "\n\n# Sources\n\n"
    # Sort sources by number for the final list
    sorted_sources = sorted(unique_sources.items(), key=lambda item: item[1]['number'])

    for url, data in sorted_sources:
        number = data['number']
        apa = data['apa']
        # Add an HTML anchor for the hyperlink target
        sources_list_md += f'<a id="source-{number}"></a>{number}. {apa}\n'

    final_content = modified_content + sources_list_md

    try:
        with open(output_filename, 'w', encoding='utf-8') as f_out:
            f_out.write(final_content)
        print(f"Successfully reformatted document saved to: {output_filename}")
    except Exception as e:
        print(f"Error writing output file: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reformat Markdown document to consolidate sources using Gemini API.")
    parser.add_argument("input_file", help="Path to the input Markdown file.")
    parser.add_argument("output_file", help="Path to save the reformatted Markdown file.")
    parser.add_argument("-k", "--api-key", help="Gemini API Key (optional, uses GEMINI_API_KEY environment variable if not provided)", default=None)

    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Error: Gemini API Key not found.")
        print("Please provide it using the --api-key argument or set the GEMINI_API_KEY environment variable.")
    else:
        reformat_markdown(args.input_file, args.output_file, api_key)