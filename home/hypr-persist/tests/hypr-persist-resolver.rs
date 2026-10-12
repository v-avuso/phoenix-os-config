
// Phoenix: test supported exact overrides against desktop and /proc fallback.
#[cfg(test)]
mod phoenix_resolver_tests {
    use super::*;

    #[test]
    fn phoenix_exact_launch_boundaries_precede_all_fallbacks() {
        let dir = tempfile::tempdir().unwrap();
        for class in ["codex-desktop", "codex-desktop-sandboxed"] {
            std::fs::write(dir.path().join(format!("{class}.desktop")), format!(
                "[Desktop Entry]\nExec=/unsafe/bare-electron\nStartupWMClass={class}\n"
            )).unwrap();
        }
        let mut config = Config::default();
        for class in ["codex-desktop", "codex-desktop-sandboxed"] {
            config.overrides.insert(class.into(), format!("/run/current-system/sw/bin/{class}"));
        }
        let mut resolver = AppResolver::new(&config);
        resolver.desktop_index = DesktopIndex::build_from_dirs(&[dir.path().to_path_buf()]);
        let pid = i64::from(std::process::id());
        // Conflicting desktop entry must lose to the exact override.
        for class in ["codex-desktop", "codex-desktop-sandboxed"] {
            assert_eq!(resolver.resolve(class, pid), Some(format!("/run/current-system/sw/bin/{class}")));
        }
        // With no desktop entries, /proc still cannot choose the main launch.
        resolver.desktop_index = DesktopIndex::build_from_dirs(&[]);
        resolver.cache.lock().unwrap().clear();
        for class in ["codex-desktop", "codex-desktop-sandboxed"] {
            assert_eq!(resolver.resolve(class, pid), Some(format!("/run/current-system/sw/bin/{class}")));
            assert_eq!(resolver.resolve(&format!("{class}-helper"), 0), None);
        }
        // The underlying fallback is real; it is deliberately not used above.
        assert!(proc::resolve_from_proc(pid).is_some());
    }
}
