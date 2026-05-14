{ pkgs, ... }:

{
  # VM-specific options belong here, including explicit shared-folder setup.

  # VMware Workstation guest integration.
  # Needed for dynamic display resizing, host/guest clipboard support, mouse
  # integration, and VMware-specific helper tools such as `vmhgfs-fuse`.
  virtualisation.vmware.guest.enable = true;

  # VMware exposes shared folders to the guest, but in this NixOS VM the exposed
  # `repos` share was visible via `vmware-hgfsclient` while `/mnt/hgfs` remained
  # empty after reboot. Mount HGFS explicitly so the Windows-owned repo tree is
  # available persistently inside the VM.
  systemd.services.vmware-hgfs-mount = {
    description = "Mount VMware shared folders";
    wantedBy = [ "multi-user.target" ];
    after = [ "vmware.service" ];
    wants = [ "vmware.service" ];

    serviceConfig = {
      Type = "forking";
      ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p /mnt/hgfs";

      # `allow_other` permits access beyond the mounting process/root; `uid`/`gid`
      # make files appear owned by the normal user; `umask=022` keeps files readable
      # and directories traversable without making them group/world-writable.
      ExecStart = "${pkgs.open-vm-tools}/bin/vmhgfs-fuse .host:/ /mnt/hgfs -o allow_other,uid=1000,gid=100,umask=022";

      ExecStop = "${pkgs.util-linux}/bin/umount /mnt/hgfs";
      RemainAfterExit = true;
    };
  };

  # Plasma Wayland allowed host -> guest clipboard in VMware Workstation, but
  # guest -> host clipboard did not work reliably. Plasma X11 provides working
  # bidirectional clipboard integration, so use it for this VM setup phase.
  services.displayManager.defaultSession = "plasmax11";
}

