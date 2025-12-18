import importlib.metadata

packages = [
    "oracledb",
    "clickhouse-driver",
    "pytest",
    "python-dotenv",
    "apscheduler",
    "streamlit",
    "plotly",
    "pandas"
]

print("Installed packages:")
for package in packages:
    try:
        version = importlib.metadata.version(package)
        print(f"{package}=={version}")
    except importlib.metadata.PackageNotFoundError:
        print(f"# {package} not installed")
