import shutil
import os
from logger import log
from error_handler import report_error

def cleanup(profile_dir):
    try:
        if os.path.exists(profile_dir):
            shutil.rmtree(profile_dir, ignore_errors=True)
            log("Temporary profile + all traces deleted successfully")
    except Exception as e:
        log(f"Cleanup error: {e}", "WARNING")
        report_error(e, source_module="cleanup",
                     extra_context="Could not delete the temporary Chrome profile folder. You can delete it manually.")