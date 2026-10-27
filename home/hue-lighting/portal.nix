# Preserve the portal's normal consent UI. Supply app identity to its existing
# custom-picker hook so the Hue adapter can honor only Hue's source preference.
{ portal }:
assert portal.version == "1.4.1";
portal.overrideAttrs (old: {
  patches = (old.patches or [ ]) ++ [ ./portal-app-id.patch ];
})
