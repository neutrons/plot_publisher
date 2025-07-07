from unittest.mock import MagicMock, patch

import pytest

from plot_publisher import plot1d, publish_plot
from plot_publisher._plot_publisher import _inject_plotlyjs_version


@pytest.fixture
def mock_config():
    """Fixture to mock the configuration."""
    with patch("plot_publisher._plot_publisher.read_configuration") as mock_read_config:
        mock_config_obj = MagicMock()
        mock_config_obj.publish_url_template = "http://fake-server.com/publish/${instrument}/${run_number}"
        mock_config_obj.publisher_username = "testuser"
        mock_config_obj.publisher_password = "testpass"
        mock_config_obj.publisher_certificate = ""
        mock_read_config.return_value = mock_config_obj
        yield mock_read_config


def test_plot1d_success(mock_config):
    """
    Test successful 1D plot publishing.
    """
    x = [1, 2, 3]
    y = [4, 5, 6]

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response

        response = plot1d(
            run_number=123,
            data_list=[[x, y]],
            instrument="TEST",
            title="Test Plot",
            x_title="X",
            y_title="Y",
            publish=True,
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

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        response = plot1d(
            run_number=123,
            data_list=[[x, y]],
            instrument="TEST",
            title="Test Plot",
            x_title="X",
            y_title="Y",
            publish=True,
        )

        assert response.status_code == 500
        assert response.text == "Internal Server Error"


def test_plot1d_not_published(mock_config):
    """
    Test that plot1d does not attempt to publish when publish=False.
    """
    x = [1, 2, 3]
    y = [4, 5, 6]

    with patch("requests.post") as mock_post:
        response = plot1d(
            run_number=123,
            data_list=[[x, y]],
            instrument="TEST",
            title="Test Plot",
            x_title="X",
            y_title="Y",
            publish=False,
        )

        assert isinstance(response, str)
        mock_post.assert_not_called()


class TestPlotlyVersionInjection:
    """Test suite for plotlyjs-version injection functionality."""

    def test_inject_plotlyjs_version_basic(self):
        """Test basic plotlyjs-version injection into a div."""
        sample_div = (
            '<div id="abc123-def4-5678-90ab-cdef12345678" class="plotly-graph-div" '
            'style="height:400px; width:100%;"></div>'
        )

        with patch("plotly.__version__", "5.15.0"):
            result = _inject_plotlyjs_version(sample_div)
            assert 'plotlyjs-version="5.15.0"' in result
            assert 'id="abc123-def4-5678-90ab-cdef12345678"' in result

    def test_inject_plotlyjs_version_complex_div(self):
        """Test version injection with a more complex div structure."""
        sample_div = (
            '<div id="plot-div-123" class="plotly-graph-div" '
            'style="height:500px; width:80%;" data-test="value">Content</div>'
        )

        with patch("plotly.__version__", "5.16.1"):
            result = _inject_plotlyjs_version(sample_div)
            assert 'plotlyjs-version="5.16.1"' in result
            assert 'data-test="value"' in result
            assert "Content</div>" in result

    def test_inject_plotlyjs_version_already_exists(self):
        """Test that existing plotlyjs-version attribute is not duplicated."""
        sample_div = '<div id="test-div" plotlyjs-version="5.14.0" class="plotly-graph-div"></div>'

        with patch("plotly.__version__", "5.15.0"):
            result = _inject_plotlyjs_version(sample_div)
            # Should not change the existing version
            assert 'plotlyjs-version="5.14.0"' in result
            assert 'plotlyjs-version="5.15.0"' not in result

    # Note: Skipping test for plotly unavailable case due to complexity of mocking dynamic imports
    # The functionality gracefully handles ImportError with proper logging

    def test_inject_plotlyjs_version_no_div(self):
        """Test behavior with non-div content."""
        non_div_content = "Just some text content without any div tags"

        with patch("plotly.__version__", "5.15.0"):
            result = _inject_plotlyjs_version(non_div_content)
            # Should return unchanged for non-div content
            assert result == non_div_content

    def test_inject_plotlyjs_version_multiple_divs(self):
        """Test that only the first div gets the version attribute."""
        sample_html = """
        <div id="first-div" class="plotly-graph-div">First</div>
        <div id="second-div" class="plotly-graph-div">Second</div>
        """

        with patch("plotly.__version__", "5.15.0"):
            result = _inject_plotlyjs_version(sample_html)
            # Only the first div should get the attribute
            lines = result.split("\n")
            first_div_line = next(line for line in lines if "first-div" in line)
            second_div_line = next(line for line in lines if "second-div" in line)

            assert 'plotlyjs-version="5.15.0"' in first_div_line
            assert 'plotlyjs-version="5.15.0"' not in second_div_line

    def test_publish_plot_with_version_injection(self, mock_config):
        """Test that publish_plot correctly injects version into plot divs."""
        sample_div = '<div id="plot-123" class="plotly-graph-div" style="height:400px;">Plot content</div>'

        with patch("requests.post") as mock_post, patch("plotly.__version__", "5.15.0"):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files={"file": sample_div})

            # Verify that the posted content includes the version
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            posted_files = call_args.kwargs["files"]

            assert 'plotlyjs-version="5.15.0"' in posted_files["file"]
            assert 'id="plot-123"' in posted_files["file"]

    def test_publish_plot_non_html_content(self, mock_config):
        """Test that publish_plot passes through non-HTML content unchanged."""
        non_html_content = "This is just plain text"

        with patch("requests.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files={"file": non_html_content})

            # Verify that non-HTML content is unchanged
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            posted_files = call_args.kwargs["files"]

            assert posted_files["file"] == non_html_content
            assert "plotlyjs-version=" not in posted_files["file"]

    def test_publish_plot_multiple_files(self, mock_config):
        """Test publish_plot with multiple files, some HTML and some not."""
        files = {
            "plot": '<div id="plot-div" class="plotly-graph-div">Plot</div>',
            "data": "csv,data,here",
            "other_plot": '<div id="other-plot" class="plotly-graph-div">Other</div>',
        }

        with patch("requests.post") as mock_post, patch("plotly.__version__", "5.15.0"):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files=files)

            # Verify that only HTML divs get the version attribute
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            posted_files = call_args.kwargs["files"]

            assert 'plotlyjs-version="5.15.0"' in posted_files["plot"]
            assert 'plotlyjs-version="5.15.0"' in posted_files["other_plot"]
            assert posted_files["data"] == "csv,data,here"  # unchanged
