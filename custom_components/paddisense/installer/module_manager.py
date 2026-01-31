"""Module management for PaddiSense installer."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from ..const import (
    AVAILABLE_MODULES,
    DATA_DIR,
    LOVELACE_DASHBOARDS_YAML,
    MODULE_METADATA,
    MODULES_JSON,
    PACKAGES_DIR,
    PADDISENSE_DIR,
)

_LOGGER = logging.getLogger(__name__)


class ModuleManager:
    """Manage PaddiSense module installation and removal."""

    def __init__(self) -> None:
        """Initialize the module manager."""
        self.paddisense_dir = PADDISENSE_DIR
        self.packages_dir = PACKAGES_DIR
        self.data_dir = DATA_DIR

    def get_modules_metadata(self) -> dict[str, Any]:
        """Load modules metadata from modules.json or fallback to const."""
        if MODULES_JSON.exists():
            try:
                data = json.loads(MODULES_JSON.read_text(encoding="utf-8"))
                return data.get("modules", MODULE_METADATA)
            except (json.JSONDecodeError, IOError):
                pass
        return MODULE_METADATA

    def get_installed_modules(self) -> list[dict[str, Any]]:
        """Get list of currently installed modules."""
        installed = []
        metadata = self.get_modules_metadata()

        for module_id in AVAILABLE_MODULES:
            symlink_path = self.packages_dir / f"{module_id}.yaml"
            module_dir = self.paddisense_dir / module_id

            if symlink_path.exists() or symlink_path.is_symlink():
                # Module is installed
                version = self._get_module_version(module_id)
                meta = metadata.get(module_id, MODULE_METADATA.get(module_id, {}))

                installed.append({
                    "id": module_id,
                    "name": meta.get("name", module_id),
                    "version": version,
                    "icon": meta.get("icon", "mdi:package"),
                    "has_data": self._module_has_data(module_id),
                })

        return installed

    def get_available_modules(self) -> list[dict[str, Any]]:
        """Get list of modules available for installation."""
        available = []
        installed_ids = [m["id"] for m in self.get_installed_modules()]
        metadata = self.get_modules_metadata()

        for module_id in AVAILABLE_MODULES:
            if module_id not in installed_ids:
                module_dir = self.paddisense_dir / module_id

                # Only show if module folder exists in repo
                if module_dir.is_dir():
                    version = self._get_module_version(module_id)
                    meta = metadata.get(module_id, MODULE_METADATA.get(module_id, {}))

                    available.append({
                        "id": module_id,
                        "name": meta.get("name", module_id),
                        "description": meta.get("description", ""),
                        "version": version,
                        "icon": meta.get("icon", "mdi:package"),
                    })

        return available

    def _get_module_version(self, module_id: str) -> str:
        """Get version from module's VERSION file."""
        version_file = self.paddisense_dir / module_id / "VERSION"
        if version_file.exists():
            try:
                return version_file.read_text(encoding="utf-8").strip()
            except IOError:
                pass
        return "unknown"

    def _module_has_data(self, module_id: str) -> bool:
        """Check if module has local data."""
        data_path = self.data_dir / module_id
        if not data_path.exists():
            return False
        # Check if there are any files in the data directory
        return any(data_path.iterdir())

    def install_module(self, module_id: str) -> dict[str, Any]:
        """Install a module by creating symlink and updating dashboards."""
        if module_id not in AVAILABLE_MODULES:
            return {
                "success": False,
                "error": f"Unknown module: {module_id}",
            }

        module_dir = self.paddisense_dir / module_id
        if not module_dir.is_dir():
            return {
                "success": False,
                "error": f"Module not found in repository: {module_id}",
            }

        package_file = module_dir / "package.yaml"
        if not package_file.exists():
            return {
                "success": False,
                "error": f"Module package.yaml not found: {module_id}",
            }

        try:
            # Ensure packages directory exists
            self.packages_dir.mkdir(parents=True, exist_ok=True)

            # Create symlink
            symlink_path = self.packages_dir / f"{module_id}.yaml"
            if symlink_path.exists() or symlink_path.is_symlink():
                symlink_path.unlink()

            # Relative symlink: from packages/ipm.yaml to ../ipm/package.yaml
            relative_target = Path("..") / module_id / "package.yaml"
            symlink_path.symlink_to(relative_target)

            # Create data directory
            data_path = self.data_dir / module_id
            data_path.mkdir(parents=True, exist_ok=True)
            (data_path / "backups").mkdir(exist_ok=True)

            # Update lovelace dashboards
            self._add_dashboard(module_id)

            version = self._get_module_version(module_id)
            _LOGGER.info("Installed module %s v%s", module_id, version)

            return {
                "success": True,
                "module_id": module_id,
                "version": version,
                "message": f"Installed {module_id}",
                "restart_required": True,
            }

        except OSError as e:
            _LOGGER.error("Failed to install module %s: %s", module_id, e)
            return {
                "success": False,
                "error": f"Installation failed: {e}",
            }

    def remove_module(self, module_id: str) -> dict[str, Any]:
        """Remove a module by deleting symlink and dashboard entry."""
        if module_id not in AVAILABLE_MODULES:
            return {
                "success": False,
                "error": f"Unknown module: {module_id}",
            }

        symlink_path = self.packages_dir / f"{module_id}.yaml"

        if not symlink_path.exists() and not symlink_path.is_symlink():
            return {
                "success": False,
                "error": f"Module not installed: {module_id}",
            }

        try:
            # Remove symlink
            if symlink_path.exists() or symlink_path.is_symlink():
                symlink_path.unlink()

            # Remove dashboard entry
            self._remove_dashboard(module_id)

            # Note: We do NOT delete local_data/{module_id} - data is preserved

            _LOGGER.info("Removed module %s (data preserved)", module_id)

            return {
                "success": True,
                "module_id": module_id,
                "message": f"Removed {module_id} (local data preserved)",
                "restart_required": True,
            }

        except OSError as e:
            _LOGGER.error("Failed to remove module %s: %s", module_id, e)
            return {
                "success": False,
                "error": f"Removal failed: {e}",
            }

    def _add_dashboard(self, module_id: str) -> None:
        """Add dashboard entry for a module."""
        # Get metadata from modules.json (preferred) or fallback to const
        all_meta = self.get_modules_metadata()
        meta = all_meta.get(module_id, MODULE_METADATA.get(module_id, {}))

        slug = meta.get("dashboard_slug", f"{module_id}-dashboard")
        title = meta.get("dashboard_title", meta.get("name", module_id))
        icon = meta.get("icon", "mdi:package")

        # Use dashboard_file from modules.json if available
        dashboard_file_path = meta.get("dashboard_file")
        if dashboard_file_path:
            dashboard_file = self.paddisense_dir / dashboard_file_path
        else:
            # Fallback to convention
            dashboard_file = self.paddisense_dir / module_id / "dashboards" / "views.yaml"
            if module_id == "ipm":
                dashboard_file = self.paddisense_dir / "ipm" / "dashboards" / "inventory.yaml"

        if not dashboard_file.exists():
            # Try alternative path
            alt_file = self.paddisense_dir / module_id / "dashboards" / f"{module_id}.yaml"
            if alt_file.exists():
                dashboard_file = alt_file

        # Read existing dashboards
        dashboards = {}
        if LOVELACE_DASHBOARDS_YAML.exists():
            try:
                import yaml
                content = LOVELACE_DASHBOARDS_YAML.read_text(encoding="utf-8")
                dashboards = yaml.safe_load(content) or {}
            except (yaml.YAMLError, IOError):
                dashboards = {}

        # Add new dashboard
        relative_path = str(dashboard_file.relative_to(Path("/config")))
        dashboards[slug] = {
            "mode": "yaml",
            "title": title,
            "icon": icon,
            "show_in_sidebar": True,
            "filename": relative_path,
        }

        # Write back
        self._write_lovelace_dashboards(dashboards)

    def _remove_dashboard(self, module_id: str) -> None:
        """Remove dashboard entry for a module."""
        meta = MODULE_METADATA.get(module_id, {})
        slug = meta.get("dashboard_slug", f"{module_id}-dashboard")

        if not LOVELACE_DASHBOARDS_YAML.exists():
            return

        try:
            import yaml
            content = LOVELACE_DASHBOARDS_YAML.read_text(encoding="utf-8")
            dashboards = yaml.safe_load(content) or {}

            if slug in dashboards:
                del dashboards[slug]
                self._write_lovelace_dashboards(dashboards)

        except (yaml.YAMLError, IOError) as e:
            _LOGGER.error("Failed to update dashboards: %s", e)

    def _write_lovelace_dashboards(self, dashboards: dict[str, Any]) -> None:
        """Write lovelace_dashboards.yaml file."""
        import yaml

        header = """# Auto-generated by PaddiSense
# Do not edit manually - changes may be overwritten
# Manage modules via PaddiSense Manager

"""
        content = header + yaml.dump(dashboards, default_flow_style=False, sort_keys=False)
        LOVELACE_DASHBOARDS_YAML.write_text(content, encoding="utf-8")

    def install_multiple(self, module_ids: list[str]) -> dict[str, Any]:
        """Install multiple modules."""
        results = []
        success_count = 0
        failed_count = 0

        for module_id in module_ids:
            result = self.install_module(module_id)
            results.append({
                "module_id": module_id,
                "success": result.get("success", False),
                "error": result.get("error"),
            })
            if result.get("success"):
                success_count += 1
            else:
                failed_count += 1

        return {
            "success": failed_count == 0,
            "installed": success_count,
            "failed": failed_count,
            "results": results,
            "restart_required": success_count > 0,
        }

    def verify_module_installation(self, module_id: str) -> dict[str, Any]:
        """Verify a module is properly installed."""
        checks = {
            "symlink_exists": False,
            "package_exists": False,
            "data_dir_exists": False,
            "dashboard_registered": False,
        }

        # Check symlink
        symlink_path = self.packages_dir / f"{module_id}.yaml"
        checks["symlink_exists"] = symlink_path.exists() or symlink_path.is_symlink()

        # Check package file
        package_file = self.paddisense_dir / module_id / "package.yaml"
        checks["package_exists"] = package_file.exists()

        # Check data directory
        data_path = self.data_dir / module_id
        checks["data_dir_exists"] = data_path.is_dir()

        # Check dashboard registration
        if LOVELACE_DASHBOARDS_YAML.exists():
            try:
                import yaml
                content = LOVELACE_DASHBOARDS_YAML.read_text(encoding="utf-8")
                dashboards = yaml.safe_load(content) or {}
                meta = MODULE_METADATA.get(module_id, {})
                slug = meta.get("dashboard_slug", f"{module_id}-dashboard")
                checks["dashboard_registered"] = slug in dashboards
            except (yaml.YAMLError, IOError):
                pass

        all_passed = all(checks.values())

        return {
            "success": all_passed,
            "module_id": module_id,
            "checks": checks,
        }
