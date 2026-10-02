// Managed Zen preferences for the DMS/Hyprland session.

// Let DMS' generated userChrome.css own the browser chrome and follow the
// desktop light/dark mode instead of using a separate fixed-color theme.
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("extensions.activeThemeID", "default-theme@mozilla.org");
user_pref("browser.theme.toolbar-theme", 0);
user_pref("browser.theme.content-theme", 0);

// Conservative responsiveness improvements. Keep hardware acceleration and
// process isolation on their upstream defaults for the AMD Wayland session.
user_pref("browser.tabs.unloadOnLowMemory", true);
user_pref("browser.sessionstore.restore_on_demand", true);
user_pref("browser.sessionstore.restore_pinned_tabs_on_demand", true);
user_pref("browser.sessionstore.interval", 60000);
user_pref("browser.sessionstore.max_tabs_undo", 15);
user_pref("browser.startup.page", 1);

// Keep the built-in new-tab page useful but quiet and inexpensive.
user_pref("browser.newtabpage.activity-stream.showSponsored", false);
user_pref("browser.newtabpage.activity-stream.showSponsoredTopSites", false);
user_pref("browser.newtabpage.activity-stream.feeds.section.topstories", false);
user_pref("browser.newtabpage.activity-stream.feeds.topsites", true);
user_pref("browser.newtabpage.activity-stream.showSearch", true);

// Restore connection warm-up and standards-based link/page prefetching for
// faster navigation. Firefox still applies its own network scheduling limits.
user_pref("network.dns.disablePrefetch", false);
user_pref("network.http.speculative-parallel-limit", 6);
user_pref("network.prefetch-next", true);

// Avoid the expensive blur/slide animation in the installed Better Find Bar mod.
user_pref("theme.better_find_bar.instant_animations", true);
