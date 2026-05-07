from tracemalloc import start


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

    def middleNode(self):
        slow = self.head
        fast = self.head
        while slow and fast.next:
            slow = slow.next
            fast = fast.next.next

        return slow.data

    def reverseList(self):
        curr = self.head
        prev = None
        while curr:
            next_node = curr.next
            curr.next = prev
            prev = curr
            curr = next_node
        return prev

    def swapKthNode(self, k):
        curr = self.head
        count = 0
        while curr:
            curr = curr.next
            count += 1

        curr = self.head

        first_prev = None
        first = self.head
        for _ in range(k - 1):
            first_prev = first
            first = first.next

        second_prev = None
        second = self.head
        for _ in range(count - k):
            second_prev = second
            second = second.next

        if first_prev:
            first_prev.next = second

        if second_prev:
            second_prev.next = first

        temp = first.next
        first.next = second.next
        second.next = temp

        if k == 1:
            self.head = second

        if k == count:
            self.head = first
        return self.head


ll = LinkedList()

ll.append(1)
ll.append(2)
ll.append(3)
ll.append(4)
ll.append(5)
# ll.insert_at_start(4)

# ll.add_at_tail(6)

# print(ll.get(1))

# ll.add_at_index(0, 9)


# ll.print_list()

# print("middle")
# print(ll.reverseList())

head = ll.swapKthNode(2)

while head:
    print(head.data)
    head = head.next
# ll.print_list()
