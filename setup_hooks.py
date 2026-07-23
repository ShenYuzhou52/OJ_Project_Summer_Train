#!/usr/bin/env python3
"""
设置 Git hooks
"""
import os
import shutil
import stat

def setup_git_hooks():
    """设置 Git hooks"""
    hooks_src = ".git-hooks"
    hooks_dst = ".git/hooks"
    
    if not os.path.exists(hooks_dst):
        print("❌ .git directory not found. Are you in a git repository?")
        return False
    
    if not os.path.exists(hooks_src):
        print("❌ .git-hooks directory not found")
        return False
    
    print("Setting up git hooks...")
    
    for hook_file in os.listdir(hooks_src):
        src = os.path.join(hooks_src, hook_file)
        dst = os.path.join(hooks_dst, hook_file)
        
        # 复制文件
        shutil.copy2(src, dst)
        
        # 添加执行权限 (Unix-like systems)
        if os.name != 'nt':
            st = os.stat(dst)
            os.chmod(dst, st.st_mode | stat.S_IEXEC)
        
        print(f"  ✓ Installed {hook_file}")
    
    print("✓ Git hooks installed successfully")
    return True

if __name__ == "__main__":
    setup_git_hooks()