"""Unit tests for error_handler functionality."""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import time
from typing import Dict, Any

# Add path to root directory to import the main module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from mainZ import error_handler, create_error_info

class TestErrorHandler(unittest.TestCase):
    """Test cases for error_handler and related functions."""
    
    def setUp(self) -> None:
        """Set up test fixtures."""
        self.test_processor_name = "test_processor"
        self.test_error = ValueError("Test error message")
        self.test_message_dict = {"data": "test_data", "id": "123"}
        self.test_message_non_dict = "Not a dictionary"
    
    @patch('mainZ.logger')
    def test_error_handler_with_dict_message(self, mock_logger: MagicMock) -> None:
        """Test error_handler behavior with dictionary messages.
        
        Args:
            mock_logger: Mocked logger instance.
        """
        # Call the error_handler with a dictionary message
        result = error_handler(self.test_message_dict, self.test_error, self.test_processor_name)
        
        # Verify logger was called with expected arguments
        mock_logger.info.assert_any_call(f"Starting error_handler for processor: {self.test_processor_name}")
        mock_logger.error.assert_any_call(f"Error occurred in {self.test_processor_name}: {str(self.test_error)}")
        
        # Verify the result has the expected structure
        self.assertIsInstance(result, dict)
        self.assertIn("processing_error", result)
        self.assertEqual(result["data"], "test_data")
        self.assertEqual(result["id"], "123")
        
        # Verify processing_error has the required fields
        error_info = result["processing_error"]
        self.assertIn("error_id", error_info)
        self.assertIn("processor", error_info)
        self.assertIn("error", error_info)
        self.assertIn("timestamp", error_info)
        self.assertIn("error_type", error_info)
        
        # Verify specific values in error_info
        self.assertEqual(error_info["processor"], self.test_processor_name)
        self.assertEqual(error_info["error"], str(self.test_error))
        self.assertEqual(error_info["error_type"], "ValueError")
    
    @patch('mainZ.logger')
    def test_error_handler_with_non_dict_message(self, mock_logger: MagicMock) -> None:
        """Test error_handler behavior with non-dictionary messages.
        
        Args:
            mock_logger: Mocked logger instance.
        """
        # Call the error_handler with a non-dictionary message
        result = error_handler(self.test_message_non_dict, self.test_error, self.test_processor_name)
        
        # Verify logger was called with expected arguments
        mock_logger.info.assert_any_call(f"Starting error_handler for processor: {self.test_processor_name}")
        mock_logger.warning.assert_called_with(
            f"Message is not a dict, cannot add error information. Type: {type(self.test_message_non_dict)}"
        )
        
        # Verify the result is None
        self.assertIsNone(result)
    
    @patch('time.time', return_value=1234567890.0)
    @patch('random.randint', return_value=1234)
    @patch('mainZ.logger')
    def test_create_error_info(self, mock_logger: MagicMock, mock_randint: MagicMock, mock_time: MagicMock) -> None:
        """Test create_error_info function with controlled time and random values.
        
        Args:
            mock_logger: Mocked logger instance.
            mock_randint: Mocked random.randint function.
            mock_time: Mocked time.time function.
        """
        # Create expected error_id with fixed time and random values
        expected_error_id = f"ERR-1234567890-1234"
        
        # Call the create_error_info function
        error_info = create_error_info(self.test_error, self.test_processor_name)
        
        # Verify logger was called with expected error_id
        mock_logger.error.assert_called_with(f"Error ID: {expected_error_id}")
        
        # Verify the error_info has the expected structure and values
        self.assertEqual(error_info["error_id"], expected_error_id)
        self.assertEqual(error_info["processor"], self.test_processor_name)
        self.assertEqual(error_info["error"], str(self.test_error))
        self.assertEqual(error_info["timestamp"], 1234567890.0)
        self.assertEqual(error_info["error_type"], "ValueError")


if __name__ == '__main__':
    unittest.main() 