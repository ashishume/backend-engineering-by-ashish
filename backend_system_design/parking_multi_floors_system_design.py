# Design a parking system for a parking lot.
# It may consist of multiple floors, and each floor contains a fixed number of parking spots. These spots are often categorized by vehicle size such as small, compact, or large. When a vehicle enters the parking lot, a parking ticket is issued to record the entry time. Upon exiting, the vehicle owner pays the parking fee.


# Core Domain Objects
# - ParkingLot
# - ParkingFloor
# - ParkingSpot
# - Vehicle
# - Ticket
# - Gate (Entry / Exit)
# - Payment
# - PricingStrategy

from threading import Lock
from abc import ABC, abstractmethod
from enum import Enum
import time
import uuid


class VehicleType(Enum):
    CAR = "car"
    TRUCK = "truck"
    BIKE = "bike"


class SpotType(Enum):
    CAR_PARKING = "car_parking"
    TRUCK_PARKING = "truck_parking"
    BIKE_PARKING = "bike_parking"


class TicketStatus(Enum):
    ACTIVE = "active"
    PAID = "paid"


class GateType(Enum):
    ENTRY = "entry"
    EXIT = "exit"


class Vehicle:
    def __init__(self, vehicle_type: VehicleType, vehicle_number: int):
        self.vehicle_number = vehicle_number
        self.vehicle_type = vehicle_type


class ParkingSpot(ABC):
    def __init__(self, spot_type: SpotType, spot_id: str):
        self.spot_id = spot_id
        self.spot_type = spot_type
        self.vehicle: Vehicle | None = None
        self.is_available = True
        self.lock = Lock()

    @abstractmethod
    def can_fit(self, vehicle: Vehicle):
        pass

    def park(self, vehicle: Vehicle):
        with self.lock:
            if not self.is_available:
                raise Exception("slot is already taken")
            self.vehicle = vehicle
            self.is_available = False

    def release(self):
        with self.lock:
            self.is_available = True
            self.vehicle = None


class SmallSpot(ParkingSpot):
    def can_fit(self, vehicle: Vehicle):
        return vehicle.vehicle_type == VehicleType.BIKE


class MediumSpot(ParkingSpot):
    def can_fit(self, vehicle: Vehicle):
        return vehicle.vehicle_type == VehicleType.CAR


class LargeSpot(ParkingSpot):
    def can_fit(self, vehicle: Vehicle):
        return vehicle.vehicle_type == VehicleType.TRUCK


class ParkingFloor:
    def __init__(self, floor_id: str, floor_num: str, parking_spots: list[ParkingSpot]):
        self.floor_id = floor_id
        self.floor_num = floor_num
        self.parking_spots = parking_spots
        self.lock = Lock()

    def get_available_spots(self, vehicle: Vehicle) -> ParkingSpot | None:
        with self.lock:
            for spot in self.parking_spots:
                if spot.is_available and spot.can_fit(vehicle):
                    return spot
        return None


class ParkingTicket:
    def __init__(self, ticket_id: str, parking_spot: ParkingSpot, vehicle: Vehicle):
        self.ticket_id = ticket_id
        self.vehicle: Vehicle = vehicle
        self.parking_spot = parking_spot
        self.entry_time = time.time()
        self.exit_time: float | None = None
        self.status = TicketStatus.ACTIVE


class PricingStrategy(ABC):
    @abstractmethod
    def calculate(
        self, entry_time: float, exit_time: float, vehicle_type: VehicleType
    ) -> float:
        pass


class HourlyPricing(PricingStrategy):
    RATES = {VehicleType.BIKE: 20, VehicleType.CAR: 50, VehicleType.TRUCK: 100}

    def calculate(
        self, entry_time: float, exit_time: float, vehicle_type: VehicleType
    ) -> float:
        hours = max(1, int((exit_time - entry_time) / 3600))
        return hours * self.RATES[vehicle_type]


class Gate:
    def __init__(self, gate_id: str, gate_type: GateType):
        self.gate_id = gate_id
        self.gate_type = gate_type
        self.lock = Lock()


class ParkingLot:
    def __init__(
        self,
        parking_lot_id: str,
        floors: list[ParkingFloor],
        entry_gates: list[Gate],
        exit_gates: list[Gate],
        pricing_strategy: PricingStrategy,
    ):
        self.parking_lot_id = parking_lot_id
        self.floors = floors
        self.entry_gates = entry_gates
        self.exit_gates = exit_gates
        self.pricing_strategy = pricing_strategy
        self.active_tickets: dict[str, ParkingTicket] = {}
        self.lock = Lock()

    def _find_available_spot(
        self, vehicle: Vehicle
    ) -> tuple[ParkingFloor, ParkingSpot] | None:
        # Internal method - assumes lock is already held by caller
        for floor in self.floors:
            spot = floor.get_available_spots(vehicle)
            if spot:
                return (floor, spot)
        return None

    def park_vehicle(self, gate: Gate, vehicle: Vehicle):
        if gate.gate_type != GateType.ENTRY:
            raise Exception("Invalid gate type")
        with self.lock:
            result = self._find_available_spot(vehicle)
            if not result:
                raise Exception("No available spot")
            floor, spot = result

            spot.park(vehicle)

            ticket_id = str(uuid.uuid4())

            ticket = ParkingTicket(
                ticket_id=ticket_id, parking_spot=spot, vehicle=vehicle
            )

            self.active_tickets[ticket_id] = ticket

            return ticket

    def exit_vehicle(self, ticket_id: str, gate: Gate):
        if gate.gate_type != GateType.EXIT:
            raise Exception("Invalid gate type")
        with self.lock:
            ticket = self.active_tickets.get(ticket_id)
            if not ticket:
                raise Exception("Ticket not found")

            if ticket.status != TicketStatus.ACTIVE:
                raise Exception("Ticket is not active")

            ticket.status = TicketStatus.PAID
            ticket.exit_time = time.time()

            amount = self.pricing_strategy.calculate(
                ticket.entry_time, ticket.exit_time, ticket.vehicle.vehicle_type
            )

            # process the payment based on the amount

            ticket.parking_spot.release()

            del self.active_tickets[ticket_id]

            return amount


if __name__ == "__main__":

    # Each floor needs its own unique spot instances
    floor1_spots = [
        SmallSpot(spot_id="1-1", spot_type=SpotType.BIKE_PARKING),
        MediumSpot(spot_id="1-2", spot_type=SpotType.CAR_PARKING),
        LargeSpot(spot_id="1-3", spot_type=SpotType.TRUCK_PARKING),
    ]
    floor2_spots = [
        SmallSpot(spot_id="2-1", spot_type=SpotType.BIKE_PARKING),
        MediumSpot(spot_id="2-2", spot_type=SpotType.CAR_PARKING),
        LargeSpot(spot_id="2-3", spot_type=SpotType.TRUCK_PARKING),
    ]
    floor3_spots = [
        SmallSpot(spot_id="3-1", spot_type=SpotType.BIKE_PARKING),
        MediumSpot(spot_id="3-2", spot_type=SpotType.CAR_PARKING),
        LargeSpot(spot_id="3-3", spot_type=SpotType.TRUCK_PARKING),
    ]

    floor1 = ParkingFloor(floor_id="1", floor_num="1", parking_spots=floor1_spots)
    floor2 = ParkingFloor(floor_id="2", floor_num="2", parking_spots=floor2_spots)
    floor3 = ParkingFloor(floor_id="3", floor_num="3", parking_spots=floor3_spots)

    entry_gate1 = Gate(gate_id="1", gate_type=GateType.ENTRY)
    exit_gate1 = Gate(gate_id="1", gate_type=GateType.EXIT)
    exit_gate2 = Gate(gate_id="2", gate_type=GateType.EXIT)
    exit_gate3 = Gate(gate_id="3", gate_type=GateType.EXIT)

    pricing = HourlyPricing()

    parking_lot = ParkingLot(
        "parking_Lot_id",
        [floor1, floor2, floor3],
        [entry_gate1],
        [exit_gate1, exit_gate2, exit_gate3],
        pricing,
    )

    car = Vehicle(vehicle_type=VehicleType.CAR, vehicle_number="1234")
    bike = Vehicle(vehicle_type=VehicleType.BIKE, vehicle_number="1235")
    truck = Vehicle(vehicle_type=VehicleType.TRUCK, vehicle_number="1236")

    # Test parking a car
    print("Parking a car...")
    ticket = parking_lot.park_vehicle(entry_gate1, car)
    print(
        f"Ticket issued: {ticket.ticket_id}, Spot: {ticket.parking_spot.spot_id}, Vehicle: {ticket.vehicle.vehicle_type.value}"
    )

    # Test exiting the car
    print("\nExiting the car...")
    amount = parking_lot.exit_vehicle(ticket.ticket_id, exit_gate1)
    print(f"Amount to pay: ₹{amount}")

    # Test parking a bike
    print("\nParking a bike...")
    ticket = parking_lot.park_vehicle(entry_gate1, bike)
    print(
        f"Ticket issued: {ticket.ticket_id}, Spot: {ticket.parking_spot.spot_id}, Vehicle: {ticket.vehicle.vehicle_type.value}"
    )

    print("\nAll tests completed successfully!")
