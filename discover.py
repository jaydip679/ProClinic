import os

for root, dirs, files in os.walk('backend'):
    if '__pycache__' in dirs: dirs.remove('__pycache__')
    if 'migrations' in dirs: dirs.remove('migrations')
    for f in files:
        if f.endswith('.py'):
            print(os.path.join(root, f))
