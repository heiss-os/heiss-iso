class FakeSystem:
    def __init__(self, installed=(), explicit=None, required_by=None, services=(), flatpaks=(), files=None, kde=None, online=True):
        self.installed = set(installed)
        self.explicit = set(installed if explicit is None else explicit)
        self.deps = required_by or {}
        self.services = set(services)
        self.flatpaks = set(flatpaks)
        self.files = files or {}
        self.online = online
        self.kde = kde or {}

    def installed_packages(self): return set(self.installed)
    def explicit_packages(self): return set(self.explicit)
    def required_by(self, pkg): return set(self.deps.get(pkg, ()))
    def enabled_services(self): return set(self.services)
    def installed_flatpaks(self): return set(self.flatpaks)
    def read_text(self, path): return self.files.get(path)
    def kde_value(self, file, group, key): return self.kde.get((file, group, key))
    def network_connected(self): return self.online
