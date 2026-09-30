from __future__ import annotations


class BGIO:
    def __init__(self, io_manager, config):
        self.io = io_manager
        self.config = config

    def read_door(self):
        return self.io.read_input(self.config.inputChannel)

    def set_alarm(self, value):
        return self.io.write_output(self.config.outputAlarm, bool(value))

    def set_relay(self, value):
        return self.io.write_output(self.config.outputContor, bool(value))

    def set_state_machine(self, value):
        return self.io.write_output(self.config.outputStateMachine, bool(value))

    def reset_outputs(self):
        self.set_alarm(False)
        self.set_relay(False)
        self.set_state_machine(False)
