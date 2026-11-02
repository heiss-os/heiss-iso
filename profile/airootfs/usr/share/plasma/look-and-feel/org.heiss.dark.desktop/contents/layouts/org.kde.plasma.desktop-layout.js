// Heiss OS default desktop layout (Plasma loads it from the active look-and-feel package,
// kdeglobals [KDE] LookAndFeelPackage, at the first start of plasmashell). The panel is
// created from the first frame, so no stock panel flashes and nothing has to be rebuilt.
//
// ONE bottom floating panel: Heiss launcher, icon-only task manager, system tray, clock.
// The live-only installer pin is added later by heiss-setup-dock.sh (the installed system
// must not pin a desktop file that heiss-cleanup.sh removes: it would show a white icon).
//
// Pins are a real JS array: a comma-joined string is stored as ONE launcher entry (that was
// the white generic icon with the tooltip "firefox.desktop,applications:org.kde.d...").

var panel = new Panel();
panel.location = "bottom";
panel.height = 52;
panel.lengthMode = "fill";
panel.floating = true;
panel.opacity = "translucent";

var kickoff = panel.addWidget("org.kde.plasma.kickoff");
kickoff.currentConfigGroup = ["General"];
kickoff.writeConfig("icon", "heiss-launcher-sand");

var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:firefox.desktop",
    "applications:org.kde.dolphin.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:systemsettings.desktop"
]);

panel.addWidget("org.kde.plasma.systemtray");

// Time only, small and light; where a date is shown anyway it is the short one.
var clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["Appearance"];
clock.writeConfig("autoFontAndSize", false);
clock.writeConfig("fontFamily", "Inter");
clock.writeConfig("fontWeight", 400);
clock.writeConfig("fontStyleName", "Regular");
clock.writeConfig("fontSize", 11);
clock.writeConfig("boldText", false);
clock.writeConfig("showDate", false);
clock.writeConfig("dateFormat", "shortDate");

var desktopsArray = desktopsForActivity(currentActivity());
for (var j = 0; j < desktopsArray.length; j++) {
    desktopsArray[j].wallpaperPlugin = "org.kde.image";
}
