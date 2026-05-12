class PublishEvent:
    def __init__(self):
        self.events = {}

    def subscribe(self, event_type, handler):
        if event_type not in self.events:
            self.events[event_type] = []

        self.events[event_type].append(handler)

    def publish(self, event_type, data):
        handlers = self.events.get(event_type, [])

        for handler in handlers:
            handler(data)


ev = PublishEvent()


def create_order(order_id, user_id):
    print(f"[Order] Order created: {order_id}")

    event = {"order_id": order_id, "user_id": user_id}

    ev.publish("OrderPlaced", event)


def order_placed(data):
    print(f"order placed {data}")


def payment_processed(data):
    print(f"payment processed {data}")


def send_mail(data):
    print(f"send mail {data}")


ev.subscribe("OrderPlaced", order_placed)
ev.subscribe("OrderPlaced", payment_processed)
ev.subscribe("OrderPlaced", send_mail)
create_order(101, 1)
