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
    grace_termination_period: int = 30,
) -> None:
    """
    Migrates workload from the source node pool to the destination node pool.

    Args:
        subscription_id (str): Azure subscription ID.
        resource_group (str): Resource group of the AKS cluster.
        cluster_name (str): Name of the AKS cluster.
        source_pool (str): Name of the source node pool.
        destination_pool (str): Name of the destination node pool.
        grace_termination_period (int): Grace period in seconds for pod termination.

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

        # drain nodes in source pool
        nodes = node_manager.list_nodes()
        if nodes is not None:
            for node in nodes.items:
                # Here it's assumed that node name and node pool name are same
                if node.metadata.name == source_pool:
                    if node_manager.drain_node(
                        node.metadata.name, grace_termination_period
                    ):
                        logging.info(f"Successfully drained node {node.metadata.name}")
                    else:
                        logging.error(f"Failed to drain node {node.metadata.name}")
        else:
            logging.error(f"Failed to get nodes in the cluster")
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
