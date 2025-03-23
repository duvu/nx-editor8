"""Unit tests for pipeline creation functionality."""

import unittest
from unittest.mock import patch, MagicMock, call
import sys
import os

# Add path to root directory to import the main module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mainZ import create_complete_pipeline, PIPELINE_CONFIG

class TestPipelineCreation(unittest.TestCase):
    """Test cases for pipeline creation functionality."""
    
    @patch('mainZ.ProcessorChain')
    @patch('mainZ.logger')
    def test_create_complete_pipeline(self, mock_logger: MagicMock, 
                                     mock_processor_chain: MagicMock) -> None:
        """Test the create_complete_pipeline function.
        
        Args:
            mock_logger: Mocked logger instance.
            mock_processor_chain: Mocked ProcessorChain class.
        """
        # Setup mock chain instance
        mock_chain_instance = mock_processor_chain.return_value
        
        # Call the function to test
        result = create_complete_pipeline()
        
        # Verify chain was created with correct name
        mock_processor_chain.assert_called_once_with("complete_pipeline")
        
        # Verify each processor was added correctly
        expected_calls = [call(processor_func, processor_name) 
                         for processor_func, processor_name in PIPELINE_CONFIG]
        mock_chain_instance.add_processor.assert_has_calls(expected_calls)
        
        # Verify error handler was set
        mock_chain_instance.set_error_handler.assert_called_once()
        
        # Verify logger calls
        mock_logger.info.assert_any_call("Complete processing pipeline created successfully")
        
        # Verify result
        self.assertEqual(result, mock_chain_instance)
    
    def test_pipeline_config_structure(self) -> None:
        """Test that the pipeline configuration has the correct structure."""
        # Verify pipeline config is a list
        self.assertIsInstance(PIPELINE_CONFIG, list)
        
        # Verify each item in pipeline config is a tuple with 2 elements
        for item in PIPELINE_CONFIG:
            self.assertIsInstance(item, tuple)
            self.assertEqual(len(item), 2)
            
            # First element should be callable (processor function)
            self.assertTrue(callable(item[0]))
            
            # Second element should be a string (processor name)
            self.assertIsInstance(item[1], str)
    
    @patch('mainZ.extract_article')
    @patch('mainZ.image_processor')
    @patch('mainZ.video_processor') 
    @patch('mainZ.script_processor')
    @patch('mainZ.s2j_processor')
    def test_pipeline_processors_order(self, mock_s2j: MagicMock, 
                                      mock_script: MagicMock,
                                      mock_video: MagicMock,
                                      mock_image: MagicMock,
                                      mock_extract: MagicMock) -> None:
        """Test that the processors in the pipeline config are in the correct order.
        
        Args:
            mock_s2j: Mocked s2j_processor function.
            mock_script: Mocked script_processor function.
            mock_video: Mocked video_processor function.
            mock_image: Mocked image_processor function.
            mock_extract: Mocked extract_article function.
        """
        # Verify the order of processors in PIPELINE_CONFIG
        # This is important because the order affects how messages are processed
        expected_order = [
            (mock_extract, "extract_article"),
            (mock_image, "image_processor"),
            (mock_video, "video_processor"),
            (mock_script, "script_processor"),
            (mock_s2j, "script2json")
        ]
        
        # Import the actual PIPELINE_CONFIG value after patching
        from mainZ import PIPELINE_CONFIG as actual_config
        
        # Verify configuration matches expected order
        self.assertEqual(len(actual_config), len(expected_order))
        
        for i, (processor_func, processor_name) in enumerate(actual_config):
            expected_func, expected_name = expected_order[i]
            self.assertEqual(processor_func, expected_func)
            self.assertEqual(processor_name, expected_name)

if __name__ == '__main__':
    unittest.main() 