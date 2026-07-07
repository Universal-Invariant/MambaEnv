import subprocess
import json
import sys
import argparse
import platform
import datetime
import os
import glob


_search_cache = {}
IS_WINDOWS = platform.system() == "Windows"
PROTECTED_PACKAGES = {'pip', 'setuptools', 'wheel', 'distutils', 'python'}

def get_all_envs():
    """Retrieves all mamba environments, excluding the base installation."""
    result = subprocess.run("mamba env list --json", shell=True, capture_output=True, text=True)
    
    try:
        data = json.loads(result.stdout)
        all_paths = data.get('envs', [])
        env_names = []
        
        for path in all_paths:
            # os.path.basename extracts the last part of a path (e.g., 'bark' from '.../envs/bark')
            name = os.path.basename(path)
            
            # Filter: If the path doesn't contain 'envs', it's likely the base/root install.
            # We want to skip it so we don't accidentally try to "fix" your base shell.
            if 'envs' in path.lower() or 'envs' in path:
                env_names.append(name)
        
        return env_names
        
    except Exception as e:
        print(f"!! Could not parse mamba environment list. Error: {e}")
        return []

def get_env_json(env, command):
    """Runs the command with a delimiter to isolate JSON output."""
    # Handle Shell difference: Windows uses cmd.exe, Linux uses /bin/bash
    if IS_WINDOWS:
        full_cmd = f"mamba activate {env} & echo ----- JSON LIST ----- & {command}"
    else:
        # Note: 'source activate' requires your shell to have conda/mamba hooks initialized
        full_cmd = f"source activate {env} && echo ----- JSON LIST ----- && {command}"
        
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    
    if "----- JSON LIST -----" in result.stdout:
        _, json_part = result.stdout.split("----- JSON LIST -----", 1)
        json_part = json_part.strip()
        try:
            return json.loads(json_part)
        except json.JSONDecodeError:
            print(f"  [!] JSON Parse error for '{env}'")
            return None
    return None

def get_env_data(envs, prt=True):
    env_data = {}
    all_packages = set()

    for env in envs:
        if prt: print(f":: Fetching data for environment: {env}...")
        env_data[env] = {'mamba': {}, 'pip': {}, 'outdated': {}}

        mamba_json = get_env_json(env, "mamba list --json")
        if mamba_json:
            for pkg in mamba_json:
                name = pkg.get('name', '').lower()
                if name:
                    env_data[env]['mamba'][name] = pkg.get('version', '')
                    all_packages.add(name)

        pip_json = get_env_json(env, "pip list --format=json")
        if pip_json:
            for pkg in pip_json:
                name = pkg.get('name', '').lower()
                if name:
                    env_data[env]['pip'][name] = pkg.get('version', '')
                    all_packages.add(name)
                    
        # Outdated Data (Slowest, but necessary)
        out_json = get_env_json(env, "pip list --outdated --format=json")
        if out_json:
            for pkg in out_json:
                name = pkg.get('name', '').lower()
                env_data[env]['outdated'][name] = pkg.get('latest_version', '')                    

    return env_data, sorted(list(all_packages))

def check_mamba_availability(pkg_name):
    if pkg_name in _search_cache:
        return _search_cache[pkg_name]

    full_cmd = f"mamba search -f {pkg_name} --json"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    
    if "No entries matching" in result.stdout:
        _search_cache[pkg_name] = False
        return False
        
    try:
        data = json.loads(result.stdout)
        is_available = bool(data)
        _search_cache[pkg_name] = is_available
        return is_available
    except:
        pass
    _search_cache[pkg_name] = False
    return False


def get_mamba_package_info(pkg_name):
    if pkg_name in _search_cache: return _search_cache[pkg_name]
    
    # We call search to see if Mamba knows it
    full_cmd = f"mamba search --json {pkg_name}"
    result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    
    try:
        data = json.loads(result.stdout)
        info = data.get(pkg_name, [])
        _search_cache[pkg_name] = info
        return info
    except:
        _search_cache[pkg_name] = []
        return []
        

def should_migrate(pkg_name, mamba_info):
    """Channel-aware migration logic."""
    if not mamba_info: return False
    
    # Check if Intel channel is involved
    for version in mamba_info:
        channel_url = version.get('channel', '')
        if 'intel' in channel_url:
            return True # If Mamba has an Intel version, we trust it
    
    # Default: If it's a generic package and Mamba has it, safe to migrate
    return True
    

def get_pkg_action(pkg, m_ver, p_ver):
    """Determines the action needed for a package based on its state."""
    
    # 1. Force critical packages to be ignored by the cleanup process
    if pkg.lower() in PROTECTED_PACKAGES:
        return "OK"

    # 2. Existing logic for everything else
    is_double = (m_ver != "?" and p_ver != "?")
    is_pip_only = (m_ver == "?" and p_ver != "?")
    
    if is_double:
        return "RP" # Redundant Pip: Uninstall Pip version
    elif is_pip_only:
        if check_mamba_availability(pkg):
            return "MM" # Move to Mamba
        return "KEEP" # Cannot move, best state
    return "OK" # Best state


def perform_backups(envs):
    """
    Executes backups only if the environment has changed.
    Also prunes redundant backups from disk.
    """
    print(f":: Auditing/Backing up {len(envs)} environments...")
    
    for env in envs:
        # 1. Find existing backups for this env
        backup_files = sorted(glob.glob(f"{env}-backup-*.yml"), reverse=True)
        
        # 2. Pruning Logic: If the two most recent are identical, delete the newest
        if len(backup_files) >= 2:
            with open(backup_files[0], 'r', encoding='utf-8') as f1, \
                 open(backup_files[1], 'r', encoding='utf-8') as f2:
                if f1.read() == f2.read():
                    print(f"  -> Pruning redundant backup: {os.path.basename(backup_files[0])}")
                    os.remove(backup_files[0])
                    # Update our list after deletion
                    backup_files.pop(0)

        # 3. Perform current export
        print(f"  -> Checking '{env}'...", end="", flush=True)
        cmd = f"mamba env export -n {env} --no-builds"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f" [FAILED TO EXPORT]")
            continue

        new_content = result.stdout
        
        # 4. Comparison Logic: Skip if identical to the latest existing backup
        if backup_files:
            with open(backup_files[0], 'r', encoding='utf-8') as f:
                if f.read() == new_content:
                    print(f" [NO CHANGE - SKIPPED]")
                    continue

        # 5. Save new backup
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = f"{env}-backup-{timestamp}.yml"
        with open(backup_name, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f" [CREATED: {backup_name}]")
            
            

        
def generate_fix_commands(env_data, envs):
    comment_char = "#"
    comment_sep = ""
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    
    if IS_WINDOWS:
        print("@echo off\nsetlocal enabledelayedexpansion")
        comment_char = "::"
        comment_sep = "&"
    else:
        print("#!/bin/bash\nset -e") # set -e stops execution on error (replaces goto:error)
  
      
    print(f"{comment_char} \n")
    print(f"{comment_char} !!! WARNING: YOU ARE ABOUT TO MODIFY YOUR ENVIRONMENT(S)       !!!")
    print(f"{comment_char} !!! Uninstalling pip packages may break dependencies.          !!!")
    print(f"{comment_char} !!! An environment backup will be created before any changes.  !!!")
    print(f"{comment_char} \n")
    
    print(f"\n{comment_char} WARNING: If this script fails, revert to your backup .yml file.")
    
    for env in envs:
        print(f"\n{comment_char} --- Fixing Environment: {env} ---")
        
        # Activation syntax
        if IS_WINDOWS:
            print(f"call mamba activate {env} || (echo Failed to activate {env} & goto :error)")
        else:
            print(f"source activate {env} || {{ echo 'Failed to activate {env}'; exit 1; }}")
        
        # Create the Backup
        backup_name = f"{env}-backup-{timestamp}.yml"
        print(f"{comment_char} Creating backup: {backup_name}")
        print(f"mamba env export --no-builds > {backup_name}")        
        
        packages = set(env_data[env]['mamba'].keys()) | set(env_data[env]['pip'].keys())
        totalpks = 0
        for pkg in sorted(list(packages)):
            
            if pkg.lower() in PROTECTED_PACKAGES:
                continue
                
            m_ver = env_data[env]['mamba'].get(pkg, "?")
            p_ver = env_data[env]['pip'].get(pkg, "?")
            action = get_pkg_action(pkg, m_ver, p_ver)
            
            comment = f"{comment_char} [{action}] Env: {env} | Pkg: {pkg} | Mamba: {m_ver} | Pip: {p_ver}"
            
            if action == "RP":
                print(f"pip uninstall -y {pkg} {comment_sep} {comment}")
                totalpks = totalpks + 1
            elif action == "MM":
                totalpks = totalpks + 1
                # Using && ensures command only runs if uninstall succeeds                
                print(f"mamba install -y {pkg} && pip uninstall -y {pkg} {comment_sep} {comment}")
                
    
        print(f"{comment_char} Total Listed Packages/Total Packages = {totalpks}/{len(packages)}")
    
    if IS_WINDOWS:
        print("\n:error\necho [!] An error occurred. Stopping script to prevent contamination.\nexit /b 1")
        
def display_comparison(env_data, all_packages, envs, clean_mode=False):        
    if not all_packages:
        print("\nNo packages found to compare.")
        return

    # Print a clear key legendary descriptor for actionable auditing
    print("\nLegend:")
    print("  RP M/P  -> Redundant Pip (Installed in both Mamba & Pip. Clean up Pip!)")
    print("  MM ?/P  -> Move to Mamba  (Pip-only, but package exists in Mamba channels)")
    print("  ! P_VER -> Pure Pip Unique (Pip-only, missing from Mamba channels entirely)")
    print("  -       -> Not installed in this environment")

    col_width = 30
    header = f"\n{'Package':<30} | {'Latest':<10}"
    for env in envs:
        header += f" | {env:<{col_width}}"
    
    print(header)
    print("-" * len(header))

    totalpks = 0    
    # Populate the table row by row
    for pkg in all_packages:    
        states = []
        latest = next((env_data[e]['outdated'].get(pkg, "") for e in envs), "")
        
        for env in envs:
            m_ver = env_data[env]['mamba'].get(pkg, "?")
            p_ver = env_data[env]['pip'].get(pkg, "?")
            states.append((m_ver, p_ver))

        all_best = all(get_pkg_action(pkg, m, p) in ["OK", "KEEP"] for m, p in states)
        
        # Logic: If clean_mode is ON, skip "Best State" items
        if clean_mode and all_best:
            continue
            
        all_consistent = all(state == states[0] for state in states)

        # Only display if there is a discrepancy between environments
        if not all_consistent or len(envs) == 1:
            totalpks = totalpks + 1            
            row = f"{pkg:<30} | {latest:<10}"
            
            for m_ver, p_ver in states:
                is_double = (m_ver != "?" and p_ver != "?")
                is_pip_only = (m_ver == "?" and p_ver != "?")
                is_mamba_only = (m_ver != "?" and p_ver == "?")
                
                if m_ver == "?" and p_ver == "?":
                    # Clearer visual mapping for an uninstalled package space
                    cell = "-"
                
                elif is_double:
                    # Explicit layout for true duplication
                    cell = f"RP {m_ver}/{p_ver}"
                
                elif is_pip_only:
                    if check_mamba_availability(pkg):
                        cell = f"MM ?/{p_ver}"
                    else:
                        # Clean unique local indicator matching your design request
                        cell = f"! {p_ver}"
                
                elif is_mamba_only:
                    cell = f"{m_ver}"
                
                else:
                    cell = f"{m_ver}/{p_ver}"
                    if m_ver == p_ver:
                        cell = f"{m_ver}"
            
                row += f" | {cell:<{col_width}}"
            print(row)

    print(f"Total Listed Packages/Total Packages = {totalpks}/{len(all_packages)}")

         

  
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit, Backup, and Fix environments.")
    parser.add_argument("envs", nargs='*', help="List of environments to check")
    parser.add_argument("--all", action="store_true", help="Parse all environments found in mamba")
    parser.add_argument("--fix", action="store_true", help="Output batch commands to fix environments")
    parser.add_argument("--backup", action="store_true", help="Include commands to create YML backups")
    parser.add_argument("-c", "--clean", action="store_true", help="Only show packages that need action")
    args = parser.parse_args()

    # 1. Resolve Environments
    target_envs = args.envs
    if args.all:
        target_envs = get_all_envs()
        if not target_envs:
            print("No environments found.")
            sys.exit(1)

    if not target_envs:
        print("Please specify environments or use --all.")
        sys.exit(1)

    # 2. Lazy Data Collection
    # Only fetch data if we are going to display comparison or run a fix.
    # If we are ONLY doing --backup, we skip this entire heavy process.
    needs_data = args.fix or not (args.fix or args.backup)
    
    data = None
    packages = []
    
    if needs_data:
        data, packages = get_env_data(target_envs, not args.fix)

    # 3. Execution Logic
    if args.fix or args.backup:
        # Determine script header
        if IS_WINDOWS:
            print("@echo off\nsetlocal enabledelayedexpansion")
        else:
            print("#!/bin/bash\nset -e")
        
        # If backup requested, run it (Doesn't need package data)
        if args.backup:
            perform_backups(target_envs)
            
        # If fix requested, run it (Requires package data)
        if args.fix:
            if data is None: # Safety check
                print(f"!! Error: Cannot fix without gathering data.")
                sys.exit(1)
            generate_fix_commands(data, target_envs)
    else:
        # Default: Display comparison
        if data is not None:
            display_comparison(data, packages, target_envs, clean_mode=args.clean)