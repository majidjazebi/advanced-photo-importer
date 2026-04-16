# -*- coding: utf-8 -*-
# Copyright (C) 2026 Majid Jazebi
# Web: Geotechzone.com
# All rights reserved.
# This plugin is licensed under GNU GPL v3.
"""
Error Handler for Advanced Photo Importer
Centralized error handling utilities to prevent crashes and provide clear error messages. 
"""

import os
import traceback
from functools import wraps
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtWidgets import QMessageBox


class ErrorHandler:
    """Centralized error handling for the plugin."""
    
    LOG_TAG = 'Photo Plugin'
    
    @staticmethod
    def log_error(message, exception=None, show_user=False, parent=None):
        """
        Log an error with optional user notification.
        
        Args:
            message: Error message
            exception: Exception object (optional)
            show_user: Whether to show message box to user
            parent: Parent widget for message box
        """
        full_message = message
        if exception:
            full_message = f"{message}: {str(exception)}"
        
        # Log to QGIS message log
        QgsMessageLog.logMessage(
            f"[ERROR] {full_message}",
            ErrorHandler.LOG_TAG,
            Qgis.Critical
        )
        
        # Log stack trace if exception exists
        if exception:
            stack_trace = traceback.format_exc()
            QgsMessageLog.logMessage(
                f"[STACK TRACE]\n{stack_trace}",
                ErrorHandler.LOG_TAG,
                Qgis.Critical
            )
        
        # Show to user if requested
        if show_user and parent:
            QMessageBox.critical(
                parent,
                "Photo Plugin Error",
                f"{message}\n\nCheck the QGIS log panel for details."
            )
    
    @staticmethod
    def log_warning(message, show_user=False, parent=None):
        """Log a warning message."""
        QgsMessageLog.logMessage(
            f"[WARNING] {message}",
            ErrorHandler.LOG_TAG,
            Qgis.Warning
        )
        
        if show_user and parent:
            QMessageBox.warning(
                parent,
                "Photo Plugin Warning",
                message
            )
    
    @staticmethod
    def log_info(message):
        """Log an info message."""
        QgsMessageLog.logMessage(
            f"[INFO] {message}",
            ErrorHandler.LOG_TAG,
            Qgis.Info
        )
    
    @staticmethod
    def safe_start_editing(layer, operation_name="operation"):
        """
        Safely start editing a layer with proper error handling.
        
        Returns:
            bool: True if editing started successfully, False otherwise
        """
        if not layer or not layer.isValid():
            ErrorHandler.log_error(
                f"Cannot start editing for {operation_name}: Layer is invalid or None"
            )
            return False
        
        try:
            if layer.isEditable():
                ErrorHandler.log_info(f"Layer already in edit mode for {operation_name}")
                return True
            
            if not layer.startEditing():
                ErrorHandler.log_error(
                    f"Failed to start editing layer for {operation_name}: startEditing() returned False"
                )
                return False
            
            ErrorHandler.log_info(f"Successfully started editing for {operation_name}")
            return True
            
        except RuntimeError as e:
            ErrorHandler.log_error(
                f"RuntimeError when starting edit for {operation_name}",
                e
            )
            return False
        except Exception as e:
            ErrorHandler.log_error(
                f"Unexpected error when starting edit for {operation_name}",
                e
            )
            return False
    
    @staticmethod
    def safe_commit_changes(layer, operation_name="operation", rollback_on_fail=True):
        """
        Safely commit changes to a layer with proper error handling.
        
        Args:
            layer: The layer to commit
            operation_name: Description of the operation
            rollback_on_fail: Whether to rollback on failure
        
        Returns:
            bool: True if commit successful, False otherwise
        """
        if not layer or not layer.isValid():
            ErrorHandler.log_error(
                f"Cannot commit changes for {operation_name}: Layer is invalid or None"
            )
            return False
        
        try:
            if not layer.isEditable():
                ErrorHandler.log_warning(
                    f"Layer not in edit mode for {operation_name}, nothing to commit"
                )
                return True
            
            if not layer.commitChanges():
                error_msg = layer.commitErrors()
                ErrorHandler.log_error(
                    f"Failed to commit changes for {operation_name}: {error_msg}"
                )
                
                if rollback_on_fail:
                    ErrorHandler.log_info(f"Rolling back changes for {operation_name}")
                    layer.rollBack()
                
                return False
            
            ErrorHandler.log_info(f"Successfully committed changes for {operation_name}")
            return True
            
        except RuntimeError as e:
            ErrorHandler.log_error(
                f"RuntimeError when committing changes for {operation_name}",
                e
            )
            if rollback_on_fail and layer.isEditable():
                layer.rollBack()
            return False
        except Exception as e:
            ErrorHandler.log_error(
                f"Unexpected error when committing changes for {operation_name}",
                e
            )
            if rollback_on_fail and layer.isEditable():
                layer.rollBack()
            return False
    
    @staticmethod
    def safe_rollback(layer, operation_name="operation"):
        """Safely rollback layer changes."""
        if not layer or not layer.isValid():
            return
        
        try:
            if layer.isEditable():
                layer.rollBack()
                ErrorHandler.log_info(f"Rolled back changes for {operation_name}")
        except Exception as e:
            ErrorHandler.log_error(
                f"Error during rollback for {operation_name}",
                e
            )
    
    @staticmethod
    def safe_file_exists(filepath, operation_name="file operation"):
        """
        Check if file exists with error handling.
        
        Returns:
            bool: True if file exists, False otherwise
        """
        try:
            if not filepath:
                ErrorHandler.log_warning(
                    f"Empty file path provided for {operation_name}"
                )
                return False
            
            exists = os.path.exists(filepath)
            if not exists:
                ErrorHandler.log_warning(
                    f"File does not exist for {operation_name}: {filepath}"
                )
            return exists
            
        except Exception as e:
            ErrorHandler.log_error(
                f"Error checking file existence for {operation_name}",
                e
            )
            return False
    
    @staticmethod
    def safe_open_file(filepath, mode='r', operation_name="file operation"):
        """
        Safely open a file with error handling.
        
        Returns:
            file handle or None if failed
        """
        try:
            if not ErrorHandler.safe_file_exists(filepath, operation_name):
                return None
            
            file_handle = open(filepath, mode)
            return file_handle
            
        except PermissionError as e:
            ErrorHandler.log_error(
                f"Permission denied for {operation_name}: {filepath}",
                e
            )
            return None
        except IOError as e:
            ErrorHandler.log_error(
                f"IO error for {operation_name}: {filepath}",
                e
            )
            return None
        except Exception as e:
            ErrorHandler.log_error(
                f"Unexpected error opening file for {operation_name}: {filepath}",
                e
            )
            return None
    
    @staticmethod
    def safe_get_feature(layer, feature_id, operation_name="get feature"):
        """
        Safely get a feature from layer.
        
        Returns:
            QgsFeature or None if failed
        """
        try:
            if not layer or not layer.isValid():
                ErrorHandler.log_error(
                    f"Cannot get feature for {operation_name}: Layer is invalid"
                )
                return None
            
            feature = layer.getFeature(feature_id)
            if not feature.isValid():
                ErrorHandler.log_warning(
                    f"Feature {feature_id} is invalid for {operation_name}"
                )
                return None
            
            return feature
            
        except RuntimeError as e:
            ErrorHandler.log_error(
                f"RuntimeError getting feature {feature_id} for {operation_name}",
                e
            )
            return None
        except Exception as e:
            ErrorHandler.log_error(
                f"Unexpected error getting feature {feature_id} for {operation_name}",
                e
            )
            return None
    
    @staticmethod
    def safe_layer_operation(func):
        """
        Decorator for layer operations that need edit mode.
        Automatically handles startEditing, commitChanges, and rollback.
        
        Usage:
            @ErrorHandler.safe_layer_operation
            def my_layer_function(layer, ...):
                # Your code here
                return True  # or False on failure
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract layer from first argument
            layer = args[0] if args else None
            operation_name = func.__name__
            
            if not layer or not layer.isValid():
                ErrorHandler.log_error(
                    f"Invalid layer in {operation_name}"
                )
                return False
            
            # Start editing
            was_editing = layer.isEditable()
            if not was_editing:
                if not ErrorHandler.safe_start_editing(layer, operation_name):
                    return False
            
            try:
                # Execute the actual function
                result = func(*args, **kwargs)
                
                # Commit if we started editing
                if not was_editing:
                    if result:  # Only commit if function succeeded
                        if not ErrorHandler.safe_commit_changes(layer, operation_name):
                            return False
                    else:
                        ErrorHandler.safe_rollback(layer, operation_name)
                
                return result
                
            except Exception as e:
                ErrorHandler.log_error(
                    f"Exception in {operation_name}",
                    e
                )
                if not was_editing:
                    ErrorHandler.safe_rollback(layer, operation_name)
                return False
        
        return wrapper
    
    @staticmethod
    def validate_coordinates(lat, lon, operation_name="coordinate validation"):
        """
        Validate GPS coordinates.
        
        Returns:
            bool: True if valid, False otherwise
        """
        try:
            if lat is None or lon is None:
                ErrorHandler.log_warning(
                    f"Null coordinates for {operation_name}"
                )
                return False
            
            lat = float(lat)
            lon = float(lon)
            
            if not (-90 <= lat <= 90):
                ErrorHandler.log_error(
                    f"Invalid latitude {lat} for {operation_name} (must be -90 to 90)"
                )
                return False
            
            if not (-180 <= lon <= 180):
                ErrorHandler.log_error(
                    f"Invalid longitude {lon} for {operation_name} (must be -180 to 180)"
                )
                return False
            
            # Check for suspicious coordinates (0,0 - Gulf of Guinea)
            if lat == 0.0 and lon == 0.0:
                ErrorHandler.log_warning(
                    f"Suspicious coordinates (0,0) for {operation_name} - possible GPS error"
                )
            
            return True
            
        except (ValueError, TypeError) as e:
            ErrorHandler.log_error(
                f"Invalid coordinate format for {operation_name}",
                e
            )
            return False
    
    @staticmethod
    def create_error_context(operation, **kwargs):
        """
        Create a context string for error logging with relevant details.
        
        Args:
            operation: Operation name
            **kwargs: Additional context (layer_name, feature_id, file_path, etc.)
        
        Returns:
            str: Formatted context string
        """
        context_parts = [f"Operation: {operation}"]
        
        for key, value in kwargs.items():
            context_parts.append(f"{key}: {value}")
        
        return " | ".join(context_parts)


# Convenience function for quick error logging
def log_plugin_error(message, exception=None, show_user=False, parent=None):
    """Quick access to error logging."""
    ErrorHandler.log_error(message, exception, show_user, parent)


def log_plugin_warning(message, show_user=False, parent=None):
    """Quick access to warning logging."""
    ErrorHandler.log_warning(message, show_user, parent)


def log_plugin_info(message):
    """Quick access to info logging."""
    ErrorHandler.log_info(message)
