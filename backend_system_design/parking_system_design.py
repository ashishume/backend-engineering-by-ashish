from enum import Enum
from datetime import datetime
import time


class VehicleType(Enum):
    BIKE = "bike"
    CAR = "car"
    TRUCK = "truck"


class Vehicle:
    def __init__(self, number, vehicle_type: VehicleType):
        self.number = number
        self.vehicle_type = vehicle_type


class ParkingSlot:
    def __init__(self, slot_id, vehicle_type: VehicleType):
        self.slot_id = slot_id
        self.vehicle_type = vehicle_type
        self.is_free = True

    def assign(self):
        self.is_free = False

    def release(self):
        self.is_free = True


class Ticket:
    def __init__(self, ticket_id, vehicle: Vehicle, slot: ParkingSlot):
        self.ticket_id = ticket_id
        self.vehicle = vehicle
        self.slot = slot
        self.entry_time = datetime.now()
        self.exit_time = None


class SlotManager:
    """
    Optimized slot allocation → O(1)
    """

    def __init__(self):
        self.free_slots = {
            VehicleType.BIKE: [],
            VehicleType.CAR: [],
            VehicleType.TRUCK: [],
        }

    def add_slot(self, slot: ParkingSlot):
        self.free_slots[slot.vehicle_type].append(slot)

    def get_slot(self, vehicle_type: VehicleType):
        if self.free_slots[vehicle_type]:
            return self.free_slots[vehicle_type].pop()
        return None

    def release_slot(self, slot: ParkingSlot):
        self.free_slots[slot.vehicle_type].append(slot)


class TicketService:
    def __init__(self):
        self.tickets = {}
        self.counter = 1

    def create_ticket(self, vehicle, slot):
        ticket = Ticket(self.counter, vehicle, slot)
        self.tickets[self.counter] = ticket
        self.counter += 1
        return ticket

    def get_ticket(self, ticket_id):
        return self.tickets.get(ticket_id)


class PricingStrategy:
    def calculate(self, ticket: Ticket):
        raise NotImplementedError


class HourlyPricing(PricingStrategy):
    def calculate(self, ticket: Ticket):
        duration_seconds = (datetime.now() - ticket.entry_time).seconds
        hours = duration_seconds // 3600 + 1
        return hours * 20  # ₹20/hour


class PaymentService:
    def pay(self, amount):
        print(f"[PAYMENT] ₹{amount} paid successfully")
        return True


class Gate:
    def open(self):
        print("[GATE OPENED]")


class ParkingLot:
    def __init__(self):
        self.slot_manager = SlotManager()
        self.ticket_service = TicketService()
        self.pricing = HourlyPricing()
        self.payment = PaymentService()
        self.gate = Gate()

    def add_slot(self, slot: ParkingSlot):
        self.slot_manager.add_slot(slot)

    def park_vehicle(self, vehicle: Vehicle):
        slot = self.slot_manager.get_slot(vehicle.vehicle_type)

        if not slot:
            print("[FULL] No slots available")
            return None

        slot.assign()
        ticket = self.ticket_service.create_ticket(vehicle, slot)

        self.gate.open()
        print(f"[ENTRY] Ticket ID: {ticket.ticket_id}, Slot: {slot.slot_id}")

        return ticket

    def exit_vehicle(self, ticket_id):
        ticket = self.ticket_service.get_ticket(ticket_id)

        if not ticket:
            print("[ERROR] Invalid ticket")
            return

        amount = self.pricing.calculate(ticket)

        if self.payment.pay(amount):
            ticket.exit_time = datetime.now()
            ticket.slot.release()
            self.slot_manager.release_slot(ticket.slot)

            self.gate.open()
            print(f"[EXIT] Vehicle {ticket.vehicle.number} exited")


if __name__ == "__main__":
    parking_lot = ParkingLot()

    # Add slots
    for i in range(3):
        parking_lot.add_slot(ParkingSlot(i, VehicleType.CAR))

    for i in range(3, 5):
        parking_lot.add_slot(ParkingSlot(i, VehicleType.BIKE))

    # Vehicle enters
    vehicle1 = Vehicle("KA01AB1234", VehicleType.CAR)
    ticket1 = parking_lot.park_vehicle(vehicle1)

    # Simulate time passing
    time.sleep(2)

    # Vehicle exits
    if ticket1:
        parking_lot.exit_vehicle(ticket1.ticket_id)
