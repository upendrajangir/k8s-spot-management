import logging
import yaml
from typing import Optional
from kubernetes import client
from .client import KubernetesApiClient

logger = logging.getLogger(__name__)
k8s_api_instance = KubernetesApiClient().api_client


class NodeManager:
    labels = [{"type": "spot"}, {"beta.kubernetes.io/instance-type": "Standard_F2s_v2"}]

    def __init__(self):
        self.api_instance = client.CoreV1Api()

    def list_nodes(self) -> Optional[client.V1DeploymentList]:
        try:
            return self.api_instance.list_nodes(watch=False)
        except client.ApiException as e:
            logger.error(f"Error listing nodes: {e}")
            return None

    def get_node(self, name: str) -> Optional[client.V1Deployment]:
        try:
            # TODO: write logic for getting node
            return self.api_instance.read_node(name=name)
        except client.ApiException as e:
            logger.error(f"Error getting deployment: {e}")
            return None

    def scale_nodes(
        self, nodepool_name: str, replicas: str
    ) -> Optional[client.V1Deployment]:
        try:
            # TODO: write logic for scaling node
            return self.api_instance.create_namespaced_deployment(
                namespace=namespace, body=deployment
            )
        except client.ApiException as e:
            logger.error(f"Error creating deployment: {e}")
            return None

    def delete_node(self, name: str) -> bool:
        try:
            self.api_instance.delete_node(name=name)
            return True
        except client.ApiException as e:
            logger.error(f"Error deleting deployment: {e}")
            return False

    def drain_node(self, name: str, grace_termination_period: int) -> Optional[bool]:
        try:
            # Taint the node first
            body = {
                "spec": {
                    "taints": [
                        {
                            "effect": "NoSchedule",
                            "key": "node.kubernetes.io/unschedulable",
                            "value": "true",
                        }
                    ]
                }
            }

            # Update the node with the taint
            self.api_instance.patch_node(name, body)

            # Now we will drain the node. We will first cordon it (make it unschedulable)
            body = {"spec": {"unschedulable": True}}

            # Update the node status to unschedulable
            self.api_instance.patch_node(name, body)

            # Get the list of pods running on the node
            pods = self.api_instance.list_pod_for_all_namespaces(
                field_selector=f"spec.nodeName={name}", watch=False
            )

            # Evict and delete the pods from the node
            for pod in pods.items:
                pod_name = pod.metadata.name
                namespace = pod.metadata.namespace

                # Create an eviction for the pod with the user-specified termination period
                eviction = client.V1Eviction(
                    metadata=client.V1ObjectMeta(name=pod_name, namespace=namespace),
                    delete_options=client.V1DeleteOptions(
                        grace_period_seconds=grace_termination_period
                    ),
                )

                # Evict the pod from the node
                self.api_instance.create_namespaced_pod_eviction(
                    name=pod_name, namespace=namespace, body=eviction, pretty="true"
                )
            return True
        except client.ApiException as e:
            logger.error(f"Error scaling deployment: {e}")
            return None
