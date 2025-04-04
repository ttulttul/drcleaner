import unittest
import os
import sys
import tempfile
import subprocess
import shutil
from dotenv import load_dotenv

# Add parent directory to path to import drcleaner
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env file
load_dotenv()

class TestDRCleanerIntegration(unittest.TestCase):
    """Integration tests for the DR Cleaner script."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create test input file
        self.input_file = os.path.join(self.test_dir, 'test_input.md')
        self.output_file = os.path.join(self.test_dir, 'test_output.md')
        
        # Sample markdown content with sources
        test_content = """# Integration Test Document

This is a paragraph with a source reference ([Example Source](https://example.com)).

Here's another paragraph with a different source ([Another Source](https://example.org)).

This paragraph references the first source again ([Example Source](https://example.com)).
"""
        with open(self.input_file, 'w', encoding='utf-8') as f:
            f.write(test_content)
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Remove temporary directory and its contents
        shutil.rmtree(self.test_dir)
    
    @unittest.skipIf(not os.environ.get('PERPLEXITY_API_KEY'), 
                    "Skipping integration test: PERPLEXITY_API_KEY environment variable not set")
    def test_script_execution(self):
        """Test executing the script as a subprocess."""
        # Get API key from environment
        api_key = os.environ.get('PERPLEXITY_API_KEY')
        
        # Get the absolute path to the script
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'drcleaner.py'))
        
        # Run the script as a subprocess
        result = subprocess.run(
            [sys.executable, script_path, self.input_file, self.output_file, '-k', api_key],
            capture_output=True,
            text=True
        )
        
        # Check that the script executed successfully
        self.assertEqual(result.returncode, 0, f"Script failed with error: {result.stderr}")
        
        # Check that the output file was created
        self.assertTrue(os.path.exists(self.output_file), "Output file was not created")
        
        # Read the output file
        with open(self.output_file, 'r', encoding='utf-8') as f:
            output_content = f.read()
        
        # Verify the output contains expected elements
        self.assertIn("[1](#source-1)", output_content)
        self.assertIn("[2](#source-2)", output_content)
        self.assertIn("# Sources", output_content)
        self.assertIn("<a id=\"source-1\"></a>", output_content)
        self.assertIn("<a id=\"source-2\"></a>", output_content)
        
        # Verify that there are exactly 2 sources (not 3, as one URL is repeated)
        sources_count = output_content.count("<a id=\"source-")
        self.assertEqual(sources_count, 2, f"Expected 2 unique sources, found {sources_count}")

if __name__ == '__main__':
    unittest.main()
