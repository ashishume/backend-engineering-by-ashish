from enum import Enum
from threading import Lock
import threading


class RideStatus(Enum):
    REQUESTED = "REQUESTED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class Ride:
    def __init__(self, ride_id, user_id):
        self.ride_id = ride_id
        self.user_id = user_id
        self.driver_id = None
        self.status = RideStatus.REQUESTED


class Driver:
    def __init__(self, driver_id):
        self.driver_id = driver_id


class RideRepository:
    def __init__(self):
        self.rides = {}
        self.lock = Lock()  # DB-level lock simulation

    def create_ride(self, ride: Ride):
        self.rides[ride.ride_id] = ride

    def get_ride(self, ride_id):
        return self.rides.get(ride_id)

    def confirm_ride(self, ride_id, driver_id):
        """
        Atomic DB update simulation
        """
        with self.lock:
            ride = self.rides.get(ride_id)
            if ride and ride.status == RideStatus.REQUESTED:
                ride.status = RideStatus.CONFIRMED
                ride.driver_id = driver_id
                return True
            return False


class LockManager:
    def __init__(self):
        self.locks = {}
        self.global_lock = Lock()

    def acquire_lock(self, key):
        with self.global_lock:
            if key not in self.locks:
                self.locks[key] = True
                return True
            return False

    def release_lock(self, key):
        with self.global_lock:
            if key in self.locks:
                del self.locks[key]


class RideService:
    def __init__(self, ride_repo: RideRepository, lock_manager: LockManager):
        self.ride_repo = ride_repo
        self.lock_manager = lock_manager

    def accept_ride(self, ride_id, driver_id):
        lock_key = f"ride_lock:{ride_id}"

        # Step 1: Try acquiring distributed lock
        if not self.lock_manager.acquire_lock(lock_key):
            return f"Driver {driver_id}: Failed ❌ (Lock not acquired)"

        try:
            # Step 2: Atomic DB update
            success = self.ride_repo.confirm_ride(ride_id, driver_id)

            if success:
                return f"Driver {driver_id}: SUCCESS ✅"
            else:
                return f"Driver {driver_id}: Failed ❌ (Already taken)"
        finally:
            self.lock_manager.release_lock(lock_key)


def simulate_driver_accept(ride_service, ride_id, driver_id):
    result = ride_service.accept_ride(ride_id, driver_id)
    print(result)


# Setup
ride_repo = RideRepository()
lock_manager = LockManager()
ride_service = RideService(ride_repo, lock_manager)

ride = Ride("ride_1", "user_1")
ride_repo.create_ride(ride)

# Simulate multiple drivers accepting simultaneously
threads = []
for i in range(5):
    t = threading.Thread(
        target=simulate_driver_accept, args=(ride_service, "ride_1", f"driver_{i}")
    )
    threads.append(t)
    t.start()

for t in threads:
    t.join()
