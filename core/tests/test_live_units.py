"""Nothing in the live image phones home on its own: every symlink under /etc/systemd is pinned
(enabled units, aliases, masks), cloud-init and the live sshd are gone, the autostart entries are
pinned, and the "quiet by default" files are in place."""
import json
import re
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AIROOTFS = os.path.join(REPO, "profile", "airootfs")
SYSTEMD = os.path.join(AIROOTFS, "etc", "systemd")
LIB = "/usr/lib/systemd/system/"

# Every symlink under profile/airootfs/etc/systemd, relative to that directory, with its target.
# A new link here is a decision: add it together with a DECISIONS entry that says what it talks to.
LINKS = {
    "system/dbus-org.freedesktop.ModemManager1.service": LIB + "ModemManager.service",
    "system/dbus-org.freedesktop.nm-dispatcher.service": LIB + "NetworkManager-dispatcher.service",
    "system/dbus-org.freedesktop.resolve1.service": LIB + "systemd-resolved.service",
    "system/dbus-org.freedesktop.timesync1.service": LIB + "systemd-timesyncd.service",
    "system/display-manager.service": LIB + "sddm.service",
    "system-generators/systemd-gpt-auto-generator": "/dev/null",
    "system/multi-user.target.wants/choose-mirror.service": "../choose-mirror.service",
    "system/multi-user.target.wants/hv_fcopy_daemon.service": LIB + "hv_fcopy_daemon.service",
    "system/multi-user.target.wants/hv_kvp_daemon.service": LIB + "hv_kvp_daemon.service",
    "system/multi-user.target.wants/hv_vss_daemon.service": LIB + "hv_vss_daemon.service",
    "system/multi-user.target.wants/livecd-talk.service": "/etc/systemd/system/livecd-talk.service",
    "system/multi-user.target.wants/ModemManager.service": LIB + "ModemManager.service",
    "system/multi-user.target.wants/NetworkManager.service": LIB + "NetworkManager.service",
    "system/multi-user.target.wants/pacman-init.service": "../pacman-init.service",
    "system/multi-user.target.wants/systemd-resolved.service": LIB + "systemd-resolved.service",
    "system/multi-user.target.wants/vboxservice.service": LIB + "vboxservice.service",
    "system/multi-user.target.wants/vmtoolsd.service": LIB + "vmtoolsd.service",
    "system/multi-user.target.wants/vmware-vmblock-fuse.service": LIB + "vmware-vmblock-fuse.service",
    "system/sockets.target.wants/pcscd.socket": LIB + "pcscd.socket",
    "system/sound.target.wants/livecd-alsa-unmuter.service": "../livecd-alsa-unmuter.service",
    "system/sysinit.target.wants/systemd-timesyncd.service": LIB + "systemd-timesyncd.service",
    "system/sysinit.target.wants/systemd-time-wait-sync.service": LIB + "systemd-time-wait-sync.service",
}
# D-Bus activation aliases: the link name differs from the unit on purpose.
ALIASES = {"dbus-org.freedesktop.ModemManager1.service", "dbus-org.freedesktop.nm-dispatcher.service",
           "dbus-org.freedesktop.resolve1.service", "dbus-org.freedesktop.timesync1.service",
           "display-manager.service", "systemd-gpt-auto-generator"}
# Units that are never enabled or aliased in the image: each one would talk to a remote host at boot.
NEVER = {"sshd.service", "sshd.socket", "reflector.service", "reflector.timer", "pkgstats.timer",
         "pkgstats.service", "cloud-init.target", "cloud-init-main.service", "cloud-init-local.service",
         "cloud-init-network.service", "cloud-config.service", "cloud-final.service", "geoclue.service",
         "avahi-daemon.service", "avahi-daemon.socket", "fwupd.service", "fwupd-refresh.timer",
         "packagekit.service", "packagekit-offline-update.service"}
# Programs the default Hyprland configuration starts (exec-once): none of them may fetch anything.
EXEC_ONCE = ["heiss-wallpaper", "heiss-welcome --first-run", "waybar", "mako", "hypridle", "hyprpolkitagent", "nm-applet --indicator", "blueman-applet",
             "command -v VBoxClient-all >/dev/null && VBoxClient-all"]


def packages(name):
    with open(os.path.join(REPO, "profile", name), encoding="utf-8") as f:
        return [l.split("#")[0].strip() for l in f if l.split("#")[0].strip()]


def settings(path):
    """Non-empty, non-comment lines of an ini-style file."""
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def all_links():
    found = {}
    for dirpath, dirnames, filenames in os.walk(SYSTEMD):
        for name in dirnames + filenames:
            p = os.path.join(dirpath, name)
            if os.path.islink(p):
                found[os.path.relpath(p, SYSTEMD)] = os.readlink(p)
    return found


class SystemdLinks(unittest.TestCase):
    def test_every_symlink_under_etc_systemd_is_the_listed_one(self):
        self.assertEqual(all_links(), LINKS)

    def test_no_phone_home_unit_by_name_or_by_target(self):
        for name, target in all_links().items():
            self.assertNotIn(os.path.basename(name), NEVER, name)
            self.assertNotIn(os.path.basename(target), NEVER, name)

    def test_only_wants_links_enable_units(self):
        # a *.requires or *.upholds directory would be a second way to start a unit at boot
        for dirpath, dirnames, _ in os.walk(SYSTEMD):
            for d in dirnames:
                self.assertFalse(d.endswith((".requires", ".upholds")), os.path.join(dirpath, d))

    def test_link_names_match_their_unit_and_targets_stay_in_the_image(self):
        for name, target in all_links().items():
            base = os.path.basename(name)
            if base not in ALIASES:
                self.assertEqual(os.path.basename(target), base, name)
            if target.startswith(LIB):
                continue   # a package unit: checked by the package list and the real boot
            if target.startswith("/"):
                resolved = os.path.join(AIROOTFS, target.lstrip("/"))
            else:
                resolved = os.path.normpath(os.path.join(SYSTEMD, os.path.dirname(name), target))
            if target == "/dev/null":
                continue   # a mask
            self.assertEqual(os.path.commonpath([AIROOTFS, resolved]), AIROOTFS, name)
            self.assertTrue(os.path.isfile(resolved), "%s -> %s" % (name, target))

    def test_cloud_init_wants_directory_is_gone(self):
        self.assertFalse(os.path.exists(os.path.join(SYSTEMD, "system", "cloud-init.target.wants")))


class Autostart(unittest.TestCase):
    def test_no_xdg_autostart_entries_in_the_image(self):
        self.assertFalse(os.path.exists(os.path.join(AIROOTFS, "etc", "xdg", "autostart")))

    def test_session_starts_the_two_live_helpers_only_in_the_live_system(self):
        with open(os.path.join(REPO, "desktop", "bin", "heiss-session"), encoding="utf-8") as f:
            text = f.read()
        m = re.search(r"if \[ -d /run/archiso/bootmnt \]; then\n(.*?)\nfi", text, re.S)
        self.assertIsNotNone(m)
        self.assertEqual(re.findall(r"/usr/local/bin/[\w.-]+", m.group(1)),
                         ["/usr/local/bin/heiss-start-installer.sh", "/usr/local/bin/heiss-open-link"])

    def test_default_hyprland_config_starts_the_listed_programs(self):
        with open(os.path.join(REPO, "desktop", "hypr", "hyprland.lua"), encoding="utf-8") as f:
            text = f.read()
        block = re.search(r'hl\.on\("hyprland\.start", function\(\)\n(.*?)\nend\)', text, re.S)
        self.assertIsNotNone(block)
        started = re.findall(r'^\s*hl\.exec_cmd\("(.*)"\)\s*$', block.group(1), re.M)
        self.assertEqual(started, EXEC_ONCE)
        for cmd in started:
            self.assertNotRegex(cmd, r"curl|wget|http")


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

    def test_resolved_does_not_announce_on_the_lan(self):
        path = os.path.join(AIROOTFS, "etc/systemd/resolved.conf.d/archiso.conf")
        self.assertEqual(settings(path), ["[Resolve]", "MulticastDNS=no", "LLMNR=no"])

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
