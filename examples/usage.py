# examples/usage.py

from crowsight import CodebaseAnalyzer
from crowsight.filters.node_filter import NodeCategory

def main():
    an = CodebaseAnalyzer("examples/my_project", "examples/project.crs", log_config={"level":"INFO"}, force=True)
    an.analyze()

    print("Imports:", an.find(node_type=NodeCategory.IMPORT))
    print("Todos:", an.find(node_type="comment", pattern=r"\bTODO\b|\bFIXME\b"))
    print("Go functions ≥2 args:",
          an.find(node_type=NodeCategory.FUNCTION, args_min=2, lang="go"))
    print("Rust structs:", an.find(node_type="struct_item"))

if __name__ == "__main__":
    main()
