"""Model Versioning Module.

Manages model versions with rollback capability.
"""

import pickle
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import json
import hashlib

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelVersion:
    """Metadata for a model version."""
    version_id: str
    version_number: int
    created_at: datetime
    model_path: str
    scaler_path: str
    accuracy: float
    auc_roc: float
    brier_score: float
    hole_rate: float
    feature_count: int
    training_samples: int
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    is_active: bool = False
    model_type: str = "ensemble"  # ensemble, neural_network, etc.
    file_hash: str = ""


class ModelVersionManager:
    """Manages model versions with rollback capability.
    
    Features:
    - Version numbering (v1, v2, v3, etc.)
    - Metadata tracking
    - Rollback to previous versions
    - A/B testing support
    - Side-by-side comparison
    
    Example:
        >>> manager = ModelVersionManager()
        >>> version = manager.save_version(model, metrics, "Initial model")
        >>> manager.activate_version(version.version_id)
        >>> manager.rollback(version_number=1)
    """
    
    VERSIONS_DIR = Path("models/versions")
    METADATA_FILE = "version_metadata.json"
    
    def __init__(self, base_dir: str = None):
        """Initialize version manager.
        
        Args:
            base_dir: Base directory for storing versions
        """
        self.base_dir = Path(base_dir) if base_dir else self.VERSIONS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        self.versions: List[ModelVersion] = []
        self.active_version: Optional[ModelVersion] = None
        
        self._load_metadata()
    
    def _get_next_version_number(self) -> int:
        """Get the next version number."""
        if not self.versions:
            return 1
        return max(v.version_number for v in self.versions) + 1
    
    def _generate_version_id(self, version_number: int) -> str:
        """Generate unique version ID."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"v{version_number}_{timestamp}"
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        if not file_path.exists():
            return ""
        
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]
    
    def save_version(
        self,
        model,
        metrics: Dict[str, float],
        notes: str = "",
        hyperparameters: Dict[str, Any] = None,
        model_type: str = "ensemble"
    ) -> ModelVersion:
        """Save a new model version.
        
        Args:
            model: Trained model object
            metrics: Performance metrics
            notes: Optional notes about this version
            hyperparameters: Model hyperparameters
            model_type: Type of model
            
        Returns:
            ModelVersion metadata
        """
        version_number = self._get_next_version_number()
        version_id = self._generate_version_id(version_number)
        
        # Create version directory
        version_dir = self.base_dir / version_id
        version_dir.mkdir(parents=True, exist_ok=True)
        
        # Save model
        model_path = version_dir / "model.pkl"
        scaler_path = version_dir / "scaler.pkl"
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        # Save scaler if available
        scaler = getattr(model, 'scaler', None)
        if scaler is not None:
            with open(scaler_path, 'wb') as f:
                pickle.dump(scaler, f)
        
        # Create version metadata
        version = ModelVersion(
            version_id=version_id,
            version_number=version_number,
            created_at=datetime.now(),
            model_path=str(model_path),
            scaler_path=str(scaler_path) if scaler else "",
            accuracy=metrics.get('accuracy', 0.0),
            auc_roc=metrics.get('auc_roc', 0.0),
            brier_score=metrics.get('brier_score', 0.0),
            hole_rate=metrics.get('hole_rate', 0.0),
            feature_count=metrics.get('feature_count', 0),
            training_samples=metrics.get('training_samples', 0),
            hyperparameters=hyperparameters or {},
            notes=notes,
            model_type=model_type,
            file_hash=self._calculate_file_hash(model_path)
        )
        
        self.versions.append(version)
        self._save_metadata()
        
        logger.info(f"Saved model version {version_id} (v{version_number})")
        
        return version
    
    def activate_version(
        self,
        version_id: str = None,
        version_number: int = None
    ) -> bool:
        """Activate a model version.
        
        Args:
            version_id: Version ID to activate
            version_number: Or version number to activate
            
        Returns:
            True if successful
        """
        version = self.get_version(version_id, version_number)
        
        if not version:
            logger.error(f"Version not found: {version_id or version_number}")
            return False
        
        # Deactivate current
        for v in self.versions:
            v.is_active = False
        
        # Activate new
        version.is_active = True
        self.active_version = version
        
        # Copy to active location
        active_model_path = Path("models/overtime_model.pkl")
        active_scaler_path = Path("models/overtime_scaler.pkl")
        
        shutil.copy2(version.model_path, active_model_path)
        if version.scaler_path and Path(version.scaler_path).exists():
            shutil.copy2(version.scaler_path, active_scaler_path)
        
        self._save_metadata()
        
        logger.info(f"Activated version {version.version_id} (v{version.version_number})")
        
        return True
    
    def rollback(
        self,
        version_id: str = None,
        version_number: int = None
    ) -> bool:
        """Rollback to a previous version.
        
        Args:
            version_id: Version ID to rollback to
            version_number: Or version number to rollback to
            
        Returns:
            True if successful
        """
        if version_number is None and version_id is None:
            # Rollback to previous version
            if len(self.versions) < 2:
                logger.error("No previous version to rollback to")
                return False
            
            # Find currently active version
            current_idx = next(
                (i for i, v in enumerate(self.versions) if v.is_active),
                len(self.versions) - 1
            )
            
            if current_idx > 0:
                version_number = self.versions[current_idx - 1].version_number
            else:
                logger.error("Already at oldest version")
                return False
        
        success = self.activate_version(version_id, version_number)
        
        if success:
            logger.info(f"Rolled back to version {version_id or version_number}")
        
        return success
    
    def get_version(
        self,
        version_id: str = None,
        version_number: int = None
    ) -> Optional[ModelVersion]:
        """Get a specific version.
        
        Args:
            version_id: Version ID
            version_number: Or version number
            
        Returns:
            ModelVersion or None
        """
        for v in self.versions:
            if version_id and v.version_id == version_id:
                return v
            if version_number and v.version_number == version_number:
                return v
        return None
    
    def get_active_version(self) -> Optional[ModelVersion]:
        """Get the currently active version.
        
        Returns:
            Active ModelVersion or None
        """
        for v in self.versions:
            if v.is_active:
                return v
        return None
    
    def load_model(self, version: ModelVersion = None):
        """Load a model from a version.
        
        Args:
            version: Version to load (uses active if not provided)
            
        Returns:
            Loaded model object
        """
        version = version or self.get_active_version()
        
        if not version:
            raise ValueError("No version specified or active")
        
        model_path = Path(version.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        
        logger.info(f"Loaded model from version {version.version_id}")
        
        return model
    
    def compare_versions(
        self,
        version1_id: str = None,
        version2_id: str = None,
        version1_num: int = None,
        version2_num: int = None
    ) -> Dict[str, Any]:
        """Compare two versions side-by-side.
        
        Args:
            version1_id: First version ID
            version2_id: Second version ID
            version1_num: Or first version number
            version2_num: Or second version number
            
        Returns:
            Comparison dict
        """
        v1 = self.get_version(version1_id, version1_num)
        v2 = self.get_version(version2_id, version2_num)
        
        if not v1 or not v2:
            return {}
        
        return {
            'version_1': {
                'id': v1.version_id,
                'number': v1.version_number,
                'accuracy': v1.accuracy,
                'auc_roc': v1.auc_roc,
                'hole_rate': v1.hole_rate,
                'created_at': v1.created_at.isoformat()
            },
            'version_2': {
                'id': v2.version_id,
                'number': v2.version_number,
                'accuracy': v2.accuracy,
                'auc_roc': v2.auc_roc,
                'hole_rate': v2.hole_rate,
                'created_at': v2.created_at.isoformat()
            },
            'differences': {
                'accuracy_diff': v2.accuracy - v1.accuracy,
                'auc_roc_diff': v2.auc_roc - v1.auc_roc,
                'hole_rate_diff': v2.hole_rate - v1.hole_rate,
            },
            'recommendation': 'v2' if v2.accuracy > v1.accuracy else 'v1'
        }
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """List all versions with summary info.
        
        Returns:
            List of version summaries
        """
        return [
            {
                'version_id': v.version_id,
                'version_number': v.version_number,
                'created_at': v.created_at.isoformat(),
                'accuracy': v.accuracy,
                'auc_roc': v.auc_roc,
                'hole_rate': v.hole_rate,
                'is_active': v.is_active,
                'notes': v.notes
            }
            for v in sorted(self.versions, key=lambda x: x.version_number, reverse=True)
        ]
    
    def delete_version(
        self,
        version_id: str = None,
        version_number: int = None
    ) -> bool:
        """Delete a version.
        
        Args:
            version_id: Version ID to delete
            version_number: Or version number to delete
            
        Returns:
            True if successful
        """
        version = self.get_version(version_id, version_number)
        
        if not version:
            return False
        
        if version.is_active:
            logger.error("Cannot delete active version")
            return False
        
        # Remove files
        version_dir = Path(version.model_path).parent
        if version_dir.exists():
            shutil.rmtree(version_dir)
        
        # Remove from list
        self.versions.remove(version)
        self._save_metadata()
        
        logger.info(f"Deleted version {version.version_id}")
        
        return True
    
    def cleanup_old_versions(self, keep_count: int = 5) -> int:
        """Delete old versions, keeping the most recent ones.
        
        Args:
            keep_count: Number of versions to keep
            
        Returns:
            Number of versions deleted
        """
        sorted_versions = sorted(
            self.versions,
            key=lambda x: x.version_number,
            reverse=True
        )
        
        to_delete = sorted_versions[keep_count:]
        deleted = 0
        
        for v in to_delete:
            if not v.is_active:
                if self.delete_version(version_id=v.version_id):
                    deleted += 1
        
        logger.info(f"Cleaned up {deleted} old versions")
        
        return deleted
    
    def _save_metadata(self) -> None:
        """Save version metadata to disk."""
        metadata_path = self.base_dir / self.METADATA_FILE
        
        data = {
            'versions': [
                {
                    'version_id': v.version_id,
                    'version_number': v.version_number,
                    'created_at': v.created_at.isoformat(),
                    'model_path': v.model_path,
                    'scaler_path': v.scaler_path,
                    'accuracy': v.accuracy,
                    'auc_roc': v.auc_roc,
                    'brier_score': v.brier_score,
                    'hole_rate': v.hole_rate,
                    'feature_count': v.feature_count,
                    'training_samples': v.training_samples,
                    'hyperparameters': v.hyperparameters,
                    'notes': v.notes,
                    'is_active': v.is_active,
                    'model_type': v.model_type,
                    'file_hash': v.file_hash
                }
                for v in self.versions
            ]
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_metadata(self) -> None:
        """Load version metadata from disk."""
        metadata_path = self.base_dir / self.METADATA_FILE
        
        if not metadata_path.exists():
            return
        
        try:
            with open(metadata_path, 'r') as f:
                data = json.load(f)
            
            self.versions = [
                ModelVersion(
                    version_id=v['version_id'],
                    version_number=v['version_number'],
                    created_at=datetime.fromisoformat(v['created_at']),
                    model_path=v['model_path'],
                    scaler_path=v.get('scaler_path', ''),
                    accuracy=v.get('accuracy', 0),
                    auc_roc=v.get('auc_roc', 0),
                    brier_score=v.get('brier_score', 0),
                    hole_rate=v.get('hole_rate', 0),
                    feature_count=v.get('feature_count', 0),
                    training_samples=v.get('training_samples', 0),
                    hyperparameters=v.get('hyperparameters', {}),
                    notes=v.get('notes', ''),
                    is_active=v.get('is_active', False),
                    model_type=v.get('model_type', 'ensemble'),
                    file_hash=v.get('file_hash', '')
                )
                for v in data.get('versions', [])
            ]
            
            # Set active version
            self.active_version = next(
                (v for v in self.versions if v.is_active),
                None
            )
            
            logger.info(f"Loaded {len(self.versions)} version(s) from metadata")
            
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
