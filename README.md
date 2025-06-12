# Plot Publisher

A utility to publish plotly plots as HTML `div` elements to the Live Data Server.

This package is intended for use in data reduction scripts at SNS and HFIR. It provides a simple interface to generate and publish plots to the monitoring webpages.

## Usage in a Reduction Script

To use the publisher in your script, you can import it and call one of the plotting functions.

```python
from plot_publisher import plot1d, publish_plot

# ... your data processing ...
x = [1, 2, 3, 4]
y = [10, 11, 12, 13]

# Generate a 1D plot and publish it
plot1d(
    run_number=12345,
    data_list=[x, y],
    instrument="MYSPE",
    title="My Awesome Plot",
    x_title="Time (s)",
    y_title="Counts"
)
```

## Configuration

For `publish_plot` to successfully send plots to the server, a configuration file is required. This file must be located at either `/etc/autoreduce/post_processing.conf` or in the local directory as `post_processing.conf`.

The file should contain the following JSON structure with the appropriate values for the Live Data Server:

```json
{
    "publish_url_template": "https://server.com/live/publish/${instrument}/${run_number}",
    "publisher_username": "username",
    "publisher_password": "password",
    "publisher_certificate": ""
}
```

- `publish_url_template`: The URL template for posting plot data. `${instrument}` and `${run_number}` will be substituted.
- `publisher_username`: The username for authentication.
- `publisher_password`: The password for authentication.
- `publisher_certificate`: (Optional) Path to a client certificate for authentication. 
