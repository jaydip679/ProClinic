import os

for root, dirs, files in os.walk('frontend/templates'):
    for f in files:
        if f.endswith('.html'):
            print(os.path.join(root, f))
