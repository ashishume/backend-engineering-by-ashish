from datetime import datetime
from enum import Enum
from traceback import print_tb


class Visitor:
    def __init__(self, name: str, phone: int):
        self.name = name
        self.phone = phone


class User:
    def __init__(self, id: str, name: int):
        self.id = id
        self.name = name


class Flat:
    def __init__(self, flat_no: int, owner: User):
        self.user = owner
        self.flat_no = flat_no


class VisitStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"


class VisitRequest:
    def __init__(
        self,
        request_id: str,
        visitor: Visitor,
        flat: Flat,
    ):
        self.request_id = request_id
        self.visitor = visitor
        self.status = VisitStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.flat = flat


class VisitorService:
    def __init__(self):
        self.requests = {}
        self.counter = 1

    def create_request(self, visitor, flat):
        req = VisitRequest(self.counter, visitor, flat)
        self.requests[self.counter] = req
        self.counter += 1
        return req

    def get_requests(self, request_id: str):
        return self.requests.get(request_id)


class NotificationService:
    def notify_owner(self, flat: Flat, message: str):
        print(f"notify {flat.user.name}:{message}")


class ApprovalService:
    def approve(self, request: VisitRequest):
        request.status = VisitStatus.APPROVED

    def reject(self, request: VisitRequest):
        request.status = VisitStatus.REJECTED


class EntryService:
    def check_in(self, request: VisitRequest):
        if request.status != VisitStatus.APPROVED:
            raise Exception("Unthorised entry")

        request.start_time = datetime.now()
        print("visitor entered")

    def check_out(self, request: VisitRequest):
        request.end_time = datetime.now()
        request.status = VisitStatus.COMPLETED
        print("visit exited")


def complete_flow(
    visitor_service,
    notification_service,
    entry_service,
    approval_service,
):

    visitor = Visitor("Akash", 290820)
    owner = User(2, "Ashish")
    flat = Flat(313, owner)
    req = visitor_service.create_request(visitor, flat)
    notification_service.notify_owner(flat, "Delivery waiting")
    approval_service.approve(req)
    entry_service.check_in(req)


visitor_service = VisitorService()
notification_service = NotificationService()
approval_service = ApprovalService()
entry_service = EntryService()

complete_flow(
    visitor_service,
    notification_service,
    entry_service,
    approval_service,
)
