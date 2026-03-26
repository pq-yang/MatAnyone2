from matanyone2.webapp.queue import QueueCoordinator


class WorkerLoop:
    def __init__(self, coordinator: QueueCoordinator):
        self.coordinator = coordinator

    def recover(self) -> None:
        self.coordinator.recover_interrupted_jobs()
