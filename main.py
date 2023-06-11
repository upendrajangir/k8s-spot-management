import logging
from typing import Optional

from azure.nodepool import AzureNodeScaler
from k8s.node import NodeManager

logging.basicConfig(level=logging.INFO)


def migrate_workload(
    subscription_id: str,
    resource_group: str,
    cluster_name: str,
    source_pool: str,
    destination_pool: str,
) -> None:
    """
    Migrates workload from the source node pool to the destination node pool.

    Args:
        subscription_id (str): Azure subscription ID.
        resource_group (str): Resource group of the AKS cluster.
        cluster_name (str): Name of the AKS cluster.
        source_pool (str): Name of the source node pool.
        destination_pool (str): Name of the destination node pool.

    Returns:
        None
    """
    # Instantiate AzureNodeScaler with the provided subscription ID
    scaler = AzureNodeScaler(subscription_id)

    # Instantiate NodeManager
    node_manager = NodeManager()

    # Scale destination pool
    if scaler.increment_node_pool(resource_group, cluster_name, destination_pool):
        logging.info(f"Successfully scaled node pool {destination_pool}")

        # Get list of pods in source pool (excluding kube-system namespace)
        pod_list = node_manager.list_pods_by_nodepool(
            source_pool, exclude_namespaces=["kube-system"]
        )

        if pod_list and pod_list.items:
            logging.info(f"Found {len(pod_list.items)} pods in node pool {source_pool}")

            # Evict pods from source pool and schedule them on the destination pool
            for pod in pod_list.items:
                if node_manager.evict_pod_from_nodepool(
                    pod.metadata.name, pod.metadata.namespace, source_pool
                ):
                    logging.info(
                        f"Evicted pod {pod.metadata.name} to node pool {source_pool}"
                    )
                else:
                    logging.error(
                        f"Failed to evict pod {pod.metadata.name} to node pool {source_pool}"
                    )
        else:
            logging.info(
                f"No pods found in node pool {source_pool} (excluding kube-system namespace)"
            )
    else:
        logging.error(f"Failed to scale node pool {destination_pool}")


if __name__ == "__main__":
    # Set your desired values for the variables
    subscription_id = "d4e53310-d7ea-4386-8e45-a6f2f328f977"
    resource_group = "rg-gg-demo-eus-001"
    cluster_name = "aks-gg-demo-eus-001"
    source_pool = "userpool02"
    destination_pool = "userpool01"

    migrate_workload(
        subscription_id, resource_group, cluster_name, source_pool, destination_pool
    )
