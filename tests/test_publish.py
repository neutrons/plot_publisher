import os
import logging
from plot_publisherpy import plot1d

# Configure logging
logging.basicConfig(level=logging.INFO)

def test_publish_plot():
    """
    A simple test script to publish a plot.
    This requires a post_processing.conf file in the project root directory.
    """
    conf_path = "post_processing.conf"

    if not os.path.exists(conf_path):
        # Create a dummy one for testing if it doesn't exist
        with open(conf_path, "w") as f:
            f.write("""
{
    "publish_url_template": "http://localhost:8080/publish/${instrument}/${run_number}",
    "publisher_username": "test",
    "publisher_password": "password",
    "publisher_certificate": ""
}
""")
        logging.warning(f"Created dummy config at {conf_path}")

    logging.info("Attempting to publish a test plot...")

    x = [1, 2, 3, 4, 5]
    y = [2, 4, 6, 8, 10]

    try:
        # We expect this to fail if a server is not running, but it tests the code path
        response = plot1d(
            run_number=9999,
            data_list=[x, y],
            instrument="NOWX",
            title="Test Plot from plot_publisher",
            x_title="X-axis",
            y_title="Y-axis",
            publish=True
        )
        if response and response.status_code == 200:
            logging.info("Plot published successfully!")
            logging.info(f"Server response: {response.text}")
        else:
            logging.error(f"Failed to publish plot (as expected without a server). Status code: {response.status_code if response else 'N/A'}")

    except Exception as e:
        logging.info(f"An error occurred during publishing as expected: {e}")
    finally:
        if os.path.exists(conf_path) and "localhost" in open(conf_path).read():
            os.remove(conf_path)

if __name__ == "__main__":
    test_publish_plot() 