import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

# Add parent directory to path to import drcleaner
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import drcleaner

# Load environment variables from .env file
load_dotenv()

class TestDRCleaner(unittest.TestCase):
    """Test cases for the DR Cleaner script."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_api_key = "test_api_key"
        
        # Create temporary files for testing
        self.temp_input = tempfile.NamedTemporaryFile(delete=False, suffix='.md')
        self.temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.md')
        
        # Close the files so they can be reopened by the script
        self.temp_input.close()
        self.temp_output.close()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary files
        os.unlink(self.temp_input.name)
        os.unlink(self.temp_output.name)
    
    def test_source_pattern_regex(self):
        """Test the SOURCE_PATTERN regex correctly identifies source references."""
        test_cases = [
            ("This is a test ([Source](https://example.com))", True),
            ("No source reference here", False),
            ("Multiple sources ([Source1](https://example1.com)) and ([Source2](https://example2.com))", True),
            ("Malformed source [Source](https://example.com)", False),
            ("Malformed source (Source)(https://example.com)", False),
        ]
        
        for text, should_match in test_cases:
            matches = list(drcleaner.SOURCE_PATTERN.finditer(text))
            if should_match:
                self.assertTrue(len(matches) > 0, f"Should match: {text}")
            else:
                self.assertEqual(len(matches), 0, f"Should not match: {text}")
    
    @patch('drcleaner._call_perplexity_api')
    def test_get_apa_citation(self, mock_call_api):
        """Test the get_apa_citation function with a mocked API response."""
        # Mock the _call_perplexity_api function
        mock_call_api.return_value = 'Author, A. (2023). Test Title. Example.com. https://example.com'
        
        # Call the function
        result = drcleaner.get_apa_citation(self.test_api_key, "https://example.com")
        
        # Verify the result
        self.assertEqual(result, 'Author, A. (2023). Test Title. Example.com. https://example.com')
        
        # Verify the API function was called with the correct parameters
        mock_call_api.assert_called_once()
        args, kwargs = mock_call_api.call_args
        self.assertEqual(args[0], self.test_api_key)
        self.assertEqual(args[1], "https://example.com")
        self.assertIn("https://example.com", args[2])
    
    @patch('drcleaner.get_apa_citation')
    def test_reformat_markdown(self, mock_get_apa):
        """Test the reformat_markdown function with a simple markdown file."""
        # Mock the APA citation generation
        mock_get_apa.return_value = "Author, A. (2023). Test Title. Example.com. https://example.com"
        
        # Create a test markdown file
        test_content = "# Test Document\n\nThis is a paragraph with a source reference ([Example Source](https://example.com)).\n"
        with open(self.temp_input.name, 'w', encoding='utf-8') as f:
            f.write(test_content)
        
        # Call the function
        drcleaner.reformat_markdown(self.temp_input.name, self.temp_output.name, self.test_api_key)
        
        # Read the output file
        with open(self.temp_output.name, 'r', encoding='utf-8') as f:
            output_content = f.read()
        
        # Verify the output
        self.assertIn("[1](#source-1)", output_content)
        self.assertIn("# Sources", output_content)
        self.assertIn("<a id=\"source-1\"></a>1. Author, A. (2023). Test Title. Example.com. https://example.com", output_content)
        
        # Verify the APA citation function was called
        mock_get_apa.assert_called_once_with(self.test_api_key, "https://example.com")

if __name__ == '__main__':
    unittest.main()
