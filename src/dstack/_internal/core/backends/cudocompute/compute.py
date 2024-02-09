from typing import List, Optional

from dstack._internal.core.backends.base import Compute
from dstack._internal.core.backends.base.compute import get_shim_commands
from dstack._internal.core.backends.base.offers import get_catalog_offers
from dstack._internal.core.backends.cudocompute.api_client import CudoComputeApiClient
from dstack._internal.core.backends.cudocompute.config import CudoComputeConfig
from dstack._internal.core.models.backends.base import BackendType
from dstack._internal.core.models.instances import (
    InstanceAvailability,
    InstanceOfferWithAvailability,
    LaunchedInstanceInfo,
)
from dstack._internal.core.models.runs import Job, Requirements, Run


class CudoComputeCompute(Compute):
    def __init__(self, config: CudoComputeConfig):
        self.config = config
        self.api_client = CudoComputeApiClient(config.creds.api_key)

    def get_offers(
        self, requirements: Optional[Requirements] = None
    ) -> List[InstanceOfferWithAvailability]:
        offers = get_catalog_offers(
            backend=BackendType.CUDOCOMPUTE,
            requirements=requirements,
        )
        offers = [
            InstanceOfferWithAvailability(
                **offer.dict(), availability=InstanceAvailability.AVAILABLE
            )
            for offer in offers
        ]
        return offers

    def run_job(
        self,
        run: Run,
        job: Job,
        instance_offer: InstanceOfferWithAvailability,
        project_ssh_public_key: str,
        project_ssh_private_key: str,
    ) -> LaunchedInstanceInfo:
        disk_size = round(instance_offer.instance.resources.disk.size_mib / 1024)
        memory_size = round(instance_offer.instance.resources.memory_mib / 1024)

        self.api_client.get_or_create_ssh_key(project_ssh_public_key.strip())
        self.api_client.get_or_create_ssh_key(run.run_spec.ssh_key_pub.strip())

        commands = get_shim_commands(
            backend=BackendType.CUDOCOMPUTE,
            image_name=job.job_spec.image_name,
            authorized_keys=[
                run.run_spec.ssh_key_pub.strip(),
                project_ssh_public_key.strip(),
            ],
            registry_auth_required=job.job_spec.registry_auth is not None,
        )

        startup_script = " ".join([" && ".join(commands)])

        resp_data = self.api_client.create_virtual_machine(
            project_id=self.config.project_id,
            boot_disk_storage_class="STORAGE_CLASS_NETWORK",
            boot_disk_size_gib=disk_size,
            book_disk_id="dstack_disk_id",
            boot_disk_image_id="ubuntu-nvidia-docker",
            data_center_id=instance_offer.region,
            gpu_model=instance_offer.instance.resources.gpus[0].name,
            gpus=len(instance_offer.instance.resources.gpus),
            machine_type=instance_offer.instance.name,
            memory_gib=memory_size,
            vcpus=instance_offer.instance.resources.cpus,
            vm_id="dstack-vm-id",
            start_script=startup_script,
        )

        launched_instance = LaunchedInstanceInfo(
            instance_id=resp_data["id"],
            ip_address=resp_data["vm"]["nics"]["externalIpAddress"],
            region=resp_data["vm"]["regionId"],
            ssh_port=22,
            username="root",
            dockerized=True,
            backend_data=None,
        )
        return launched_instance

    def terminate_instance(
        self, instance_id: str, region: str, backend_data: Optional[str] = None
    ):
        self.api_client.terminate_virtual_machine(instance_id, self.config.project_id)
