
"""
Advanced backup and data protection service
"""
import os
import shutil
import json
import gzip
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import hashlib
import sqlite3
from utils.helpers.logger import logger

class BackupService:
    """Comprehensive backup and recovery service"""
    
    def __init__(self, backup_root: str = "data/backups"):
        self.backup_root = Path(backup_root)
        self.backup_root.mkdir(parents=True, exist_ok=True)
        self.backup_config = self._load_backup_config()
        self.backup_log = self.backup_root / "backup_log.db"
        self._init_backup_log()
    
    def _load_backup_config(self) -> Dict[str, Any]:
        """Load backup configuration"""
        return {
            'retention_days': 30,
            'max_backup_size_gb': 10,
            'compression_enabled': True,
            'incremental_backup': True,
            'backup_schedule': {
                'daily': True,
                'weekly': True,
                'monthly': True
            },
            'backup_targets': [
                'data/storage',
                'data/cache',
                'logs',
                'config'
            ]
        }
    
    def _init_backup_log(self):
        """Initialize backup log database"""
        with sqlite3.connect(self.backup_log) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS backup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    backup_id TEXT UNIQUE,
                    backup_type TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    status TEXT,
                    size_bytes INTEGER,
                    files_count INTEGER,
                    checksum TEXT,
                    error_message TEXT
                )
            ''')
            conn.commit()
    
    def create_full_backup(self) -> Dict[str, Any]:
        """Create a complete system backup"""
        backup_id = f"full_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = self.backup_root / backup_id
        backup_dir.mkdir(exist_ok=True)
        
        logger.log_structured('info', 'Starting full backup', backup_id=backup_id)
        
        start_time = datetime.now()
        backup_result = {
            'backup_id': backup_id,
            'type': 'full',
            'start_time': start_time.isoformat(),
            'status': 'in_progress',
            'files_backed_up': 0,
            'total_size': 0,
            'errors': []
        }
        
        try:
            # Backup each target directory
            for target in self.backup_config['backup_targets']:
                target_path = Path(target)
                if target_path.exists():
                    self._backup_directory(target_path, backup_dir / target_path.name, backup_result)
            
            # Create backup manifest
            manifest = self._create_backup_manifest(backup_dir, backup_result)
            
            # Compress if enabled
            if self.backup_config['compression_enabled']:
                compressed_path = self._compress_backup(backup_dir)
                shutil.rmtree(backup_dir)
                backup_result['compressed_path'] = str(compressed_path)
            
            backup_result['status'] = 'completed'
            backup_result['end_time'] = datetime.now().isoformat()
            
            # Log backup completion
            self._log_backup_completion(backup_result)
            
            logger.log_structured('info', 'Full backup completed', 
                                backup_id=backup_id, 
                                files_count=backup_result['files_backed_up'],
                                size_mb=backup_result['total_size'] / (1024*1024))
            
        except Exception as e:
            backup_result['status'] = 'failed'
            backup_result['error'] = str(e)
            backup_result['end_time'] = datetime.now().isoformat()
            
            logger.log_error_with_context(e, {'backup_id': backup_id, 'backup_type': 'full'})
        
        return backup_result
    
    def create_incremental_backup(self, last_backup_time: Optional[datetime] = None) -> Dict[str, Any]:
        """Create incremental backup of changed files"""
        if last_backup_time is None:
            last_backup_time = self._get_last_backup_time()
        
        backup_id = f"incr_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = self.backup_root / backup_id
        backup_dir.mkdir(exist_ok=True)
        
        logger.log_structured('info', 'Starting incremental backup', 
                            backup_id=backup_id,
                            since=last_backup_time.isoformat() if last_backup_time else 'never')
        
        start_time = datetime.now()
        backup_result = {
            'backup_id': backup_id,
            'type': 'incremental',
            'start_time': start_time.isoformat(),
            'since': last_backup_time.isoformat() if last_backup_time else None,
            'status': 'in_progress',
            'files_backed_up': 0,
            'total_size': 0,
            'errors': []
        }
        
        try:
            # Backup only changed files
            for target in self.backup_config['backup_targets']:
                target_path = Path(target)
                if target_path.exists():
                    self._backup_changed_files(target_path, backup_dir / target_path.name, 
                                             last_backup_time, backup_result)
            
            # Create backup manifest
            manifest = self._create_backup_manifest(backup_dir, backup_result)
            
            backup_result['status'] = 'completed'
            backup_result['end_time'] = datetime.now().isoformat()
            
            self._log_backup_completion(backup_result)
            
            logger.log_structured('info', 'Incremental backup completed', 
                                backup_id=backup_id,
                                files_count=backup_result['files_backed_up'])
            
        except Exception as e:
            backup_result['status'] = 'failed'
            backup_result['error'] = str(e)
            backup_result['end_time'] = datetime.now().isoformat()
            
            logger.log_error_with_context(e, {'backup_id': backup_id, 'backup_type': 'incremental'})
        
        return backup_result
    
    def restore_backup(self, backup_id: str, restore_path: Optional[str] = None) -> Dict[str, Any]:
        """Restore from backup"""
        backup_path = self.backup_root / backup_id
        compressed_backup = self.backup_root / f"{backup_id}.tar.gz"
        
        if compressed_backup.exists():
            backup_path = self._decompress_backup(compressed_backup)
        elif not backup_path.exists():
            return {'status': 'failed', 'error': f'Backup {backup_id} not found'}
        
        logger.log_structured('info', 'Starting backup restore', 
                            backup_id=backup_id, restore_path=restore_path)
        
        restore_result = {
            'backup_id': backup_id,
            'restore_path': restore_path or '.',
            'start_time': datetime.now().isoformat(),
            'status': 'in_progress',
            'files_restored': 0,
            'errors': []
        }
        
        try:
            # Load backup manifest
            manifest_path = backup_path / 'backup_manifest.json'
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
            else:
                manifest = {}
            
            # Restore files
            target_path = Path(restore_path) if restore_path else Path('.')
            self._restore_directory(backup_path, target_path, restore_result)
            
            restore_result['status'] = 'completed'
            restore_result['end_time'] = datetime.now().isoformat()
            
            logger.log_structured('info', 'Backup restore completed', 
                                backup_id=backup_id,
                                files_restored=restore_result['files_restored'])
            
        except Exception as e:
            restore_result['status'] = 'failed'
            restore_result['error'] = str(e)
            restore_result['end_time'] = datetime.now().isoformat()
            
            logger.log_error_with_context(e, {'backup_id': backup_id, 'operation': 'restore'})
        
        return restore_result
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups"""
        backups = []
        
        with sqlite3.connect(self.backup_log) as conn:
            cursor = conn.execute('''
                SELECT backup_id, backup_type, start_time, end_time, status, 
                       size_bytes, files_count, checksum
                FROM backup_history 
                ORDER BY start_time DESC
            ''')
            
            for row in cursor.fetchall():
                backup_info = {
                    'backup_id': row[0],
                    'type': row[1],
                    'start_time': row[2],
                    'end_time': row[3],
                    'status': row[4],
                    'size_bytes': row[5],
                    'files_count': row[6],
                    'checksum': row[7]
                }
                backups.append(backup_info)
        
        return backups
    
    def cleanup_old_backups(self) -> Dict[str, Any]:
        """Clean up old backups based on retention policy"""
        cutoff_date = datetime.now() - timedelta(days=self.backup_config['retention_days'])
        
        cleanup_result = {
            'deleted_backups': [],
            'freed_space_bytes': 0,
            'errors': []
        }
        
        with sqlite3.connect(self.backup_log) as conn:
            cursor = conn.execute('''
                SELECT backup_id, size_bytes FROM backup_history 
                WHERE start_time < ? AND status = 'completed'
            ''', (cutoff_date.isoformat(),))
            
            old_backups = cursor.fetchall()
            
            for backup_id, size_bytes in old_backups:
                try:
                    # Delete backup files
                    backup_path = self.backup_root / backup_id
                    compressed_path = self.backup_root / f"{backup_id}.tar.gz"
                    
                    if backup_path.exists():
                        shutil.rmtree(backup_path)
                    if compressed_path.exists():
                        compressed_path.unlink()
                    
                    # Remove from log
                    conn.execute('DELETE FROM backup_history WHERE backup_id = ?', (backup_id,))
                    
                    cleanup_result['deleted_backups'].append(backup_id)
                    cleanup_result['freed_space_bytes'] += size_bytes or 0
                    
                except Exception as e:
                    cleanup_result['errors'].append(f"Failed to delete {backup_id}: {str(e)}")
            
            conn.commit()
        
        logger.log_structured('info', 'Backup cleanup completed', 
                            deleted_count=len(cleanup_result['deleted_backups']),
                            freed_mb=cleanup_result['freed_space_bytes'] / (1024*1024))
        
        return cleanup_result
    
    def _backup_directory(self, source_dir: Path, backup_dir: Path, result: Dict[str, Any]):
        """Backup a directory recursively"""
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for item in source_dir.rglob('*'):
            if item.is_file():
                try:
                    relative_path = item.relative_to(source_dir)
                    backup_file = backup_dir / relative_path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(item, backup_file)
                    result['files_backed_up'] += 1
                    result['total_size'] += item.stat().st_size
                    
                except Exception as e:
                    result['errors'].append(f"Failed to backup {item}: {str(e)}")
    
    def _backup_changed_files(self, source_dir: Path, backup_dir: Path, 
                            since: datetime, result: Dict[str, Any]):
        """Backup only files changed since the specified time"""
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        for item in source_dir.rglob('*'):
            if item.is_file():
                try:
                    # Check if file was modified since last backup
                    mod_time = datetime.fromtimestamp(item.stat().st_mtime)
                    if mod_time > since:
                        relative_path = item.relative_to(source_dir)
                        backup_file = backup_dir / relative_path
                        backup_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        shutil.copy2(item, backup_file)
                        result['files_backed_up'] += 1
                        result['total_size'] += item.stat().st_size
                        
                except Exception as e:
                    result['errors'].append(f"Failed to backup {item}: {str(e)}")
    
    def _create_backup_manifest(self, backup_dir: Path, backup_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create backup manifest file"""
        manifest = {
            'backup_id': backup_result['backup_id'],
            'backup_type': backup_result['type'],
            'created_at': backup_result['start_time'],
            'files_count': backup_result['files_backed_up'],
            'total_size': backup_result['total_size'],
            'checksum': self._calculate_directory_checksum(backup_dir)
        }
        
        manifest_path = backup_dir / 'backup_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return manifest
    
    def _compress_backup(self, backup_dir: Path) -> Path:
        """Compress backup directory"""
        compressed_path = backup_dir.with_suffix('.tar.gz')
        shutil.make_archive(str(backup_dir), 'gztar', backup_dir)
        return compressed_path
    
    def _decompress_backup(self, compressed_path: Path) -> Path:
        """Decompress backup archive"""
        extract_dir = compressed_path.with_suffix('')
        shutil.unpack_archive(str(compressed_path), str(extract_dir))
        return extract_dir
    
    def _calculate_directory_checksum(self, directory: Path) -> str:
        """Calculate checksum for directory contents"""
        hash_md5 = hashlib.md5()
        
        for file_path in sorted(directory.rglob('*')):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def _get_last_backup_time(self) -> Optional[datetime]:
        """Get timestamp of last successful backup"""
        with sqlite3.connect(self.backup_log) as conn:
            cursor = conn.execute('''
                SELECT MAX(end_time) FROM backup_history 
                WHERE status = 'completed'
            ''')
            result = cursor.fetchone()
            
            if result[0]:
                return datetime.fromisoformat(result[0])
        
        return None
    
    def _log_backup_completion(self, backup_result: Dict[str, Any]):
        """Log backup completion to database"""
        with sqlite3.connect(self.backup_log) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO backup_history 
                (backup_id, backup_type, start_time, end_time, status, 
                 size_bytes, files_count, checksum, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                backup_result['backup_id'],
                backup_result['type'],
                backup_result['start_time'],
                backup_result.get('end_time'),
                backup_result['status'],
                backup_result.get('total_size', 0),
                backup_result.get('files_backed_up', 0),
                backup_result.get('checksum'),
                backup_result.get('error')
            ))
            conn.commit()
    
    def _restore_directory(self, backup_dir: Path, target_dir: Path, result: Dict[str, Any]):
        """Restore directory from backup"""
        for item in backup_dir.rglob('*'):
            if item.is_file() and item.name != 'backup_manifest.json':
                try:
                    relative_path = item.relative_to(backup_dir)
                    target_file = target_dir / relative_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(item, target_file)
                    result['files_restored'] += 1
                    
                except Exception as e:
                    result['errors'].append(f"Failed to restore {item}: {str(e)}")

# Global backup service instance
backup_service = BackupService()
