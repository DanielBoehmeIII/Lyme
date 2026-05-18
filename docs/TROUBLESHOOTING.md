# Troubleshooting

## "lyme: command not found"

```bash
# Python 3.10+ is required
python3 --version

# Install via pip
python3 -m pip install lyme

# Or run directly
python3 -m lyme --help
```

## "pip install fails"

```bash
# Upgrade pip first
python3 -m pip install --upgrade pip

# Try user install
python3 -m pip install --user lyme

# Check Python version (3.10+ required)
python3 --version
```

## "lyme heal finds no issues"

This is normal for well-maintained repos. Try a deeper scan:
```bash
lyme doctor
lyme v1-audit
```

## "ImportError on startup"

```bash
# Check install
python3 -m lyme doctor --install

# Reinstall
python3 -m pip install --upgrade lyme
```

## Known Issues

- `lyme heal --fix` applies safe patches but skips high-risk files
- Large repos (100k+ files) may take 30+ seconds to scan
- Windows WSL is recommended over native Windows

## Getting Help

```bash
lyme doctor --install   # Show install diagnostics
lyme v1-audit           # Show readiness score with evidence
```
