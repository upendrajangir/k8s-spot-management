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
        """
        Lists all nodes in the Kubernetes cluster.

        Returns:
            Optional[client.V1DeploymentList]: List of nodes in the cluster.
        """
        try:
            return self.api_instance.list_node(watch=False).items
        except client.ApiException as e:
            logger.error(f"Error listing nodes: {e}")
            return None

    def get_node(self, name: str) -> Optional[client.V1Deployment]:
        """
        Retrieves information about a specific node in the Kubernetes cluster.

        Args:
            name (str): Name of the node.

        Returns:
            Optional[client.V1Deployment]: Information about the node.
        """
        try:
            return self.api_instance.read_node(name=name)
        except client.ApiException as e:
            logger.error(f"Error getting node: {e}")
            return None

    def scale_nodes(
        self, nodepool_name: str, replicas: str
    ) -> Optional[client.V1Deployment]:
        """
        Scales the number of nodes in a specific node pool.

        Args:
            nodepool_name (str): Name of the node pool.
            replicas (str): Number of replicas/nodes to scale to.

        Returns:
            Optional[client.V1Deployment]: Result of scaling operation.
        """
        try:
            # TODO: Write logic for scaling nodes
            return self.api_instance.create_namespaced_deployment(
                namespace=namespace, body=deployment
            )
        except client.ApiException as e:
            logger.error(f"Error scaling nodes: {e}")
            return None

    def delete_node(self, name: str) -> bool:
        """
        Deletes a node from the Kubernetes cluster.

        Args:
            name (str): Name of the node to delete.

        Returns:
            bool: True if the node is successfully deleted, False otherwise.
        """
        try:
            self.api_instance.delete_node(name=name)
            return True
        except client.ApiException as e:
            logger.error(f"Error deleting node: {e}")
            return False

    def drain_node(self, name: str, grace_termination_period: int) -> Optional[bool]:
        """
        Drains a node by evicting and deleting the pods running on it.

        Args:
            name (str): Name of the node to drain.
            grace_termination_period (int): Grace period in seconds for pod termination.

        Returns:
            Optional[bool]: True if the node is successfully drained, False otherwise.
        """
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

            # Reset the taints on the node
            body = {"spec": {"taints": []}}
            self.api_instance.patch_node(name, body)

            # Make the node schedulable again
            body = {"spec": {"unschedulable": False}}

            # Update the node status to schedulable
            self.api_instance.patch_node(name, body)

            return True
        except client.ApiException as e:
            logger.error(f"Error draining node: {e}")
            return None

    def list_pods_by_nodepool(
        self, node_pool_name: str, exclude_namespaces: Optional[list[str]] = None
    ) -> Optional[client.V1PodList]:
        """
        Lists pods running on a specific node pool.

        Args:
            node_pool_name (str): Name of the node pool.
            exclude_namespaces (Optional[list[str]]): List of namespaces to exclude. Default is None.

        Returns:
            Optional[client.V1PodList]: List of pods running on the specified node pool.
        """
        try:
            field_selector = f"spec.nodeName={node_pool_name}"
            if exclude_namespaces:
                field_selector += "," + ",".join(
                    [f"metadata.namespace!={ns}" for ns in exclude_namespaces]
                )

            return self.api_instance.list_pod_for_all_namespaces(
                field_selector=field_selector, watch=False
            )
        except client.ApiException as e:
            logger.error(f"Error listing pods: {e}")
            return None

    def evict_pod_to_nodepool(
        self, pod_name: str, namespace: str, node_pool_name: str
    ) -> bool:
        """
        Evicts a pod from its current node pool and schedules it on a different node pool.

        Args:
            pod_name (str): Name of the pod.
            namespace (str): Namespace of the pod.
            node_pool_name (str): Name of the destination node pool.

        Returns:
            bool: True if the pod is successfully evicted and scheduled on the destination node pool, False otherwise.
        """
        try:
            body = {"spec": {"nodeName": node_pool_name}}

            self.api_instance.patch_namespaced_pod(
                name=pod_name, namespace=namespace, body=body
            )

            return True
        except client.ApiException as e:
            logger.error(f"Error evicting pod: {e}")
            return False
