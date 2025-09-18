# Example usage of the revised DataManager class with logging

from src.core.data_manager import DataManager
import os
import logging

# Set up example logger
example_logger = logging.getLogger('DataManagerExample')
example_logger.setLevel(logging.INFO)

# Create console handler for examples
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    fmt='%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)
example_logger.addHandler(console_handler)
example_logger.propagate = False

def example_basic_usage():
    """Example of basic DataManager usage with default logging."""
    example_logger.info("=== Starting Basic Usage Example ===")
    
    try:
        # Create a new data manager instance with default logging
        dm = DataManager()
        example_logger.debug("Created DataManager instance")
        
        # Create a new database
        db_path = "example_database.fldb"
        if dm.create_database(db_path):
            example_logger.info("✅ Database created successfully")
        else:
            example_logger.error("❌ Failed to create database")
            return
        
        # Open the database
        if dm.open_database(db_path):
            example_logger.info("✅ Database opened successfully")
        else:
            example_logger.error("❌ Failed to open database")
            return
        
        # Get database information
        db_info = dm.get_database_info()
        if db_info:
            example_logger.info("✅ Retrieved Database Info:")
            example_logger.info(f"   Total files: {db_info['total_files']}")
            example_logger.info(f"   File types: {db_info['file_types']}")
            example_logger.info(f"   Database size: {db_info['file_size_mb']:.2f} MB")
        else:
            example_logger.warning("⚠️ Could not retrieve database information")
        
        # Clean up example database
        if os.path.exists(db_path):
            os.remove(db_path)
            example_logger.info("🧹 Cleaned up example database")
        else:
            example_logger.warning("⚠️ Database file not found for cleanup")
            
    except Exception as e:
        example_logger.critical(f"💥 Critical error in basic usage example: {e}")
    
    example_logger.info("=== Completed Basic Usage Example ===\n")

def example_advanced_logging():
    """Example of DataManager with advanced logging features."""
    example_logger.info("=== Starting Advanced Logging Example ===")
    
    try:
        # Create data manager with file logging
        log_file = "datamanager.log"
        dm = DataManager(log_file=log_file, log_level=logging.DEBUG)
        
        example_logger.info(f"📝 Logging to file: {log_file}")
        example_logger.info("📊 Available log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL")
        
        # Set different logging levels to demonstrate
        example_logger.info("--- Setting INFO level ---")
        DataManager.set_logging_level(logging.INFO)
        
        # Create a new database
        db_path = "advanced_example.fldb"
        if not dm.create_database(db_path):
            example_logger.error("Failed to create advanced example database")
            return
            
        if not dm.open_database(db_path):
            example_logger.error("Failed to open advanced example database")
            return
        
        example_logger.info("--- Setting DEBUG level ---")
        DataManager.set_logging_level(logging.DEBUG)
        
        # Get database info with debug logging
        db_info = dm.get_database_info()
        if not db_info:
            example_logger.warning("Could not retrieve database info in DEBUG mode")
        
        example_logger.info("--- Setting WARNING level (less verbose) ---")
        DataManager.set_logging_level(logging.WARNING)
        
        # This won't show in logs now since it's INFO level
        db_info_warning = dm.get_database_info()
        if db_info_warning:
            example_logger.debug("Retrieved database info in WARNING mode (this won't show)")
        
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
            example_logger.info("Cleaned up advanced example database")
        else:
            example_logger.warning("Advanced example database not found for cleanup")
            
        if os.path.exists(log_file):
            example_logger.info(f"📄 Check the log file '{log_file}' for detailed logs")
            # Uncomment next line to remove log file
            # os.remove(log_file)
        else:
            example_logger.warning(f"Log file '{log_file}' not found")
            
    except Exception as e:
        example_logger.critical(f"💥 Critical error in advanced logging example: {e}")
    
    example_logger.info("=== Completed Advanced Logging Example ===\n")

def example_with_file_operations():
    """Example showing file operations with logging."""
    example_logger.info("=== Starting File Operations Example ===")
    
    try:
        # Create data manager with INFO level logging
        dm = DataManager(log_file="file_operations.log", log_level=logging.INFO)
        example_logger.debug("Created DataManager with file logging enabled")
        
        # Create database
        db_path = "file_ops_example.fldb"
        if not dm.create_database(db_path):
            example_logger.error("Failed to create file operations database")
            return
            
        if not dm.open_database(db_path):
            example_logger.error("Failed to open file operations database")
            return
        
        # Example: Add files (commented out since we don't have actual files)
        example_logger.info("Adding example files (demonstration only)...")
        # flz_id = dm.add_flz_file("path/to/measurement.flz")
        # flr_id = dm.add_flr_file("path/to/raw_data.flr")
        
        # Demonstrate error handling for non-existent files
        result = dm.add_flz_file("non_existent.flz")
        if result is None:
            example_logger.warning("Expected: Could not add non-existent FLZ file")
        
        # List files
        files = dm.list_files()
        example_logger.info(f"Files in database: {len(files)}")
        
        # Get database statistics
        db_info = dm.get_database_info()
        if db_info:
            example_logger.info(f"Database size: {db_info['file_size_mb']:.2f} MB")
        else:
            example_logger.error("Could not retrieve database statistics")
        
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
            example_logger.info("🧹 File operations cleanup completed")
        else:
            example_logger.warning("File operations database not found for cleanup")
            
    except Exception as e:
        example_logger.critical(f"💥 Critical error in file operations example: {e}")
    
    example_logger.info("=== Completed File Operations Example ===\n")

def show_log_format_examples():
    """Show different log message formats."""
    example_logger.info("=== Starting Log Format Examples ===")
    
    try:
        dm = DataManager(log_level=logging.DEBUG)
        example_logger.debug("Created DataManager with DEBUG level logging")
        
        # Create a temporary database to demonstrate different log levels
        db_path = "log_demo.fldb"
        
        example_logger.info("Creating database (will show INFO level):")
        if not dm.create_database(db_path):
            example_logger.error("Failed to create log demo database")
            return
        
        example_logger.info("Opening database (will show INFO level):")
        if not dm.open_database(db_path):
            example_logger.error("Failed to open log demo database")
            return
        
        example_logger.info("Trying to open non-existent file (will show ERROR level):")
        result = dm.open_database("non_existent.fldb")
        if not result:
            example_logger.debug("Expected failure confirmed: non-existent file rejected")
        
        example_logger.info("Getting database info (will show DEBUG/INFO levels):")
        db_info = dm.get_database_info()
        if db_info:
            example_logger.debug("Successfully retrieved database information")
        else:
            example_logger.warning("Could not retrieve database information")
        
        # Demonstrate format switching
        example_logger.info("Switching to simple log format:")
        DataManager.configure_logging_format(simple=True)
        dm.get_database_info()
        
        example_logger.info("Switching back to detailed format:")
        DataManager.configure_logging_format(simple=False)
        dm.get_database_info()
        
        # Clean up
        if os.path.exists(db_path):
            os.remove(db_path)
            example_logger.info("🧹 Log format demo cleanup completed")
        else:
            example_logger.warning("Log demo database not found for cleanup")
            
    except Exception as e:
        example_logger.critical(f"💥 Critical error in log format examples: {e}")
    
    example_logger.info("=== Completed Log Format Examples ===\n")

def demonstrate_exception_logging():
    """Demonstrate proper exception logging with different levels."""
    example_logger.info("=== Starting Exception Logging Demonstration ===")
    
    try:
        dm = DataManager(log_level=logging.DEBUG)
        
        # Demonstrate WARNING level: Expected but non-critical issues
        example_logger.info("Testing WARNING level: Attempting to open non-existent database")
        result = dm.open_database("definitely_not_a_real_file.fldb")
        if not result:
            example_logger.warning("Expected: Database file not found (this is a warning, not an error)")
        
        # Demonstrate ERROR level: Unexpected failures that prevent operation
        example_logger.info("Testing ERROR level: Attempting operation without opened database")
        db_info = dm.get_database_info()
        if not db_info:
            example_logger.error("Expected: Cannot get database info without opened database")
        
        # Demonstrate successful operations with INFO/DEBUG
        example_logger.info("Testing INFO/DEBUG levels: Normal operations")
        if dm.create_database("exception_demo.fldb"):
            example_logger.info("✅ Database created successfully")
            
            if dm.open_database("exception_demo.fldb"):
                example_logger.info("✅ Database opened successfully")
                
                # This will generate DEBUG logs
                db_info = dm.get_database_info()
                if db_info:
                    example_logger.info(f"✅ Database info retrieved: {db_info['total_files']} files")
        
        # Demonstrate CRITICAL level with actual exception
        example_logger.info("Testing CRITICAL level: Forcing an exception")
        try:
            # This will cause an exception that should be logged as CRITICAL
            with open("/root/definitely_no_permission.txt", "w") as f:
                f.write("This should fail")
        except PermissionError as e:
            example_logger.critical(f"💥 Permission denied (demonstrating CRITICAL level): {e}")
        except Exception as e:
            example_logger.critical(f"💥 Unexpected exception (demonstrating CRITICAL level): {e}")
        
        # Clean up
        if os.path.exists("exception_demo.fldb"):
            os.remove("exception_demo.fldb")
            example_logger.info("🧹 Exception demo cleanup completed")
            
    except Exception as e:
        example_logger.critical(f"💥 Critical error in exception demonstration: {e}")
    
    example_logger.info("=== Completed Exception Logging Demonstration ===\n")

if __name__ == "__main__":
    example_logger.info("🚀 Starting DataManager Examples Suite")
    example_logger.info("=" * 60)
    
    try:
        # Run all examples with proper logging
        example_basic_usage()
        example_advanced_logging() 
        example_with_file_operations()
        show_log_format_examples()
        demonstrate_exception_logging()
        
        example_logger.info("=" * 60)
        example_logger.info("✅ All DataManager examples completed successfully")
        
    except KeyboardInterrupt:
        example_logger.warning("🛑 Examples interrupted by user")
    except Exception as e:
        example_logger.critical(f"💥 Fatal error in examples suite: {e}")
        raise