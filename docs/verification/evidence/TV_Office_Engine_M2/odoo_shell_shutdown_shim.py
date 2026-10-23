import psutil

def _tv_shell_no_children(self, recursive=False):
    # This one-shot Odoo shell process starts with preload=[]; avoid the local
    # macOS KERN_PROC_ALL permission failure in Odoo's shutdown-only cleanup.
    return []

psutil.Process.children = _tv_shell_no_children
