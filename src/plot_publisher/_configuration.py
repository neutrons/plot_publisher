import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

CONFIG_FILE = "/etc/autoreduce/post_processing.conf"
CONFIG_FILE_ALTERNATE = "post_processing.conf"

logger = logging.getLogger(__name__)


@dataclass
class Configuration:
    """
    Configuration settings for plot publishing.

    This is a heavily abridged version of what is found in postprocessing.
    """

    publish_url_template: str
    publisher_username: str
    publisher_password: str
    publisher_certificate: Optional[str] = ""
    verify_ssl: bool = True
    config_file: Optional[str] = None

    @classmethod
    def from_file(cls, config_file: str) -> "Configuration":
        """Create configuration from a JSON file."""
        if not os.access(config_file, os.R_OK):
            raise RuntimeError(f"Configuration file doesn't exist or is not readable: {config_file}")

        with open(config_file, "r") as cfg:
            json_encoded = cfg.read()

        try:
            config_data = json.loads(json_encoded)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in configuration file {config_file}: {e}") from e

        return cls(
            publish_url_template=config_data.get("publish_url_template", ""),
            publisher_username=config_data.get("publisher_username", ""),
            publisher_password=config_data.get("publisher_password", ""),
            publisher_certificate=config_data.get("publisher_certificate", ""),
            verify_ssl=config_data.get("verify_ssl", True),
            config_file=config_file,
        )


def _determine_config_file(config_file: Optional[str] = None) -> Optional[str]:
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


def read_configuration(config_file: Optional[str] = None) -> Configuration:
    """
    Returns a new configuration object for a given configuration file.

    @param config_file: configuration file to process
    @return: Configuration object
    @raises RuntimeError: If no valid configuration file is found
    """
    config_file = _determine_config_file(config_file)
    if config_file is None:
        raise RuntimeError("Failed to find Configuration file")

    logger.info("Loading configuration '%s'", config_file)
    return Configuration.from_file(config_file)
