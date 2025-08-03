# Docker Build Disk Space Solutions

## Problem
You're encountering "No space left on device" errors during Docker builds when installing packages. This is a common issue when building Docker images with many dependencies.

## Solutions

### 1. Immediate Fix - Clean Docker System
```bash
# Clean up Docker system
docker system prune -f
docker builder prune -f

# Check available disk space
df -h /
```

### 2. Use the Helper Script
```bash
# Make script executable (if not already)
chmod +x docker-build-helper.sh

# Clean Docker and build
./docker-build-helper.sh clean

# Or use optimized build
./docker-build-helper.sh optimized
```

### 3. Optimized Dockerfile Changes

The main Dockerfile has been optimized with:
- `--no-install-recommends` flag to reduce package size
- Aggressive cleanup of package caches
- Combined RUN commands to reduce layers
- Cache cleanup for pip

### 4. Multi-Stage Build (Dockerfile.optimized)

The `Dockerfile.optimized` uses multi-stage build to:
- Separate build dependencies from runtime dependencies
- Reduce final image size
- Minimize disk usage during build

### 5. Additional Solutions

#### A. Increase Docker Daemon Memory
```bash
# On macOS, increase Docker Desktop memory allocation
# Go to Docker Desktop > Settings > Resources > Advanced
# Increase memory limit to 8GB or more
```

#### B. Use BuildKit
```bash
# Enable BuildKit for better caching and memory management
export DOCKER_BUILDKIT=1
docker build --build-arg BUILDKIT_INLINE_CACHE=1 -t callbot .
```

#### C. Build with No Cache
```bash
# If you suspect cache corruption
docker build --no-cache -t callbot .
```

#### D. Use Alpine Linux Base (Alternative)
If the issues persist, consider using Alpine Linux:
```dockerfile
FROM python:3.9-alpine
# Note: Some packages might need different names on Alpine
```

### 6. System-Level Solutions

#### A. Check and Free Disk Space
```bash
# Check disk usage
df -h
du -sh /*

# Clean up system
sudo apt-get clean  # On Ubuntu/Debian
brew cleanup        # On macOS
```

#### B. Increase Docker Disk Image Size
```bash
# On macOS, increase Docker Desktop disk image size
# Go to Docker Desktop > Settings > Resources > Advanced
# Increase disk image size limit
```

### 7. Build Commands

#### Regular Build (Optimized)
```bash
docker build -t callbot .
```

#### Optimized Multi-Stage Build
```bash
docker build -f Dockerfile.optimized -t callbot-optimized .
```

#### Build with Helper Script
```bash
./docker-build-helper.sh clean
```

### 8. Troubleshooting

#### Check Build Context Size
```bash
# See what's being sent to Docker daemon
docker build --progress=plain -t callbot . 2>&1 | head -20
```

#### Monitor Disk Usage During Build
```bash
# In another terminal, monitor disk usage
watch -n 1 'df -h /'
```

#### Use Docker Build with Verbose Output
```bash
docker build --progress=plain --no-cache -t callbot .
```

## Recommended Approach

1. **First try**: Use the helper script with clean option
   ```bash
   ./docker-build-helper.sh clean
   ```

2. **If that fails**: Use the optimized multi-stage build
   ```bash
   ./docker-build-helper.sh optimized
   ```

3. **If still failing**: Clean Docker system and increase Docker Desktop resources

4. **Last resort**: Build with no cache and increased memory allocation

## Prevention

- Regularly clean Docker system: `docker system prune -f`
- Use `.dockerignore` to reduce build context
- Monitor disk space before builds
- Consider using multi-stage builds for complex applications

## File Changes Made

1. **Dockerfile**: Added `--no-install-recommends`, aggressive cleanup
2. **Dockerfile.optimized**: Multi-stage build for smaller final image
3. **docker-build-helper.sh**: Automated build management script
4. **.dockerignore**: Reduced build context size
5. **DOCKER_BUILD_SOLUTIONS.md**: This comprehensive guide 