"""Nothing in the live image phones home on its own: the enabled units are a fixed list,
cloud-init and the live sshd are gone, and the three "quiet by default" files are in place."""
import json
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AIROOTFS = os.path.join(REPO, "profile", "airootfs")
SYSTEMD = os.path.join(AIROOTFS, "etc", "systemd", "system")

# Every unit the live image enables through a *.wants link. A new link here is a decision:
# add it to this list together with a DECISIONS entry that says what it talks to.
ENABLED = {
    "multi-user.target.wants": {
        "choose-mirror.service", "hv_fcopy_daemon.service", "hv_kvp_daemon.service", "hv_vss_daemon.service",
        "livecd-talk.service", "ModemManager.service", "NetworkManager.service", "pacman-init.service",
        "systemd-resolved.service", "vboxservice.service", "vmtoolsd.service", "vmware-vmblock-fuse.service",
    },
    "sockets.target.wants": {"pcscd.socket"},
    "sound.target.wants": {"livecd-alsa-unmuter.service"},
    "sysinit.target.wants": {"systemd-timesyncd.service", "systemd-time-wait-sync.service"},
}
# Units that are never enabled in the image: each one would talk to a remote host at boot.
NEVER = {"sshd.service", "reflector.service", "reflector.timer", "pkgstats.timer", "cloud-init.target",
         "cloud-init-main.service", "cloud-init-local.service", "cloud-init-network.service",
         "cloud-config.service", "cloud-final.service", "apparmor.service"}


def packages(name):
    with open(os.path.join(REPO, "profile", name), encoding="utf-8") as f:
        return [l.split("#")[0].strip() for l in f if l.split("#")[0].strip()]


def settings(path):
    """Non-empty, non-comment lines of an ini-style file."""
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


class EnabledUnits(unittest.TestCase):
    def wants_dirs(self):
        return sorted(d for d in os.listdir(SYSTEMD) if d.endswith(".wants"))

    def test_enabled_units_are_exactly_the_listed_ones(self):
        found = {d: set(os.listdir(os.path.join(SYSTEMD, d))) for d in self.wants_dirs()}
        self.assertEqual(found, ENABLED)

    def test_no_phone_home_unit_is_enabled_anywhere(self):
        for d in self.wants_dirs():
            self.assertEqual(set(os.listdir(os.path.join(SYSTEMD, d))) & NEVER, set(), d)
        self.assertFalse(os.path.exists(os.path.join(SYSTEMD, "cloud-init.target.wants")))

    def test_every_wants_link_points_at_a_unit_that_exists_in_the_image_or_a_package(self):
        # links into /etc/systemd/system must resolve inside airootfs; links into /usr/lib are package units
        for d in self.wants_dirs():
            for name in os.listdir(os.path.join(SYSTEMD, d)):
                target = os.readlink(os.path.join(SYSTEMD, d, name))
                if target.startswith("/usr/lib/systemd/system/"):
                    continue
                resolved = os.path.normpath(os.path.join(SYSTEMD, d, target)) if not target.startswith("/") \
                    else os.path.join(AIROOTFS, target.lstrip("/"))
                self.assertTrue(os.path.isfile(resolved), "%s/%s -> %s" % (d, name, target))


class LivePackages(unittest.TestCase):
    def test_cloud_init_is_not_in_the_image(self):
        for name in ("packages.x86_64", "packages.aarch64"):
            self.assertNotIn("cloud-init", packages(name), name)

    def test_live_sshd_config_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(AIROOTFS, "etc/ssh/sshd_config.d/10-archiso.conf")))


class QuietByDefault(unittest.TestCase):
    def test_networkmanager_connectivity_probe_is_off(self):
        path = os.path.join(AIROOTFS, "etc/NetworkManager/conf.d/20-connectivity.conf")
        self.assertEqual(settings(path), ["[connectivity]", "enabled=false"])

    def test_firefox_policy_disables_telemetry_and_studies(self):
        path = os.path.join(AIROOTFS, "etc/firefox/policies/policies.json")
        with open(path, encoding="utf-8") as f:
            pol = json.load(f)["policies"]
        self.assertIs(pol.get("DisableTelemetry"), True)
        self.assertIs(pol.get("DisableFirefoxStudies"), True)

    def test_time_servers_are_the_generic_pool(self):
        path = os.path.join(AIROOTFS, "etc/systemd/timesyncd.conf.d/heiss.conf")
        lines = settings(path)
        self.assertEqual(lines[0], "[Time]")
        servers = [l for l in lines[1:] if l.startswith("FallbackNTP=")]
        self.assertEqual(len(servers), 1)
        hosts = servers[0].split("=", 1)[1].split()
        self.assertTrue(hosts and all(h.endswith(".pool.ntp.org") and ".arch." not in h for h in hosts), hosts)


if __name__ == "__main__":
    unittest.main()
