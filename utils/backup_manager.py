"""Backup and Restore Manager for Eden Analytics Pro."""

import os
import shutil
import zipfile
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BackupInfo:
    """Information about a backup."""
    filename: str
    created_at: datetime
    size_bytes: int
    includes_database: bool
    includes_models: bool
    includes_config: bool
    version: str
    
    def to_dict(self) -> Dict:
        return {
            'filename': self.filename,
            'created_at': self.created_at.isoformat(),
            'size_bytes': self.size_bytes,
            'includes_database': self.includes_database,
            'includes_models': self.includes_models,
            'includes_config': self.includes_config,
            'version': self.version
        }


class BackupManager:
    """Manages backup and restore operations."""
    
    VERSION = "2.1.1"
    
    def __init__(self, 
                 project_root: str = None,
                 backup_dir: str = None):
        self.project_root = Path(project_root or Path(__file__).parent.parent)
        self.backup_dir = Path(backup_dir or self.project_root / "backups")
        self.backup_dir.mkdir(exist_ok=True)
        
        # Define what to backup
        self.database_files = [
            "eden_mvp.db",
            "eden_users.db",
            "historical_matches.db"
        ]
        
        self.model_files = [
            "models/overtime_model.pkl",
            "models/overtime_scaler.pkl"
        ]
        
        self.config_files = [
            "config/config.yaml"
        ]
        
        self.log_dir = "logs"
    
    def create_backup(self,
                     include_database: bool = True,
                     include_models: bool = True,
                     include_config: bool = True,
                     include_logs: bool = False,
                     name_prefix: str = "backup") -> Optional[Path]:
        """Create a backup of the application data.
        
        Args:
            include_database: Include database files
            include_models: Include ML model files
            include_config: Include configuration files
            include_logs: Include log files
            name_prefix: Prefix for backup filename
        
        Returns:
            Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{name_prefix}_{timestamp}.zip"
        backup_path = self.backup_dir / backup_name
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                files_added = 0
                
                # Add database files
                if include_database:
                    for db_file in self.database_files:
                        db_path = self.project_root / db_file
                        if db_path.exists():
                            zipf.write(db_path, f"database/{db_file}")
                            files_added += 1
                            logger.debug(f"Added database: {db_file}")
                
                # Add model files
                if include_models:
                    for model_file in self.model_files:
                        model_path = self.project_root / model_file
                        if model_path.exists():
                            zipf.write(model_path, model_file)
                            files_added += 1
                            logger.debug(f"Added model: {model_file}")
                
                # Add config files
                if include_config:
                    for config_file in self.config_files:
                        config_path = self.project_root / config_file
                        if config_path.exists():
                            zipf.write(config_path, config_file)
                            files_added += 1
                            logger.debug(f"Added config: {config_file}")
                
                # Add logs
                if include_logs:
                    logs_path = self.project_root / self.log_dir
                    if logs_path.exists():
                        for log_file in logs_path.glob("*.log"):
                            zipf.write(log_file, f"logs/{log_file.name}")
                            files_added += 1
                
                # Add backup metadata
                metadata = {
                    'version': self.VERSION,
                    'created_at': datetime.now().isoformat(),
                    'includes_database': include_database,
                    'includes_models': include_models,
                    'includes_config': include_config,
                    'includes_logs': include_logs,
                    'files_count': files_added
                }
                
                metadata_json = json.dumps(metadata, indent=2)
                zipf.writestr("backup_metadata.json", metadata_json)
            
            logger.info(f"Backup created: {backup_path} ({files_added} files)")
            return backup_path
            
        except Exception as e:
            logger.error(f"Backup creation failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            return None
    
    def restore_backup(self, backup_path: str,
                      restore_database: bool = True,
                      restore_models: bool = True,
                      restore_config: bool = True) -> bool:
        """Restore from a backup file.
        
        Args:
            backup_path: Path to the backup file
            restore_database: Restore database files
            restore_models: Restore ML model files
            restore_config: Restore configuration files
        
        Returns:
            True if successful, False otherwise
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            logger.error(f"Backup file not found: {backup_path}")
            return False
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Read metadata
                try:
                    metadata = json.loads(zipf.read("backup_metadata.json"))
                    logger.info(f"Restoring backup from {metadata.get('created_at', 'unknown')}")
                except Exception:
                    logger.warning("No metadata found in backup")
                    metadata = {}
                
                # Create temp directory for extraction
                temp_dir = self.backup_dir / "temp_restore"
                temp_dir.mkdir(exist_ok=True)
                
                try:
                    zipf.extractall(temp_dir)
                    
                    # Restore database files
                    if restore_database:
                        db_dir = temp_dir / "database"
                        if db_dir.exists():
                            for db_file in db_dir.glob("*.db"):
                                dest = self.project_root / db_file.name
                                shutil.copy2(db_file, dest)
                                logger.info(f"Restored: {db_file.name}")
                    
                    # Restore model files
                    if restore_models:
                        models_dir = temp_dir / "models"
                        if models_dir.exists():
                            dest_models_dir = self.project_root / "models"
                            dest_models_dir.mkdir(exist_ok=True)
                            for model_file in models_dir.glob("*.pkl"):
                                dest = dest_models_dir / model_file.name
                                shutil.copy2(model_file, dest)
                                logger.info(f"Restored: models/{model_file.name}")
                    
                    # Restore config files
                    if restore_config:
                        config_dir = temp_dir / "config"
                        if config_dir.exists():
                            dest_config_dir = self.project_root / "config"
                            dest_config_dir.mkdir(exist_ok=True)
                            for config_file in config_dir.glob("*"):
                                dest = dest_config_dir / config_file.name
                                shutil.copy2(config_file, dest)
                                logger.info(f"Restored: config/{config_file.name}")
                    
                finally:
                    # Cleanup temp directory
                    shutil.rmtree(temp_dir, ignore_errors=True)
                
                logger.info("Backup restored successfully")
                return True
                
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def list_backups(self) -> List[BackupInfo]:
        """List all available backups.
        
        Returns:
            List of BackupInfo objects
        """
        backups = []
        
        for backup_file in sorted(self.backup_dir.glob("*.zip"), reverse=True):
            try:
                info = self.get_backup_info(backup_file)
                if info:
                    backups.append(info)
            except Exception as e:
                logger.warning(f"Could not read backup {backup_file}: {e}")
        
        return backups
    
    def get_backup_info(self, backup_path: Path) -> Optional[BackupInfo]:
        """Get information about a backup file.
        
        Returns:
            BackupInfo object or None if invalid
        """
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                try:
                    metadata = json.loads(zipf.read("backup_metadata.json"))
                except Exception:
                    metadata = {}
                
                return BackupInfo(
                    filename=backup_path.name,
                    created_at=datetime.fromisoformat(metadata.get('created_at', '2000-01-01')),
                    size_bytes=backup_path.stat().st_size,
                    includes_database=metadata.get('includes_database', True),
                    includes_models=metadata.get('includes_models', True),
                    includes_config=metadata.get('includes_config', True),
                    version=metadata.get('version', 'unknown')
                )
        except Exception:
            return None
    
    def delete_backup(self, backup_name: str) -> bool:
        """Delete a backup file.
        
        Args:
            backup_name: Name of the backup file
        
        Returns:
            True if deleted, False otherwise
        """
        backup_path = self.backup_dir / backup_name
        
        if backup_path.exists():
            try:
                backup_path.unlink()
                logger.info(f"Deleted backup: {backup_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete backup: {e}")
                return False
        
        return False
    
    def auto_cleanup(self, max_backups: int = 10):
        """Remove old backups keeping only the most recent.
        
        Args:
            max_backups: Maximum number of backups to keep
        """
        backups = self.list_backups()
        
        if len(backups) > max_backups:
            for old_backup in backups[max_backups:]:
                self.delete_backup(old_backup.filename)
    
    def get_backup_size_total(self) -> int:
        """Get total size of all backups in bytes."""
        return sum(b.stat().st_size for b in self.backup_dir.glob("*.zip"))
    
    def schedule_auto_backup(self, interval: str = "daily") -> bool:
        """Schedule automatic backups.
        
        Args:
            interval: 'daily', 'weekly', or 'monthly'
        
        Note: This creates a marker file that can be checked on app startup.
        Actual scheduling should be done by the application's main loop.
        """
        schedule_file = self.backup_dir / "auto_backup_schedule.json"
        
        schedule = {
            'interval': interval,
            'last_backup': None,
            'next_backup': None
        }
        
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f)
        
        logger.info(f"Auto-backup scheduled: {interval}")
        return True
    
    def should_auto_backup(self) -> bool:
        """Check if an automatic backup is due."""
        schedule_file = self.backup_dir / "auto_backup_schedule.json"
        
        if not schedule_file.exists():
            return False
        
        try:
            with open(schedule_file, 'r') as f:
                schedule = json.load(f)
            
            last_backup = schedule.get('last_backup')
            interval = schedule.get('interval', 'daily')
            
            if last_backup is None:
                return True
            
            last_dt = datetime.fromisoformat(last_backup)
            now = datetime.now()
            
            if interval == 'daily':
                return (now - last_dt).days >= 1
            elif interval == 'weekly':
                return (now - last_dt).days >= 7
            elif interval == 'monthly':
                return (now - last_dt).days >= 30
            
        except Exception as e:
            logger.error(f"Error checking auto-backup schedule: {e}")
        
        return False


__all__ = ['BackupManager', 'BackupInfo']
