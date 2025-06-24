import json
import logging
import os

CONFIG_FILE = "/etc/autoreduce/post_processing.conf"
CONFIG_FILE_ALTERNATE = "post_processing.conf"


class Configuration(object):
    """
    Read and process configuration file and provide an easy
    way to hold the various options for a client. This is a
    heavily abridged version of what is found in postprocessing.
    """

    def __init__(self, config_file):
        if not os.access(config_file, os.R_OK):
            raise RuntimeError(f"Configuration file doesn't exist or is not readable: {config_file}")
        with open(config_file, "r") as cfg:
            json_encoded = cfg.read()
        config = json.loads(json_encoded)

        # Keep a record of which config file we are using
        self.config_file = config_file

        # plot publishing
        self.publish_url_template = config.get("publish_url_template", "")
        self.publisher_username = config.get("publisher_username", "")
        self.publisher_password = config.get("publisher_password", "")
        self.publisher_certificate = config.get("publisher_certificate", "")


def _determine_config_file(config_file=None):
    # put together the list of all choices
    choices = [config_file, CONFIG_FILE, CONFIG_FILE_ALTERNATE]

    # filter out bad choices
    choices = [name for name in choices if name is not None]
    choices = [name for name in choices if len(name) > 0]
    choices = [name for name in choices if os.access(name, os.R_OK)]

    # first one is a winner
    if len(choices) > 0:
        return choices[0]
    else:
        return None


def read_configuration(config_file=None):
    """
    Returns a new configuration object for a given
    configuration file
    @param config_file: configuration file to process
    """
    config_file = _determine_config_file(config_file)
    if config_file is None:
        raise RuntimeError("Failed to find Configuration file")

    logging.info("Loading configuration '%s'" % config_file)
    return Configuration(config_file) 