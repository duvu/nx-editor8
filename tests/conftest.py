import pytest
import sys
import os

# Add project root to path to ensure imports work
@pytest.fixture(autouse=True)
def setup_paths():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)
        
    # Yield control back to the test
    yield
