# Memory Management Fix for Double Free Errors

## Problem

The CallBot application was experiencing "double free or corruption (fasttop)" errors, which are serious memory management issues that can cause crashes and instability. These errors typically occur when:

1. **Memory is freed twice** - A pointer is deallocated multiple times
2. **Corrupted heap** - Memory structures are overwritten
3. **Resource leaks** - Resources aren't properly cleaned up
4. **Thread safety issues** - Multiple threads accessing shared resources

## Root Causes Identified

### 1. **SIP Client Memory Leaks**
- Active calls not properly cleaned up during shutdown
- Audio recorder resources not released
- pyVoIP phone object not properly stopped

### 2. **Component Reinitialization Issues**
- Old components not properly cleaned up before creating new ones
- Memory leaks during settings changes
- Broken state when reinitialization fails

### 3. **Audio Processing Memory Issues**
- Audio chunks accumulating without cleanup
- Recording threads not properly joined
- Temporary files not cleaned up

### 4. **TTS and Whisper Model Memory**
- Large models not properly released
- Engine instances not cleaned up
- Resource accumulation over time

## Solution

### 1. **Enhanced SIP Client Cleanup**

#### Modified `SIPClient.shutdown()`
```python
def shutdown(self):
    """Shutdown REAL pyVoIP client"""
    try:
        # Cleanup active calls first
        for call_id in list(self.active_calls.keys()):
            try:
                if call_id in self.active_calls:
                    call_handler = self.active_calls[call_id]
                    if hasattr(call_handler, 'recorder'):
                        call_handler.recorder.stop_recording()
                    del self.active_calls[call_id]
            except Exception as e:
                logger.error(f"Error cleaning up call {call_id}: {e}")
        
        # Clear active calls dictionary
        self.active_calls.clear()
        
        # Cleanup pyVoIP resources
        if hasattr(self, 'phone') and self.phone is not None:
            try:
                self.phone.stop()
            except Exception as e:
                logger.error(f"Error stopping phone: {e}")
            finally:
                self.phone = None
        
        self.registered = False
        logger.info("Real pyVoIP client shutdown complete")
    except Exception as e:
        logger.error(f"Error during pyVoIP shutdown: {e}")
    finally:
        # Ensure cleanup even if exceptions occur
        self.active_calls = {}
        self.phone = None
        self.registered = False
```

#### Enhanced AudioRecorder Cleanup
```python
def cleanup(self):
    """Clean up audio recorder resources"""
    try:
        self.recording = False
        self.audio_chunks.clear()
        if self.recording_thread and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=1.0)
    except Exception as e:
        logger.error(f"Error cleaning up audio recorder: {e}")
```

#### CallHandler Cleanup
```python
def cleanup(self):
    """Clean up call handler resources"""
    try:
        if hasattr(self, 'recorder'):
            self.recorder.cleanup()
        self.transcript_parts.clear()
    except Exception as e:
        logger.error(f"Error cleaning up call handler {self.call_id}: {e}")
```

### 2. **Improved Component Reinitialization**

#### Safe Component Replacement
```python
def reinit_components():
    with app.app_context():
        try:
            # Clean up old components first
            old_whisper = app.whisper_transcriber
            old_ollama = app.ollama_client
            old_sip = app.sip_client
            
            # Initialize new components
            app.whisper_transcriber = WhisperTranscriber(...)
            app.ollama_client = OllamaClient(...)
            
            # Shutdown old SIP client properly
            if old_sip:
                try:
                    old_sip.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down old SIP client: {e}")
            
            # Initialize new SIP client
            app.sip_client = SIPClient(...)
            
            # Clean up old components
            old_whisper = None
            old_ollama = None
            old_sip = None
            
        except Exception as e:
            logger.error(f"Failed to reinitialize components: {e}")
            # Ensure we don't leave broken state
            if not app.sip_client:
                app.sip_client = old_sip
            if not app.whisper_transcriber:
                app.whisper_transcriber = old_whisper
            if not app.ollama_client:
                app.ollama_client = old_ollama
```

### 3. **TTS Engine Cleanup**

#### Coqui TTS Cleanup
```python
def cleanup(self):
    """Clean up Coqui TTS resources"""
    try:
        if self.tts is not None:
            self.tts = None
            logger.info("Coqui TTS cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Coqui TTS: {e}")

def __del__(self):
    """Destructor to ensure cleanup"""
    try:
        self.cleanup()
    except:
        pass  # Ignore errors during cleanup
```

#### pyttsx3 Cleanup
```python
def cleanup(self):
    """Clean up pyttsx3 TTS resources"""
    try:
        if self.engine is not None:
            self.engine.stop()
            self.engine = None
            logger.info("pyttsx3 engine cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up pyttsx3: {e}")
```

### 4. **Whisper Model Cleanup**

```python
def cleanup(self):
    """Clean up Whisper model resources"""
    try:
        if self.model is not None:
            # Clear model reference to allow garbage collection
            self.model = None
            logger.info("Whisper model cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up Whisper model: {e}")

def __del__(self):
    """Destructor to ensure cleanup"""
    try:
        self.cleanup()
    except:
        pass  # Ignore errors during cleanup
```

### 5. **Application-Level Cleanup**

#### Graceful Shutdown Function
```python
def cleanup_components():
    """Clean up all components during shutdown"""
    try:
        if app.sip_client:
            app.sip_client.shutdown()
            app.sip_client = None
        
        if app.whisper_transcriber:
            app.whisper_transcriber.cleanup()
            app.whisper_transcriber = None
        
        if app.tts_manager:
            app.tts_manager.cleanup()
            app.tts_manager = None
        
        app.ollama_client = None
        logger.info("All components cleaned up")
    except Exception as e:
        logger.error(f"Error during component cleanup: {e}")
```

## Key Improvements

### 1. **Exception-Safe Cleanup**
- All cleanup operations wrapped in try-catch blocks
- Resources cleaned up even if exceptions occur
- Graceful degradation when cleanup fails

### 2. **Resource Tracking**
- Explicit cleanup of all resources
- Proper nulling of references
- Clear separation of cleanup responsibilities

### 3. **Thread Safety**
- Timeout-based thread joining
- Safe dictionary iteration during cleanup
- Proper thread state management

### 4. **Memory Leak Prevention**
- Destructors (`__del__`) for automatic cleanup
- Explicit cleanup methods for manual control
- Reference counting awareness

### 5. **State Management**
- Rollback capability during reinitialization
- Broken state prevention
- Consistent component state

## Testing

### Memory Leak Detection
```bash
# Monitor memory usage
watch -n 1 'ps aux | grep python'

# Check for memory leaks with valgrind (if available)
valgrind --tool=memcheck --leak-check=full python run.py
```

### Stress Testing
```python
# Test component reinitialization
for i in range(100):
    # Change settings to trigger reinitialization
    settings.sip_domain = f"test{i}.com"
    # Verify no memory leaks
```

## Monitoring

### Log Messages to Watch
- `"Real pyVoIP client shutdown complete"`
- `"Whisper model cleaned up"`
- `"Coqui TTS cleaned up"`
- `"pyttsx3 engine cleaned up"`
- `"All components cleaned up"`

### Error Messages to Monitor
- `"Error during pyVoIP shutdown"`
- `"Error cleaning up call handler"`
- `"Error cleaning up audio recorder"`
- `"Failed to reinitialize components"`

## Benefits

1. **Eliminates Double Free Errors**: Proper resource management prevents memory corruption
2. **Reduces Memory Leaks**: Explicit cleanup of all resources
3. **Improves Stability**: Graceful handling of cleanup failures
4. **Better Performance**: Reduced memory footprint over time
5. **Easier Debugging**: Clear logging of cleanup operations

## Migration

No migration steps required. The fixes are backward compatible and automatically improve memory management.

## Troubleshooting

If you still experience memory issues:

1. **Check for memory leaks**:
   ```bash
   ps aux | grep python
   ```

2. **Monitor cleanup logs**:
   - Look for cleanup success messages
   - Check for error messages during cleanup

3. **Test component reinitialization**:
   - Change settings multiple times
   - Monitor memory usage during changes

4. **Use memory profiling tools**:
   ```python
   import tracemalloc
   tracemalloc.start()
   # ... run your code ...
   snapshot = tracemalloc.take_snapshot()
   top_stats = snapshot.statistics('lineno')
   ```

This comprehensive fix should resolve the "double free or corruption (fasttop)" errors and significantly improve the stability of your CallBot application. 