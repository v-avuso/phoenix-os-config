
{ pkgs, lib, inputs, ... }:

let
  addons = inputs.firefox-addons.packages.${pkgs.system};

  alUrlShortener =
    "https://raw.githubusercontent.com/DandelionSprout/adfilt/master/LegitimateURLShortener.txt";

  trustedOrigins = [
    "https://chatgpt.com"
    "https://web.whatsapp.com"
  ];

  uboUserFilters = builtins.readFile ./ublock-filters.txt;

  uboSettings = {
    selectedFilterLists = [
      "user-filters"

      # uBO defaults / core lists
      "ublock-filters"
      "ublock-badware"
      "ublock-privacy"
      "ublock-unbreak"
      "ublock-quick-fixes"
      "easylist"
      "easyprivacy"
      "urlhaus-1"
      "plowe-0"

      # URL tracking cleanup without ClearURLs extension
      "adguard-spyware-url"
      alUrlShortener
    ];

    userFilters = uboUserFilters;
    externalLists = alUrlShortener;
  };

  searchDefaults = {
    force = true;
    default = "ddg";
    privateDefault = "ddg";
  };

  # Home Manager writes extension settings to local storage; keep Dark Reader
  # off its separate sync settings store so these declarations take effect.
  darkReaderSettings = {
    enabled = true;
    enabledByDefault = false;
    enabledFor = [ ];
    disabledFor = [ ];
    syncSettings = false;
  };

  # Keep this small. Every extension adds privileged code + fingerprint surface.
  hardenedExtensions = with addons; [
    ublock-origin
    keepassxc-browser
    darkreader
    sponsorblock
    remove-youtube-s-suggestions
    unpaywall
    consent-o-matic
  ];

  compatExtensions = hardenedExtensions;

  # Keep site-specific styles in separate files, then combine them for Firefox.
  userContentCss = builtins.concatStringsSep "\n" (map builtins.readFile [
    ./the-decoder.css
    ./chatgpt.css
  ]);

  safeBrowsingSettings = {
    "browser.safebrowsing.malware.enabled" = lib.mkForce true;
    "browser.safebrowsing.phishing.enabled" = lib.mkForce true;
    "browser.safebrowsing.blockedURIs.enabled" = lib.mkForce true;
    "browser.safebrowsing.downloads.enabled" = lib.mkForce true;
    "browser.safebrowsing.downloads.remote.enabled" = lib.mkForce true;
  };

  noSaveSettings = {
    "signon.rememberSignons" = false;
    "signon.autofillForms" = false;
    "browser.formfill.enable" = false;
    "extensions.formautofill.addresses.enabled" = false;
    "extensions.formautofill.creditCards.enabled" = false;
  };

  noOnboardingSettings = {
    "browser.aboutwelcome.enabled" = false;
    "browser.startup.homepage_override.mstone" = "ignore";
    "browser.startup.homepage_override_url" = "";
    "startup.homepage_welcome_url" = "";
    "startup.homepage_welcome_url.additional" = "";
    "trailhead.firstrun.didSeeAboutWelcome" = true;

    "browser.newtabpage.activity-stream.asrouter.userprefs.cfr.addons" = false;
    "browser.newtabpage.activity-stream.asrouter.userprefs.cfr.features" = false;
    "browser.messaging-system.whatsNewPanel.enabled" = false;
  };

  sessionRestoreSettings = {
    "browser.startup.page" = lib.mkForce 3;
    "privacy.clearOnShutdown_v2.browsingHistoryAndDownloads" = lib.mkForce false;
  };

  autoEnableExtensionSettings = {
    # Avoid HM-installed extensions starting disabled in fresh profiles.
    "extensions.autoDisableScopes" = 0;
  };

  appearanceSettings = {
    # Use Firefox's built-in dark theme for the browser UI.
    "extensions.activeThemeID" = "firefox-compact-dark@mozilla.org";
  };

  userContentSettings = {
    # Required for userContent.css / userChrome.css customizations.
    "toolkit.legacyUserProfileCustomizations.stylesheets" = true;
  };

  ephemeralSettings = {
    # Clear local browsing state on shutdown.
    "privacy.sanitize.sanitizeOnShutdown" = true;
    "privacy.clearOnShutdown.cache" = true;
    "privacy.clearOnShutdown.cookies" = true;
    "privacy.clearOnShutdown.history" = true;
    "privacy.clearOnShutdown.sessions" = true;

    # Keep site permission exceptions; change to true if you want brutal reset.
    "privacy.clearOnShutdown.siteSettings" = false;
  };

  compatRelaxations = {
    # Main breakage reducers.
    "privacy.resistFingerprinting" = lib.mkForce false;
    "privacy.resistFingerprinting.letterboxing" = lib.mkForce false;
    "webgl.disabled" = lib.mkForce false;

    # DRM / Widevine.
    "media.eme.enabled" = lib.mkForce true;
    "media.gmp-widevinecdm.enabled" = lib.mkForce true;
  };

  commonSettings =
    {
      "middlemouse.paste" = false;
      "browser.tabs.opentabfor.middleclick" = true;
      "sidebar.revamp" = true;
      "sidebar.verticalTabs" = true;
    }
    // autoEnableExtensionSettings
    // appearanceSettings
    // safeBrowsingSettings
    // noSaveSettings
    // noOnboardingSettings;

  mkArkenfoxProfile =
    {
      id,
      name,
      isDefault ? false,
      extensions ? hardenedExtensions,
      settings ? { },
    }:
    {
      inherit id isDefault name;
      path = name;
      search = searchDefaults;

      arkenfox = {
        enable = true;
        enableAllSections = true;
      };

      settings = commonSettings // userContentSettings // settings;

      userContent = userContentCss;

      extensions = {
        force = true;
        packages = extensions;

        settings = {
          "addon@darkreader.org".settings = darkReaderSettings;
        };
      };
    };

  mkCleanEphemeralProfile =
    {
      id,
      name,
      settings ? { },
    }:
    {
      inherit id name;
      path = name;
      search = searchDefaults;

      # No Arkenfox, no extensions: near-stock Firefox fallback.
      settings = commonSettings // ephemeralSettings // settings;
    };

in
{
  programs.firefox = {
    enable = true;

    policies = {
      OfferToSaveLogins = false;
      AutofillAddressEnabled = false;
      AutofillCreditCardEnabled = false;
      OverrideFirstRunPage = "";
      OverridePostUpdatePage = "";

      # TODO: migrate to ClearOnShutdown.Exceptions when targeting Firefox 158 or newer.
      SanitizeOnShutdown = {
        Cache = true;
        Cookies = true;
        Downloads = false;
        FormData = true;
        History = false;
        Sessions = false;
        SiteSettings = false;
        OfflineApps = false;
        Locked = false;
        Exceptions = [
          # AI / productivity
          "https://chatgpt.com"
          "https://todoist.com"

          # Google / video
          "https://google.com"
          "https://youtube.com"

          # Social media
          "https://instagram.com"
          "https://x.com"

          # Messaging
          "https://web.whatsapp.com"
          "https://discord.com"

          # Email
          "https://proton.me"
        ];
      };

      Permissions.Microphone.Allow = trustedOrigins;

      # Retain the existing cookie permission allowlist independently of shutdown clearing.
      Cookies.Allow = trustedOrigins;

      ExtensionSettings = {
        "keepassxc-browser@keepassxc.org".default_area = "navbar";
        "uBlock0@raymondhill.net".default_area = "navbar";
        "addon@darkreader.org".default_area = "menupanel";
        "sponsorBlocker@ajay.app".default_area = "menupanel";
        "{21f1ba12-47e1-4a9b-ad4e-3a0260bbeb26}".default_area = "menupanel";
        "{f209234a-76f0-4735-9920-eb62507a54cd}".default_area = "menupanel";
        "gdpr@cavi.au.dk".default_area = "menupanel";
      };

      # uBO reads this managed setting on startup and imports it as a backup-shaped config.
      # More reliable for declarative My filters than profile extension local storage.
      "3rdparty".Extensions."uBlock0@raymondhill.net" = {
        adminSettings = builtins.toJSON uboSettings;
      };
    };

    arkenfox = {
      enable = true;
      version = "master";
    };

    profiles = {
      hardened = mkArkenfoxProfile {
        id = 0;
        name = "hardened";
        isDefault = true;
        settings = sessionRestoreSettings // {
          "browser.sessionstore.max_windows_undo" = 10;
        };
      };

      compat = mkArkenfoxProfile {
        id = 1;
        name = "compat";
        extensions = compatExtensions;
        settings = compatRelaxations // ephemeralSettings // sessionRestoreSettings;
      };

      clean = mkCleanEphemeralProfile {
        id = 2;
        name = "clean";
      };
    };
  };
}
