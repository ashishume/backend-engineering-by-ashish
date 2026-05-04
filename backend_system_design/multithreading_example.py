import threading
import time


def send_email(user):
    print("sending email...")
    time.sleep(3)
    print(f"{user} email sent...")


def main():
    users = ["abc@email.com", "abc2@email.com", "abc4@email.com"]
    threads = []

    for user in users:
        t = threading.Thread(target=send_email, args=(user,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    print("all emails sent")


if __name__ == "__main__":
    main()
