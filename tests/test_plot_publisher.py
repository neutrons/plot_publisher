import pytest
from unittest.mock import patch, MagicMock
from plot_publisher.plot_publisher import plot1d, read_configuration

@pytest.fixture
def mock_config():
    """Fixture to mock the configuration."""
    with patch('plot_publisher.plot_publisher.read_configuration') as mock_read_config:
        mock_config_obj = MagicMock()
        mock_config_obj.publish_url_template = "http://fake-server.com/publish/${instrument}/${run_number}"
        mock_config_obj.publisher_username = "testuser"
        mock_config_obj.publisher_password = "testpass"
        mock_read_config.return_value = mock_config_obj
        yield mock_read_config

def test_plot1d_success(mock_config):
    """
    Test successful 1D plot publishing.
    """
    x = [1, 2, 3]
    y = [4, 5, 6]

    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response

        response = plot1d(
            run_number=123,
            data_list=[x, y],
            instrument="TEST",
            title="Test Plot",
            x_title="X",
            y_title="Y",
            publish=True
        )

        assert response.status_code == 200
        assert response.text == "Success"
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://fake-server.com/publish/TEST/123"

def test_plot1d_server_error(mock_config):
    """
    Test 1D plot publishing when the server returns an error.
    """
    x = [1, 2, 3]
    y = [4, 5, 6]

    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        response = plot1d(
            run_number=123,
            data_list=[x, y],
            instrument="TEST",
            title="Test Plot",
            x_title="X",
            y_title="Y",
            publish=True
        )

        assert response.status_code == 500
        assert response.text == "Internal Server Error"

def test_plot1d_not_published(mock_config):
    """
    Test that plot1d does not attempt to publish when publish=False.
    """
    x = [1, 2, 3]
    y = [4, 5, 6]

    with patch('requests.post') as mock_post:
        response = plot1d(
            run_number=123,
            data_list=[x, y],
            instrument="TEST",
            title="Test Plot",
            x_title="X",
            y_title="Y",
            publish=False
        )

        assert response is None
        mock_post.assert_not_called() 