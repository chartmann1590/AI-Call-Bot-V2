# CallBot Directory Structure Changes

## Overview

The CallBot project has been reorganized to move all Python source code into a dedicated `src/` directory. This provides better organization and follows Python packaging best practices.

## Changes Made

### 1. Directory Structure

**Before:**
```
A-Call-Bot-V2/
├── app.py
├── config.py
├── models.py
├── sip_client.py
├── whisper_transcriber.py
├── ollama_client.py
├── tts_engines.py
└── ...
```

**After:**
```
A-Call-Bot-V2/
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── models.py
│   ├── sip_client.py
│   ├── whisper_transcriber.py
│   ├── ollama_client.py
│   └── tts_engines.py
├── callbot.py          # New main entry point
├── run.py              # Updated development entry point
├── test_structure.py   # New structure test
└── ...
```

### 2. Import Updates

All import statements have been updated to use the new `src.` prefix:

**Before:**
```python
from config import config
from models import db, Call, Settings
from sip_client import SIPClient
```

**After:**
```python
from src.config import config
from src.models import db, Call, Settings
from src.sip_client import SIPClient
```

### 3. Entry Points

Multiple entry points are now available:

1. **`callbot.py`** - Main entry point (recommended)
2. **`run.py`** - Development server entry point
3. **`python -m src.app`** - Module execution
4. **`./start.sh`** - Automated startup script

### 4. Updated Files

#### Core Application Files
- ✅ `src/app.py` - Updated imports
- ✅ `src/config.py` - No changes needed
- ✅ `src/models.py` - No changes needed
- ✅ `src/sip_client.py` - No changes needed
- ✅ `src/whisper_transcriber.py` - No changes needed
- ✅ `src/ollama_client.py` - No changes needed
- ✅ `src/tts_engines.py` - No changes needed

#### Entry Point Files
- ✅ `callbot.py` - New main entry point
- ✅ `run.py` - Updated to import from src
- ✅ `test_setup.py` - Updated imports
- ✅ `test_structure.py` - New structure test

#### Configuration Files
- ✅ `Dockerfile` - Updated CMD to use callbot.py
- ✅ `start.sh` - Updated to use callbot.py
- ✅ `README.md` - Updated project structure and commands

### 5. Benefits of New Structure

1. **Better Organization**: All Python code is in one place
2. **Cleaner Root Directory**: Configuration and entry points at root level
3. **Python Package**: `src/` is now a proper Python package
4. **Multiple Entry Points**: Different ways to run the application
5. **Easier Testing**: Clear separation of source code and tests
6. **Better Deployment**: Docker and scripts work with new structure

### 6. How to Run CallBot

#### Development
```bash
# Option 1: Main entry point
python callbot.py

# Option 2: Development server
python run.py

# Option 3: Module execution
python -m src.app

# Option 4: Automated startup
./start.sh
```

#### Docker
```bash
# Build and run with Docker
docker-compose up -d

# The Dockerfile now uses callbot.py as entry point
```

#### Testing
```bash
# Test the new structure
python test_structure.py

# Test full setup (requires dependencies)
python test_setup.py
```

### 7. Migration Notes

- ✅ All imports updated to use `src.` prefix
- ✅ All entry points updated
- ✅ Docker configuration updated
- ✅ Documentation updated
- ✅ Startup scripts updated
- ✅ Tests updated

### 8. Verification

The new structure has been tested and verified:

```bash
# Test structure (works without dependencies)
python test_structure.py

# Test full setup (requires dependencies installed)
python test_setup.py
```

## Summary

The CallBot project now has a clean, organized structure with:
- All Python source code in `src/` directory
- Multiple entry points for different use cases
- Updated imports and references throughout
- Maintained backward compatibility through entry point scripts
- Improved project organization and maintainability

The structure is now production-ready and follows Python packaging best practices. 