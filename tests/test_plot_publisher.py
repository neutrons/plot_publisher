from unittest.mock import MagicMock, patch

import pytest
import requests

from plot_publisher import plot1d, plot_heatmap, publish_plot
from plot_publisher._plot_publisher import (
    extract_data, extract_heatmap_data, extract_plot1d_data, inject_plotlyjs_version
)


@pytest.fixture
def mock_config():
    """Fixture to mock the configuration."""
    # Return a real Configuration object rather than a mock
    from plot_publisher._configuration import Configuration

    return Configuration(
        publish_url_template="http://fake-server.com/publish/${instrument}/${run_number}",
        publisher_username="testuser",
        publisher_password="testpass",
        publisher_certificate="",
        verify_ssl=False,
    )


def test_plot1d_success(mock_config):
    """
    Test successful 1D plot publishing.
    """
    x = [1, 2, 3]
    y = [4, 5, 6]

    with (
        patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
        patch("requests.post") as mock_post,
    ):
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

    with (
        patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
        patch("requests.post") as mock_post,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.raise_for_status.side_effect = requests.HTTPError("Server Error")
        mock_post.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            plot1d(
                run_number=123,
                data_list=[[x, y]],
                instrument="TEST",
                title="Test Plot",
                x_title="X",
                y_title="Y",
                publish=True,
            )


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

        with patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"):
            result = inject_plotlyjs_version(sample_div)
            assert 'plotlyjs-version="2.24.1"' in result
            assert 'id="abc123-def4-5678-90ab-cdef12345678"' in result

    def test_inject_plotlyjs_version_complex_div(self):
        """Test version injection with a more complex div structure."""
        sample_div = (
            '<div id="plot-div-123" class="plotly-graph-div" '
            'style="height:500px; width:80%;" data-test="value">Content</div>'
        )

        with patch("plotly.offline.get_plotlyjs_version", return_value="2.25.0"):
            result = inject_plotlyjs_version(sample_div)
            assert 'plotlyjs-version="2.25.0"' in result
            assert 'data-test="value"' in result
            assert "Content</div>" in result

    def test_inject_plotlyjs_version_already_exists(self):
        """Test that existing plotlyjs-version attribute is not duplicated."""
        sample_div = '<div id="test-div" plotlyjs-version="5.14.0" class="plotly-graph-div"></div>'

        with patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"):
            result = inject_plotlyjs_version(sample_div)
            # Should not change the existing version
            assert 'plotlyjs-version="5.14.0"' in result
            assert 'plotlyjs-version="2.24.1"' not in result

    def test_inject_plotlyjs_version_auto_detect(self):
        """Test auto-detection of plotly version when version=None."""
        sample_div = (
            '<div id="abc123-def4-5678-90ab-cdef12345678" class="plotly-graph-div" '
            'style="height:400px; width:100%;"></div>'
        )

        with patch("plotly.offline.get_plotlyjs_version", return_value="2.26.1"):
            result = inject_plotlyjs_version(sample_div)  # No version parameter
            assert 'plotlyjs-version="2.26.1"' in result
            assert 'id="abc123-def4-5678-90ab-cdef12345678"' in result

    # Note: Skipping test for plotly unavailable case due to complexity of mocking dynamic imports
    # The functionality gracefully handles ImportError with proper logging

    def test_inject_plotlyjs_version_no_div(self):
        """Test behavior with non-div content."""
        non_div_content = "Just some text content without any div tags"

        with patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"):
            result = inject_plotlyjs_version(non_div_content)
            # Should return unchanged for non-div content
            assert result == non_div_content

    def test_inject_plotlyjs_version_multiple_divs(self):
        """Test that only the first div gets the version attribute."""
        sample_html = """
        <div id="first-div" class="plotly-graph-div">First</div>
        <div id="second-div" class="plotly-graph-div">Second</div>
        """

        with patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"):
            result = inject_plotlyjs_version(sample_html)
            # Only the first div should get the attribute
            lines = result.split("\n")
            first_div_line = next(line for line in lines if "first-div" in line)
            second_div_line = next(line for line in lines if "second-div" in line)

            assert 'plotlyjs-version="2.24.1"' in result
            assert 'plotlyjs-version="2.24.1"' in first_div_line
            assert 'plotlyjs-version="2.24.1"' not in second_div_line

    def test_publish_plot_with_version_injection(self, mock_config):
        """Test that publish_plot correctly injects version into plot divs."""
        sample_div = '<div id="plot-123" class="plotly-graph-div" style="height:400px;">Plot content</div>'

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("requests.post") as mock_post,
            patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"),
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files={"file": sample_div})

            # Verify that the posted content includes the version
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            posted_files = call_args.kwargs["files"]

            assert 'plotlyjs-version="2.24.1"' in posted_files["file"]
            assert 'id="plot-123"' in posted_files["file"]

    def test_publish_plot_non_html_content(self, mock_config):
        """Test that publish_plot passes through non-HTML content unchanged."""
        non_html_content = "This is just plain text"

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("requests.post") as mock_post,
        ):
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

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("requests.post") as mock_post,
            patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"),
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files=files)

            # Verify that only HTML divs get the version attribute
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            posted_files = call_args.kwargs["files"]

            assert 'plotlyjs-version="2.24.1"' in posted_files["plot"]
            assert 'plotlyjs-version="2.24.1"' in posted_files["other_plot"]
            assert posted_files["data"] == "csv,data,here"  # unchanged

    def test_publish_plot_input_validation(self, mock_config):
        """Test input validation in publish_plot function."""

        # Test empty instrument
        with pytest.raises(ValueError, match="instrument must be a non-empty string"):
            publish_plot(instrument="", run_number=123, files={"test": "content"})

        # Test non-string instrument
        with pytest.raises(ValueError, match="instrument must be a non-empty string"):
            publish_plot(instrument=123, run_number=123, files={"test": "content"})

        # Test empty files
        with pytest.raises(ValueError, match="files must be a non-empty dictionary"):
            publish_plot(instrument="TEST", run_number=123, files={})

        # Test non-dict files
        with pytest.raises(ValueError, match="files must be a non-empty dictionary"):
            publish_plot(instrument="TEST", run_number=123, files="not a dict")

    def test_inject_plotlyjs_version_input_validation(self):
        """Test input validation for inject_plotlyjs_version function."""

        # Test non-string input
        with pytest.raises(ValueError, match="html_content must be a string"):
            inject_plotlyjs_version(123)

        with pytest.raises(ValueError, match="html_content must be a string"):
            inject_plotlyjs_version(None)

    def test_inject_plotlyjs_version_auto_detect(self):  # noqa: F811
        """Test auto-detection of plotly version when no version parameter is provided."""
        sample_div = (
            '<div id="abc123-def4-5678-90ab-cdef12345678" class="plotly-graph-div" '
            'style="height:400px; width:100%;"></div>'
        )

        with patch("plotly.offline.get_plotlyjs_version", return_value="2.26.1"):
            result = inject_plotlyjs_version(sample_div)  # No version parameter
            assert 'plotlyjs-version="2.26.1"' in result
            assert 'id="abc123-def4-5678-90ab-cdef12345678"' in result

    def test_inject_plotlyjs_version_auto_detect_plotly_unavailable(self):
        """Test graceful handling when plotly is not available and no version is provided."""
        sample_div = (
            '<div id="abc123-def4-5678-90ab-cdef12345678" class="plotly-graph-div" '
            'style="height:400px; width:100%;"></div>'
        )

        with patch("builtins.__import__", side_effect=ImportError("No module named 'plotly'")):
            result = inject_plotlyjs_version(sample_div)  # No version parameter, plotly unavailable
            # Should return unchanged content
            assert result == sample_div
            assert "plotlyjs-version=" not in result


# Additional tests for coverage improvement
class TestAdditionalCoverage:
    """Additional tests to improve code coverage."""

    def test_publish_plot_config_string_path(self, mock_config):
        """Test publish_plot with string configuration path."""
        sample_div = '<div id="plot-123" class="plotly-graph-div">Plot content</div>'

        with (
            patch("plot_publisher._plot_publisher.read_configuration") as mock_read_config,
            patch("requests.post") as mock_post,
            patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"),
        ):
            mock_read_config.return_value = mock_config
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files={"file": sample_div}, config="/path/to/config.cfg")

            # Verify read_configuration was called with the string path
            mock_read_config.assert_called_with("/path/to/config.cfg")

    def test_publish_plot_invalid_config_type(self):
        """Test publish_plot with invalid configuration type."""
        sample_div = '<div id="plot-123" class="plotly-graph-div">Plot content</div>'

        with pytest.raises(ValueError, match="config must be a Configuration object"):
            publish_plot(instrument="TEST", run_number=456, files={"file": sample_div}, config=123)

    def test_publish_plot_certificate_auth(self, mock_config):
        """Test publish_plot with certificate authentication."""
        sample_div = '<div id="plot-123" class="plotly-graph-div">Plot content</div>'

        # Set up config with certificate
        mock_config.publisher_certificate = "/path/to/cert.pem"

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("requests.post") as mock_post,
            patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"),
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files={"file": sample_div})

            # Verify certificate was used in the request
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            assert "cert" in call_kwargs
            assert call_kwargs["cert"] == "/path/to/cert.pem"

    def test_publish_plot_urllib3_fallback(self, mock_config):
        """Test urllib3 warning disable fallback for older versions."""
        sample_div = '<div id="plot-123" class="plotly-graph-div">Plot content</div>'

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("requests.post") as mock_post,
            patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"),
            patch("urllib3.disable_warnings") as mock_disable_warnings,
        ):
            # Simulate AttributeError to trigger fallback
            mock_disable_warnings.side_effect = [AttributeError("No InsecureRequestWarning"), None]

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            publish_plot(instrument="TEST", run_number=456, files={"file": sample_div})

            # Verify fallback was called
            assert mock_disable_warnings.call_count == 2

    def test_is_plotly_html_content_non_string(self):
        """Test _is_plotly_html_content with non-string input."""
        from plot_publisher._plot_publisher import _is_plotly_html_content

        assert not _is_plotly_html_content(None)
        assert not _is_plotly_html_content(123)
        assert not _is_plotly_html_content([])
        assert not _is_plotly_html_content({})

    def test_plot1d_invalid_data_list(self, mock_config):
        """Test plot1d with invalid data_list parameter."""
        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            with pytest.raises(RuntimeError, match="data_list parameter is expected to be a list"):
                plot1d(run_number=123, data_list="not a list", instrument="TEST", publish=False)

    def test_plot1d_malformed_data_traces(self, mock_config):
        """Test plot1d with malformed data traces."""
        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            # Test with invalid trace (not a list)
            with pytest.raises(RuntimeError, match="data_list\\[0\\] should be a list"):
                plot1d(run_number=123, data_list=["invalid"], instrument="TEST", publish=False)

            # Test with insufficient data (less than [x, y])
            with pytest.raises(RuntimeError, match="data_list\\[0\\] should be a list with at least"):
                plot1d(run_number=123, data_list=[[1]], instrument="TEST", publish=False)

    def test_plot1d_multiple_traces_with_names(self, mock_config):
        """Test plot1d with multiple traces and data names."""
        x1, y1 = [1, 2, 3], [1, 4, 9]
        x2, y2 = [1, 2, 3], [2, 8, 18]

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            result = plot1d(
                run_number=123,
                data_list=[[x1, y1], [x2, y2]],
                data_names=["Trace 1", "Trace 2"],
                instrument="TEST",
                publish=False,
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot1d_with_error_bars(self, mock_config):
        """Test plot1d with error bars (dx and dy)."""
        x = [1, 2, 3]
        y = [1, 4, 9]
        dy = [0.1, 0.2, 0.3]
        dx = [0.05, 0.1, 0.15]

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            # Test with multiple trace format [[x, y, dy, dx]]
            result = plot1d(run_number=123, data_list=[[x, y, dy, dx]], instrument="TEST", show_dx=True, publish=False)

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot1d_hide_dx_error_bars(self, mock_config):
        """Test plot1d with dx error bars hidden."""
        x = [1, 2, 3]
        y = [1, 4, 9]
        dy = [0.1, 0.2, 0.3]
        dx = [0.05, 0.1, 0.15]

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            # Test with multiple trace format [[x, y, dy, dx]]
            result = plot1d(
                run_number=123,
                data_list=[[x, y, dy, dx]],
                instrument="TEST",
                show_dx=False,  # Hide x error bars
                publish=False,
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot1d_log_scales(self, mock_config):
        """Test plot1d with logarithmic scales."""
        x = [1, 10, 100]
        y = [1, 100, 10000]

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            result = plot1d(
                run_number=123, data_list=[[x, y]], instrument="TEST", x_log=True, y_log=True, publish=False
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot1d_other_exception(self, mock_config):
        """Test plot1d with non-HTTP exception during publishing."""
        x = [1, 2, 3]
        y = [1, 4, 9]

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("plot_publisher._plot_publisher.publish_plot") as mock_publish,
        ):
            # Simulate a non-HTTP exception
            mock_publish.side_effect = ValueError("Some other error")

            result = plot1d(run_number=123, data_list=[[x, y]], instrument="TEST", publish=True)

            # Should return None for non-HTTP exceptions
            assert result is None

    def test_plot_heatmap_basic(self, mock_config):
        """Test basic plot_heatmap functionality."""
        x = [1, 2, 3]
        y = [1, 2, 3]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            result = plot_heatmap(run_number=123, x=x, y=y, z=z, instrument="TEST", publish=False)

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot_heatmap_surface(self, mock_config):
        """Test plot_heatmap with surface plot."""
        x = [1, 2, 3]
        y = [1, 2, 3]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            result = plot_heatmap(
                run_number=123,
                x=x,
                y=y,
                z=z,
                instrument="TEST",
                surface=True,  # Enable surface plot
                publish=False,
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot_heatmap_log_scales(self, mock_config):
        """Test plot_heatmap with logarithmic scales."""
        x = [1, 10, 100]
        y = [1, 10, 100]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            result = plot_heatmap(
                run_number=123, x=x, y=y, z=z, instrument="TEST", x_log=True, y_log=True, publish=False
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot_heatmap_published(self, mock_config):
        """Test plot_heatmap with publishing enabled."""
        x = [1, 2, 3]
        y = [1, 2, 3]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("requests.post") as mock_post,
            patch("plotly.offline.get_plotlyjs_version", return_value="2.24.1"),
        ):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            response = plot_heatmap(
                run_number=123,
                x=x,
                y=y,
                z=z,
                instrument="TEST",
                title="Heatmap Test",
                x_title="X Axis",
                y_title="Y Axis",
                publish=True,
            )

            assert response.status_code == 200
            mock_post.assert_called_once()

    def test_plot_heatmap_http_error(self, mock_config):
        """Test plot_heatmap with HTTP error during publishing."""
        x = [1, 2, 3]
        y = [1, 2, 3]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("requests.post") as mock_post,
        ):
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = requests.HTTPError("Server Error")
            mock_post.return_value = mock_response

            with pytest.raises(requests.HTTPError):
                plot_heatmap(run_number=123, x=x, y=y, z=z, instrument="TEST", publish=True)

    def test_plot_heatmap_other_exception(self, mock_config):
        """Test plot_heatmap with non-HTTP exception during publishing."""
        x = [1, 2, 3]
        y = [1, 2, 3]
        z = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

        with (
            patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config),
            patch("plot_publisher._plot_publisher.publish_plot") as mock_publish,
        ):
            # Simulate a non-HTTP exception
            mock_publish.side_effect = ValueError("Some other error")

            result = plot_heatmap(run_number=123, x=x, y=y, z=z, instrument="TEST", publish=True)

            # Should return None for non-HTTP exceptions
            assert result is None

    def test_plot1d_single_trace_format_with_tuples(self, mock_config):
        """Test plot1d with single trace format using tuples instead of lists."""
        # Use tuples to trigger the single trace path (isinstance(data_list[0], list) == False)
        x = (1, 2, 3)
        y = (1, 4, 9)
        dy = (0.1, 0.2, 0.3)
        dx = (0.05, 0.1, 0.15)

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            # Test with single trace format using tuples
            result = plot1d(
                run_number=123,
                data_list=[x, y, dy, dx],  # tuples instead of lists
                data_names=["Single Trace"],
                instrument="TEST",
                show_dx=True,
                publish=False,
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot1d_single_trace_y_errors_only(self, mock_config):
        """Test plot1d single trace with only y error bars."""
        x = (1, 2, 3)
        y = (1, 4, 9)
        dy = (0.1, 0.2, 0.3)

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            # Test with single trace format using tuples, only y errors
            result = plot1d(
                run_number=123,
                data_list=[x, y, dy],  # Only x, y, dy (no dx)
                instrument="TEST",
                publish=False,
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result

    def test_plot1d_single_trace_hide_dx_errors(self, mock_config):
        """Test plot1d single trace with hidden dx error bars."""
        x = (1, 2, 3)
        y = (1, 4, 9)
        dy = (0.1, 0.2, 0.3)
        dx = (0.05, 0.1, 0.15)

        with patch("plot_publisher._plot_publisher.read_configuration", return_value=mock_config):
            # Test with show_dx=False to cover the thickness=0 line
            result = plot1d(
                run_number=123,
                data_list=[x, y, dy, dx],
                instrument="TEST",
                show_dx=False,  # This should trigger err_x["thickness"] = 0
                publish=False,
            )

            assert isinstance(result, str)
            assert "plotly-graph-div" in result


class TestExtractPlot1dData:
    """Test suite for extract_plot1d_data functionality."""
    @staticmethod
    def _make_div(data_list, **kwargs):
        """Return a plot1d div (publish=False) for the given data_list."""
        return plot1d(run_number=1, data_list=data_list, publish=False, **kwargs)

    def test_invalid_input(self):
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_plot1d_data(None)
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_plot1d_data(42)
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_plot1d_data(["<div></div>"])

        with pytest.raises(ValueError, match="No Plotly data found in the provided div"):
            extract_plot1d_data("<div><p>Hello world</p></div>")
        with pytest.raises(ValueError, match="No Plotly data found in the provided div"):
            extract_plot1d_data("")
        bad_div = (
            '<div id="x" class="plotly-graph-div"></div>'
            "<script>Plotly.newPlot('x', [{ INVALID JSON }], {})</script>"
        )
        with pytest.raises(ValueError, match="Failed to parse Plotly JSON data"):
            extract_plot1d_data(bad_div)

    def test_single_trace_xy_only(self):
        """Round-trip [x, y] – no error bars."""
        x = [1.0, 2.0, 3.0]
        y = [4.0, 5.0, 6.0]
        div = self._make_div([[x, y]])
        result = extract_plot1d_data(div)
        assert len(result) == 1
        rx, ry = result[0]
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)

    def test_single_trace_with_dy(self):
        """Round-trip [x, y, dy] – Y error bars only."""
        x = [1.0, 2.0, 3.0]
        y = [1.0, 4.0, 9.0]
        dy = [0.1, 0.2, 0.3]
        div = self._make_div([[x, y, dy]])
        result = extract_plot1d_data(div)
        assert len(result) == 1
        rx, ry, rdy = result[0]
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        assert rdy == pytest.approx(dy)

    def test_single_trace_with_dy_dx(self):
        """Round-trip [x, y, dy, dx] – both error bars."""
        x = [1.0, 2.0, 3.0]
        y = [1.0, 4.0, 9.0]
        dy = [0.1, 0.2, 0.3]
        dx = [0.05, 0.10, 0.15]
        div = self._make_div([[x, y, dy, dx]])
        result = extract_plot1d_data(div)
        assert len(result) == 1
        rx, ry, rdy, rdx = result[0]
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        assert rdy == pytest.approx(dy)
        assert rdx == pytest.approx(dx)

    def test_multiple_traces(self):
        """Round-trip with two traces."""
        x1, y1 = [1.0, 2.0, 3.0], [1.0, 4.0, 9.0]
        x2, y2 = [10.0, 20.0, 30.0], [2.0, 8.0, 18.0]
        div = self._make_div([[x1, y1], [x2, y2]])
        result = extract_plot1d_data(div)
        assert len(result) == 2
        assert result[0][0] == pytest.approx(x1)
        assert result[0][1] == pytest.approx(y1)
        assert result[1][0] == pytest.approx(x2)
        assert result[1][1] == pytest.approx(y2)

    def test_multiple_traces_with_errors(self):
        """Round-trip with two traces, each carrying dy and dx."""
        x1, y1 = [1.0, 2.0], [3.0, 4.0]
        dy1, dx1 = [0.1, 0.2], [0.01, 0.02]
        x2, y2 = [5.0, 6.0], [7.0, 8.0]
        dy2, dx2 = [0.3, 0.4], [0.03, 0.04]
        div = self._make_div([[x1, y1, dy1, dx1], [x2, y2, dy2, dx2]])
        result = extract_plot1d_data(div)
        assert len(result) == 2
        assert result[0] == [pytest.approx(x1), pytest.approx(y1), pytest.approx(dy1), pytest.approx(dx1)]
        assert result[1] == [pytest.approx(x2), pytest.approx(y2), pytest.approx(dy2), pytest.approx(dx2)]

    def test_error_bars_extracted_when_show_dx_false(self):
        """dx array is returned even when show_dx=False hides the bars visually."""
        x = [1.0, 2.0, 3.0]
        y = [1.0, 4.0, 9.0]
        dy = [0.1, 0.2, 0.3]
        dx = [0.05, 0.10, 0.15]
        div = self._make_div([[x, y, dy, dx]], show_dx=False)
        result = extract_plot1d_data(div)
        assert len(result) == 1
        rx, ry, rdy, rdx = result[0]
        assert rdx == pytest.approx(dx)


class TestExtractHeatmapData:
    """Test suite for extract_heatmap_data functionality."""

    @staticmethod
    def _make_div(x, y, z, **kwargs):
        """Return a plot_heatmap div (publish=False) for the given x, y, z."""
        return plot_heatmap(run_number=1, x=x, y=y, z=z, publish=False, **kwargs)

    def test_invalid_input(self):
        """ValueError is raised for non-string, missing Plotly data, and malformed JSON."""
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_heatmap_data(None)
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_heatmap_data(42)
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_heatmap_data(["<div></div>"])

        with pytest.raises(ValueError, match="No Plotly data found in the provided div"):
            extract_heatmap_data("<div><p>Hello world</p></div>")
        with pytest.raises(ValueError, match="No Plotly data found in the provided div"):
            extract_heatmap_data("")

        bad_div = (
            '<div id="x" class="plotly-graph-div"></div>'
            "<script>Plotly.newPlot('x', [{ INVALID JSON }], {})</script>"
        )
        with pytest.raises(ValueError, match="Failed to parse Plotly JSON data"):
            extract_heatmap_data(bad_div)

    def test_no_z_data(self):
        """ValueError is raised when the trace has no z key (e.g. a 1D plot div)."""
        div = plot1d(run_number=1, data_list=[[[1.0, 2.0], [3.0, 4.0]]], publish=False)
        with pytest.raises(ValueError, match="No z data found in trace"):
            extract_heatmap_data(div)

    def test_heatmap_round_trip(self):
        """Round-trip x, y, z for a basic heatmap."""
        x = [1.0, 2.0, 3.0]
        y = [4.0, 5.0]
        z = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        div = self._make_div(x, y, z)
        rx, ry, rz = extract_heatmap_data(div)
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        assert len(rz) == len(z)
        for row, expected_row in zip(rz, z):
            assert row == pytest.approx(expected_row)

    def test_surface_round_trip(self):
        """Round-trip x, y, z for a surface plot."""
        x = [0.0, 1.0, 2.0]
        y = [0.0, 1.0]
        z = [[1.0, 4.0, 9.0], [2.0, 8.0, 18.0]]
        div = self._make_div(x, y, z, surface=True)
        rx, ry, rz = extract_heatmap_data(div)
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        assert len(rz) == len(z)
        for row, expected_row in zip(rz, z):
            assert row == pytest.approx(expected_row)

    def test_larger_grid(self):
        """Round-trip a larger z grid."""
        x = [float(i) for i in range(5)]
        y = [float(i) for i in range(4)]
        z = [[float(i * 5 + j) for j in range(5)] for i in range(4)]
        div = self._make_div(x, y, z)
        rx, ry, rz = extract_heatmap_data(div)
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        for row, expected_row in zip(rz, z):
            assert row == pytest.approx(expected_row)


class TestExtractData:
    """Test suite for the extract_data dispatcher function."""

    def test_invalide_input(self):
        """ValueError is raised for non-string inputs."""
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_data(None)
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_data(42)
        with pytest.raises(ValueError, match="plot_div must be a string"):
            extract_data(["<div></div>"])
        with pytest.raises(ValueError, match="No Plotly data found in the provided div"):
            extract_data("<div><p>Hello world</p></div>")
        with pytest.raises(ValueError, match="No Plotly data found in the provided div"):
            extract_data("")
        bad_div = (
            '<div id="x" class="plotly-graph-div"></div>'
            "<script>Plotly.newPlot('x', [{ INVALID JSON }], {})</script>"
        )
        with pytest.raises(ValueError, match="Failed to parse Plotly JSON data"):
            extract_data(bad_div)

    def test_dispatches_to_plot1d_xy(self):
        """Delegates to extract_plot1d_data for a basic [x, y] plot."""
        x, y = [1.0, 2.0, 3.0], [4.0, 5.0, 6.0]
        div = plot1d(run_number=1, data_list=[[x, y]], publish=False)
        result = extract_data(div)
        assert len(result) == 1
        assert result[0][0] == pytest.approx(x)
        assert result[0][1] == pytest.approx(y)

    def test_dispatches_to_plot1d_with_errors(self):
        """Delegates to extract_plot1d_data for a plot with dy and dx."""
        x, y = [1.0, 2.0, 3.0], [1.0, 4.0, 9.0]
        dy, dx = [0.1, 0.2, 0.3], [0.05, 0.10, 0.15]
        div = plot1d(run_number=1, data_list=[[x, y, dy, dx]], publish=False)
        result = extract_data(div)
        assert len(result) == 1
        rx, ry, rdy, rdx = result[0]
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        assert rdy == pytest.approx(dy)
        assert rdx == pytest.approx(dx)

    def test_dispatches_to_plot1d_multiple_traces(self):
        """Delegates to extract_plot1d_data for multiple traces."""
        x1, y1 = [1.0, 2.0], [3.0, 4.0]
        x2, y2 = [5.0, 6.0], [7.0, 8.0]
        div = plot1d(run_number=1, data_list=[[x1, y1], [x2, y2]], publish=False)
        result = extract_data(div)
        assert len(result) == 2
        assert result[0][0] == pytest.approx(x1)
        assert result[1][0] == pytest.approx(x2)

    def test_dispatches_to_heatmap(self):
        """Delegates to extract_heatmap_data for a heatmap plot."""
        x = [1.0, 2.0, 3.0]
        y = [4.0, 5.0]
        z = [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]
        div = plot_heatmap(run_number=1, x=x, y=y, z=z, publish=False)
        rx, ry, rz = extract_data(div)
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        for row, expected_row in zip(rz, z):
            assert row == pytest.approx(expected_row)

    def test_dispatches_to_surface(self):
        """Delegates to extract_heatmap_data for a surface plot."""
        x = [0.0, 1.0, 2.0]
        y = [0.0, 1.0]
        z = [[1.0, 4.0, 9.0], [2.0, 8.0, 18.0]]
        div = plot_heatmap(run_number=1, x=x, y=y, z=z, surface=True, publish=False)
        rx, ry, rz = extract_data(div)
        assert rx == pytest.approx(x)
        assert ry == pytest.approx(y)
        for row, expected_row in zip(rz, z):
            assert row == pytest.approx(expected_row)

