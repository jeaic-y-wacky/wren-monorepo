import json

from agent.tools.static_analyzer import StaticAnalyzer

analyzer = StaticAnalyzer()
print(f"Semgrep availab: {analyzer._is_semgrep_available()}")

# Dangerous code test
code = """
import os
os.system("rm -rf /")
"""
result = analyzer.analyze(code)
print(json.dumps(result.to_dict(), indent=2))
