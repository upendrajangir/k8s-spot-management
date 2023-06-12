import logging
import time
import os
from typing import Optional

from azure.nodepool import AzureNodeScaler
from k8s.node import NodeManager
from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
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


def schedule_migrate_workload():
    # Get values from environment variables
    subscription_id = os.getenv("SUBSCRIPTION_ID", "")
    resource_group = os.getenv("RESOURCE_GROUP", "")
    cluster_name = os.getenv("CLUSTER_NAME", "")
    source_pool = os.getenv("SOURCE_POOL", "")
    destination_pool = os.getenv("DESTINATION_POOL", "")

    migrate_workload(
        subscription_id, resource_group, cluster_name, source_pool, destination_pool
    )


scheduler = BackgroundScheduler()
scheduler.add_job(func=schedule_migrate_workload, trigger="interval", seconds=60)
scheduler.start()


@app.route("/")
def hello():
    return "Hello, World!"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
