import re
import requests
import os
import argparse
import time
import logging
from collections import OrderedDict
from dotenv import load_dotenv

# --- Configuration ---
PERPLEXITY_MODEL_NAME = "sonar"  # Perplexity model to use
API_REQUEST_DELAY = 1  # Seconds to wait between API calls (adjust if needed for rate limits)
APA_PROMPT_TEMPLATE = "Visit this web link and generate an appropriate APA style reference line for it in markdown format: {}"
SOURCE_PATTERN = re.compile(r'\(\[([^\]]+)\]\(([^\)]+)\)\)') # Pattern: ([Display Text](URL))

# --- Logger Setup ---
logger = logging.getLogger(__name__)

# --- Helper Functions ---

def configure_perplexity(api_key):
    """Configures the Perplexity API client."""
    if not api_key:
        logger.error("Perplexity API key not provided")
        return None
    return api_key

def get_apa_citation(api_key, url):
    """Calls Perplexity API to get an APA citation for a URL."""
    if not api_key:
        return "[Perplexity API not configured]"
    
    prompt = APA_PROMPT_TEMPLATE.format(url)
    logger.info(f"  Generating APA for: {url[:60]}...")
    
    try:
        perplexity_url = "https://api.perplexity.ai/chat/completions"
        
        payload = {
            "model": PERPLEXITY_MODEL_NAME,
            "messages": [
                {
                    "role": "system",
                    "content": "Generate accurate APA style references. Be precise and concise."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2,
            "top_p": 0.9,
            "search_domain_filter": ["<any>"],
            "return_images": False,
            "return_related_questions": False,
            "top_k": 0,
            "stream": False,
            "frequency_penalty": 1,
            "web_search_options": {"search_context_size": "high"}
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(perplexity_url, json=payload, headers=headers)
        
        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                citation = response_data['choices'][0]['message']['content'].strip()
                # Basic cleanup: remove potential markdown list markers
                if citation.startswith(("- ", "* ")):
                    citation = citation[2:]
                if citation and citation[0].isdigit() and citation[1] == '.' and citation[2] == ' ':
                    citation = citation[3:] # Remove "1. " style numbering if present
                return citation
            else:
                logger.warning(f"    Unexpected response format from Perplexity API for {url}")
                return f"[APA generation failed for URL: {url}]"
        else:
            logger.warning(f"    Perplexity API returned status code {response.status_code} for {url}")
            return f"[APA generation failed for URL: {url} - API error {response.status_code}]"

    except Exception as e:
        logger.error(f"    Failed to get APA citation for {url}: {e}")
        return f"[APA generation error for URL: {url}]"
    finally:
        time.sleep(API_REQUEST_DELAY) # Prevent hitting rate limits

def reformat_markdown(input_filename, output_filename, api_key):
    """Reads markdown, extracts sources, generates citations, and reformats."""

    logger.info(f"Processing {input_filename}...")

    perplexity_api_key = configure_perplexity(api_key)
    if not perplexity_api_key:
        logger.error("Exiting due to Perplexity API configuration error.")
        return

    try:
        with open(input_filename, 'r', encoding='utf-8') as f_in:
            content = f_in.read()
    except FileNotFoundError:
        logger.error(f"Input file not found: {input_filename}")
        return
    except Exception as e:
        logger.error(f"Error reading input file {input_filename}: {e}")
        return

    # Find all source references: ([Text](URL))
    matches = list(SOURCE_PATTERN.finditer(content))
    if not matches:
        logger.info(f"No source patterns found in {input_filename}.")
        # Optionally write the original content if no changes needed
        # with open(output_filename, 'w', encoding='utf-8') as f_out:
        #     f_out.write(content)
        # logger.info(f"Original content written to {output_filename} as no sources were found.")
        return # Or proceed to just write the original content

    logger.info(f"Found {len(matches)} potential source references in {input_filename}.")

    # Store unique URLs and their first appearance order
    unique_sources = OrderedDict()
    for match in matches:
        url = match.group(2)
        if url not in unique_sources:
            unique_sources[url] = {'apa': None, 'number': None}

    logger.info(f"Found {len(unique_sources)} unique URLs in {input_filename}. Generating APA citations via Gemini API...")

    # Assign numbers and generate APA citations for unique URLs
    current_number = 1
    for url in unique_sources.keys():
        unique_sources[url]['number'] = current_number
        apa_citation = get_apa_citation(perplexity_api_key, url)
        unique_sources[url]['apa'] = apa_citation if apa_citation else f"[Failed to generate APA for {url}]"
        current_number += 1

    logger.info("APA citation generation complete for {input_filename}.")
    logger.info("Replacing inline references in {input_filename}...")

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
            logger.warning(f"URL '{url}' from match not found in unique_sources map during replacement in {input_filename}.")

    logger.info("Building final Sources section for {input_filename}...")

    # --- Handle potential pre-existing "Sources:" section ---
    # Basic removal: find the last occurrence of a line starting with "# Sources" or "**Sources:**"
    # and remove everything after it. This might be too aggressive if "Sources" appears elsewhere.
    # A safer approach might be to look specifically at the end of the document.
    # For this script, we'll just append, assuming the input format doesn't conflict badly.
    # Example of a simple removal (use with caution):
    # sources_header_match = re.search(r'^# Sources\s*$|^(\*\*Sources:\*\*)\s*$', modified_content, re.MULTILINE | re.IGNORECASE)
    # if sources_header_match:
    #      logger.info("Found existing sources section, removing...")
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
        logger.info(f"Successfully reformatted document saved to: {output_filename}")
    except Exception as e:
        logger.error(f"Error writing output file {output_filename}: {e}")


# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reformat Markdown document to consolidate sources using Gemini API.")
    parser.add_argument("input_file", help="Path to the input Markdown file.")
    parser.add_argument("output_file", help="Path to save the reformatted Markdown file.")
    parser.add_argument("-k", "--api-key", help="Perplexity API Key (optional, uses PERPLEXITY_API_KEY environment variable if not provided)", default=None)
    parser.add_argument("-v", "--verbose", help="Increase output verbosity (INFO level)", action="store_true")
    args = parser.parse_args()

    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s') # Simpler format for CLI

    api_key = args.api_key or os.getenv("PERPLEXITY_API_KEY")

    if not api_key:
        logger.error("Perplexity API Key not found.")
        logger.error("Please provide it using the --api-key argument or set the PERPLEXITY_API_KEY environment variable.")
    else:
        reformat_markdown(args.input_file, args.output_file, api_key)
