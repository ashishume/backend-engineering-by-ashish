from collections import defaultdict
import threading


class MessageQueue:
    def __init__(self):
        self.offsets=defaultdict(dict)
        self.messages=defaultdict(list)
        self.locks=defaultdict(threading.Lock)

    def subscribe(self,consumer,key):
        with self.locks[key]:
            if key not in self.offsets[consumer]:
                self.offsets[consumer][key]=0


            
    def publish(self,key,value):
        with self.locks[key]:
             self.messages[key].append(value)   

    def poll(self,consumer,key):
        with self.locks[key]:
            if key not in self.offsets[consumer]:
                return None
            offset= self.offsets[consumer][key]
            if offset>=len(self.messages[key]):
                return None
            msg= self.messages[key][offset] 
            self.offsets[consumer][key]+=1
            return msg



if __name__ == "__main__":
    mq=MessageQueue()
    mq.subscribe("consumer1","key1")
    mq.publish("key1","message1")
    mq.publish("key1","message2")
    mq.publish("key1","message3")
    print(mq.poll("consumer1","key1"))
    print(mq.poll("consumer1","key1"))