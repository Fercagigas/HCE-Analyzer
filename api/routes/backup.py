
"""
Backup API routes
"""
from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from typing import Dict, Any, Optional
from services.backup.backup_service import backup_service
from utils.helpers.logger import logger

router = APIRouter()

@router.post("/create-backup")
async def create_backup(
    request: Request,
    background_tasks: BackgroundTasks,
    backup_data: Dict[str, Any]
):
    """Create system backup"""
    user_id = request.state.user_id
    backup_type = backup_data.get('type', 'full')  # full or incremental
    
    if backup_type not in ['full', 'incremental']:
        raise HTTPException(status_code=400, detail="Invalid backup type")
    
    logger.log_user_action(user_id, 'initiate_backup', {
        'backup_type': backup_type
    })
    
    try:
        if backup_type == 'full':
            # Run backup in background
            background_tasks.add_task(backup_service.create_full_backup)
            message = "Full backup initiated"
        else:
            background_tasks.add_task(backup_service.create_incremental_backup)
            message = "Incremental backup initiated"
        
        return {
            'success': True,
            'message': message,
            'backup_type': backup_type
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'backup_type': backup_type,
            'operation': 'create_backup'
        })
        raise HTTPException(status_code=500, detail="Backup initiation failed")

@router.get("/backup-history")
async def get_backup_history(request: Request):
    """Get backup history"""
    user_id = request.state.user_id
    
    try:
        backups = backup_service.list_backups()
        
        logger.log_user_action(user_id, 'view_backup_history', {
            'backups_count': len(backups)
        })
        
        return {
            'success': True,
            'backups': backups
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'get_backup_history'
        })
        raise HTTPException(status_code=500, detail="Failed to retrieve backup history")

@router.post("/restore-backup")
async def restore_backup(
    request: Request,
    background_tasks: BackgroundTasks,
    restore_data: Dict[str, Any]
):
    """Restore from backup"""
    user_id = request.state.user_id
    backup_id = restore_data.get('backup_id')
    restore_path = restore_data.get('restore_path')
    
    if not backup_id:
        raise HTTPException(status_code=400, detail="Backup ID is required")
    
    logger.log_user_action(user_id, 'initiate_restore', {
        'backup_id': backup_id,
        'restore_path': restore_path
    })
    
    try:
        # Run restore in background
        background_tasks.add_task(
            backup_service.restore_backup,
            backup_id,
            restore_path
        )
        
        return {
            'success': True,
            'message': 'Restore initiated',
            'backup_id': backup_id
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'backup_id': backup_id,
            'operation': 'restore_backup'
        })
        raise HTTPException(status_code=500, detail="Restore initiation failed")

@router.post("/cleanup-backups")
async def cleanup_old_backups(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Clean up old backups"""
    user_id = request.state.user_id
    
    logger.log_user_action(user_id, 'initiate_backup_cleanup')
    
    try:
        # Run cleanup in background
        background_tasks.add_task(backup_service.cleanup_old_backups)
        
        return {
            'success': True,
            'message': 'Backup cleanup initiated'
        }
        
    except Exception as e:
        logger.log_error_with_context(e, {
            'user_id': user_id,
            'operation': 'cleanup_backups'
        })
        raise HTTPException(status_code=500, detail="Cleanup initiation failed")
