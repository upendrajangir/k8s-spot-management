import logging
import time
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.containerservice.models import AgentPool
from typing import Optional


class AzureNodeScaler:
    def __init__(self, subscription_id: str):
        self.subscription_id = subscription_id
        self.credential = DefaultAzureCredential()
        self.client = ContainerServiceClient(
            credential=self.credential, subscription_id=self.subscription_id
        )

    def get_node_pool(
        self, resource_group_name: str, cluster_name: str, node_pool_name: str
    ) -> Optional[AgentPool]:
        try:
            return self.client.agent_pools.get(
                resource_group_name, cluster_name, node_pool_name
            )
        except ResourceNotFoundError:
            logging.error(f"Node pool {node_pool_name} not found.")
            return None

    def increment_node_pool(
        self,
        resource_group_name: str,
        cluster_name: str,
        node_pool_name: str,
    ) -> bool:
        node_pool = self.get_node_pool(
            resource_group_name, cluster_name, node_pool_name
        )
        if node_pool is None:
            return False

        current_count = node_pool.count
        new_count = current_count + 1
        return self.scale_node_pool_manual(
            resource_group_name, cluster_name, node_pool_name, new_count
        )

    def decrement_node_pool(
        self,
        resource_group_name: str,
        cluster_name: str,
        node_pool_name: str,
    ) -> bool:
        node_pool = self.get_node_pool(
            resource_group_name, cluster_name, node_pool_name
        )
        if node_pool is None:
            return False

        if node_pool.count <= 0:
            logging.error(f"Node pool {node_pool_name} has no nodes to remove.")
            return False

        new_count = node_pool.count - 1
        return self.scale_node_pool_manual(
            resource_group_name, cluster_name, node_pool_name, new_count
        )

    def set_auto_scaling(
        self,
        resource_group_name: str,
        cluster_name: str,
        node_pool_name: str,
        min_count: int,
        max_count: int,
    ) -> bool:
        try:
            poller = self.client.agent_pools.begin_create_or_update(
                resource_group_name=resource_group_name,
                resource_name=cluster_name,
                agent_pool_name=node_pool_name,
                parameters={
                    "properties": {
                        "enableAutoScaling": True,
                        "minCount": min_count,
                        "maxCount": max_count,
                        "type": "VirtualMachineScaleSets",
                    }
                },
            )

            while not poller.done():
                print(f"Operation status: {poller.status()}")
                time.sleep(5)

            if poller.status() == "Succeeded":
                logging.info(
                    f"Set auto scaling for node pool {node_pool_name} with min: {min_count}, max: {max_count}"
                )
                return True
            else:
                logging.error(
                    f"Failed to set auto scaling for node pool {node_pool_name}"
                )
                return False

        except Exception as e:
            logging.error(
                f"Exception while setting auto scaling for node pool {node_pool_name}: {str(e)}"
            )
            return False

    def scale_node_pool_manual(
        self,
        resource_group_name: str,
        cluster_name: str,
        node_pool_name: str,
        node_count: int,
    ) -> bool:
        try:
            poller = self.client.agent_pools.begin_create_or_update(
                resource_group_name=resource_group_name,
                resource_name=cluster_name,
                agent_pool_name=node_pool_name,
                parameters={
                    "properties": {
                        "count": node_count,
                        "enableAutoScaling": False,
                    }
                },
            )

            while not poller.done():
                print(f"Operation status: {poller.status()}")
                time.sleep(5)

            if poller.status() == "Succeeded":
                logging.info(
                    f"Scaled node pool {node_pool_name} to {node_count} nodes."
                )
                return True
            else:
                logging.error(f"Failed to scale node pool {node_pool_name}")
                return False

        except Exception as e:
            logging.error(
                f"Exception while scaling node pool {node_pool_name}: {str(e)}"
            )
            return False


# scaler = AzureNodeScaler("d4e53310-d7ea-4386-8e45-a6f2f328f977")
# # scaler.get_node_pool("rg-gg-demo-eus-001", "aks-gg-demo-eus-001", "userpool02")
# # scaler.decrement_node_pool("rg-gg-demo-eus-001", "aks-gg-demo-eus-001", "userpool02")
# scaler.set_auto_scaling("rg-gg-demo-eus-001", "aks-gg-demo-eus-001", "userpool02", 1, 3)
