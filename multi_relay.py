import hid
from multiprocessing import Queue, Process

class Relay:
    def __init__(self, idVendor=0x16c0, idProduct=0x05df):
        self.h = hid.device()
        self.h.open(idVendor, idProduct)
        self.h.set_nonblocking(1)

    def get_switch_statuses_from_report(self, report):

        # Grab the 8th number, which is a integer
        switch_statuses = report[7]

        # Convert the integer to a binary, and the binary to a list.
        switch_statuses = [int(x) for x in list('{0:08b}'.format(switch_statuses))]

        # Reverse the list, since the status reads from right to left
        switch_statuses.reverse()

        # The switch_statuses now looks something like this:
        # [1, 1, 0, 0, 0, 0, 0, 0]
        # Switch 1 and 2 (index 0 and 1 respectively) are on, the rest are off.

        return switch_statuses

    def send_feature_report(self, message):
        self.h.send_feature_report(message)

    def get_feature_report(self):
        # If 0 is passed as the feature, then 0 is prepended to the report. However,
        # if 1 is passed, the number is not added and only 8 chars are returned.
        feature = 1
        # This is the length of the report.
        length = 8
        return self.h.get_feature_report(feature, length)

    def state(self, relay, on=None):
        # Getter
        if on == None:
            if relay == 0:
                report = self.get_feature_report()
                switch_statuses = self.get_switch_statuses_from_report(report)
                status = []
                for s in switch_statuses:
                    status.append(bool(s))
            else:
                report = self.get_feature_report()
                switch_statuses = self.get_switch_statuses_from_report(report)
                status = bool(switch_statuses[relay - 1])

            return status

        # Setter
        else:
            if relay == 0:
                if on:
                    message = [0xFE]
                else:
                    message = [0xFC]
            else:
                if on:
                    message = [0xFF, relay]
                else:
                    message = [0xFD, relay]

            self.send_feature_report(message)


class Reject_sys:
    def __init__(self, Q, A_wait, B_wait, A_run, B_run):
        self.relay = Relay(idVendor=0x16c0, idProduct=0x05df)
        self.relay.state(0, False)

        self.relay_status_A = 'off'
        self.relay_status_B = 'off'
        self.queue = Q

        self.Time_out = 0.01

        """ 필요한 시간이 되기까지 대기하는 시간 """
        self.reject_need_time_A = int(A_wait / self.Time_out)
        self.reject_need_time_B = int(B_wait / self.Time_out)

        """ 릴레이 작동 시간 설정 """
        standby_time_A = int(A_run / self.Time_out)
        standby_time_B = int(B_run / self.Time_out)

        self.T_A = [0] * (self.reject_need_time_A + standby_time_A)
        self.T_B = [0] * (self.reject_need_time_B + standby_time_B)

        print(len(self.T_A), self.reject_need_time_A )
        print(len(self.T_A[self.reject_need_time_A:]))

        self.get_Queue()

    def get_Queue(self):
        """ Queue를 받아서 릴레이 가동을 위한 본 프로그램 """

        while True:
            answer = ''

            try:
                answer = self.queue.get(timeout=self.Time_out)

                if answer == 'r':
                    self.T_A = self.time_traveler('A', 0, 1)
                    self.T_B = self.time_traveler('B', 0, 1)

                elif answer == 'q':
                    self.relay.state(0, False)
                    break

            except:
                self.T_A = self.time_traveler('A', 0, 0)
                self.T_B = self.time_traveler('B', 0, 0)

            self.action()

    def time_traveler(self, line, location, pass_):
        """ 타임테이블 한칸씩 오른쪽으로 이동시키기 """
        if line == 'A':
            temp = self.T_A
        else:
            temp = self.T_B
        temp = temp[:-1]
        temp.insert(location, pass_)

        return temp

    def state_on(self, i):
        """ i에 해당되는 릴레이가 꺼져 있으면 가동하고 현재의 시간을 저장 """
        if i == 1:
            self.relay.state(1, True)
            self.relay_status_A = 'on'

        elif i == 2:
            self.relay.state(2, True)
            self.relay_status_B = 'on'

    def state_off(self, i):
        """ i에 해당되는 릴레이가 꺼져 있으면 가동하고 현재의 시간을 저장 """
        if i == 1:
            self.relay.state(1, False)
            self.relay_status_A = 'off'

        elif i == 2:
            self.relay.state(2, False)
            self.relay_status_B = 'off'

    def action(self):
        if 1 in self.T_A[self.reject_need_time_A:] and self.relay_status_A == 'off':
            self.state_on(1)

        if 1 not in self.T_A and self.relay_status_A == 'on':
            self.state_off(1)

        if 1 in self.T_B[self.reject_need_time_B:] and self.relay_status_B == 'off':
            self.state_on(2)

        if 1 not in self.T_B and self.relay_status_B == 'on':
            self.state_off(2)


if __name__ == '__main__':

    task_queue = Queue()
    A_wait = 4
    B_wait = 4
    A_run = 1
    B_run = 1

    R = Process(target=Reject_sys, args=(task_queue, A_wait, B_wait, A_run, B_run,))
    R.start()

    text = ''
    while True:
        text = input('Insert data (Ex, r:Reject, q:Quit)..\n')
        task_queue.put(text)
        if text == 'q':
            break
