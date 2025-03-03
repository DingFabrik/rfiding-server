from people.models import Person
from tokens.models import Token
from machines.models import Machine
from access_log.models import AccessLog


class WidgetDataProvider():
    data = {}
    
    def prepare_token_counts(self):
        if "activeTokenCount" not in self.data:
            self.data["activeTokenCount"] = Token.objects.filter(is_active=True).count()
        if "tokenCount" not in self.data:
            self.data["tokenCount"] = Token.objects.count()
    
    def prepare_machine_counts(self):
        if "activeMachineCount" not in self.data:
            self.data["activeMachineCount"] = Machine.objects.filter(is_active=True).count()
        if "machineCount" not in self.data:
            self.data["machineCount"] = Machine.objects.count()
    
    def prepare_person_counts(self):
        if "activePeopleCount" not in self.data:
            self.data["activePeopleCount"] = Person.objects.filter(is_active=True).count()
        if "peopleCount" not in self.data:
            self.data["peopleCount"] = Person.objects.count()
            
    def prepare_access_log_latest(self):
        if "latestAccessLog" not in self.data:
            self.data["latestAccessLog"] = AccessLog.objects.all()
    
    def provide_for_widgets(self, widgets):
        for widget in widgets:
            if widget.widget == "token_counts":
                self.prepare_token_counts()
                widget.data = {
                    "active_count": self.data["activeTokenCount"],
                    "total_count": self.data["tokenCount"]
                }
            elif widget.widget == "machine_counts":
                self.prepare_machine_counts()
                widget.data = {
                    "active_count": self.data["activeMachineCount"],
                    "total_count": self.data["machineCount"]
                }
            elif widget.widget == "people_counts":
                self.prepare_person_counts()
                widget.data = {
                    "active_count": self.data["activePeopleCount"],
                    "total_count": self.data["peopleCount"]
                }
            elif widget.widget == "access_log_latest":
                self.prepare_access_log_latest()
                widget.data = {
                    "log_entries": self.data["latestAccessLog"][:10]
                }