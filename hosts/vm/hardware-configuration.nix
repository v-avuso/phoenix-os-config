# Placeholder for the currently unused VM target.
#
# The historical Windows-hosted VM hardware configuration was never committed and that VM is
# obsolete. Replace this file with the generated hardware configuration of the next real VM before
# treating the VM target as deployable.
#
# NixOS requires a root filesystem declaration to build system.build.toplevel. This generic tmpfs
# declaration is only a structural placeholder, not hardware configuration for a deployable VM.
{ ... }:
{
  fileSystems."/" = {
    device = "none";
    fsType = "tmpfs";
  };
}
