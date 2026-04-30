import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from version import __version__

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
iss_path = os.path.join(root, "shrinkify.iss")

with open(iss_path, "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(
    r"(AppVersion=)[^\r\n]+",
    r"\g<1>" + __version__,
    content,
)

with open(iss_path, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Updated shrinkify.iss version to {__version__}")
