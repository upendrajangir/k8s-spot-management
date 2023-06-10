import logging

from typing import Optional
from kubernetes import client, config

logger = logging.getLogger(__name__)


class KubernetesApiClient:
    _instance: Optional["KubernetesApiClient"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._create_kubernetes_client()

        return cls._instance

    def _create_kubernetes_client(self) -> None:
        """
        Creates a Kubernetes API client instance and saves it as an attribute of the class.
        """
        try:
            # Load Kubernetes configuration from default location
            config.load_kube_config()

            # Customize the Kubernetes API client configuration
            configuration = client.Configuration()
            configuration.assert_hostname = False

            # Create a Kubernetes API client
            self.api_client = client.api_client.ApiClient(configuration=configuration)
        except Exception as e:
            logger.error(f"Error creating Kubernetes API client: {e}")
            raise