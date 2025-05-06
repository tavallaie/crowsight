from crowsight.codebase_analyzer import CodebaseAnalyzer

def main():
    analyzer = CodebaseAnalyzer("examples/my_project", manifest="examples/manifest.json")
    analyzer.analyze()
    analyzer.write_manifest()
    print("Functions:", analyzer.find_functions(min_args=2))
    print("Imports:", analyzer.find_imports())

if __name__ == "__main__":
    main()
