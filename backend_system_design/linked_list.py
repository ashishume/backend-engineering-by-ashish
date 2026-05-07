class Node:
    def __init__(self, data):
        self.data = data
        self.next = None


class LinkedList:
    def __init__(self):
        self.head = None

    def append(self, data):
        node = Node(data)
        if not self.head:
            self.head = node
            return

        curr = self.head
        while curr.next:
            curr = curr.next

        curr.next = node

    def insert_at_start(self, data):
        curr = self.head
        new_node = Node(data)
        new_node.next = curr
        self.head = new_node

    def print_list(self):
        curr = self.head

        while curr:
            print(curr.data)
            curr = curr.next

    def get(self, index: int) -> int:
        curr = self.head
        i = 0
        while i <= index:
            curr = curr.next
            i += 1

        return curr.data

    def add_at_index(self, index, data):
        node = Node(data)
        curr = self.head

        if index == 0:
            node.next = curr
            self.head = node
            return

        i = 0
        while i < index - 1:
            curr = curr.next
            i += 1

        node.next = curr.next
        curr.next = node


ll = LinkedList()

ll.append(1)
ll.append(2)
ll.append(3)
# ll.insert_at_start(4)

# ll.add_at_tail(6)

# print(ll.get(1))

ll.add_at_index(0, 9)

ll.print_list()
