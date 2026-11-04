// Heiss OS default desktop layout (Plasma loads it from the active look-and-feel package,
// kdeglobals [KDE] LookAndFeelPackage, at the first start of plasmashell). The panel is
// created from the first frame, so no stock panel flashes and nothing has to be rebuilt.
//
// ONE bottom floating panel: Heiss launcher, icon-only task manager, system tray, clock.
// The installer is not pinned (the desktop shortcut starts it; a running installer shows as a normal task).
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
kickoff.writeConfig("icon", "heiss-launcher-sand-light");   // darker sand (#8C7448) for the light panel

var tasks = panel.addWidget("org.kde.plasma.icontasks");
tasks.currentConfigGroup = ["General"];
tasks.writeConfig("launchers", [
    "applications:org.kde.dolphin.desktop",
    "applications:org.kde.konsole.desktop",
    "applications:systemsettings.desktop",
    "applications:firefox.desktop"
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
    // Reference the wallpaper PACKAGE id (never a file path: a path shows up as a second
    // "3840x2160" entry in the Wallpaper dialog). Each theme has its own plain package, no
    // dependence on the "dynamic wallpaper" light/dark mechanism. Color is what Plasma paints
    // when the image fails to load, so a failure shows the theme background, not white.
    desktopsArray[j].currentConfigGroup = ["Wallpaper", "org.kde.image", "General"];
    desktopsArray[j].writeConfig("Image", "Heiss-Everyday-Light");
    desktopsArray[j].writeConfig("Color", "#F7F5F1");
}
