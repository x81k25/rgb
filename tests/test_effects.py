"""Tests for OpenRGB Control effects and themes."""

import subprocess
import sys
import time
import signal
import pytest
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent
MAIN_PY = PROJECT_ROOT / "main.py"

# List of all static themes to test
STATIC_THEMES = ["cyan", "blue", "ocean", "wave", "status-gradient", "blackout"]

# List of all dynamic effects to test
DYNAMIC_EFFECTS = ["breathing", "wave", "rainbow", "pulse", "ocean", "ripple", "memory"]


class TestStaticThemes:
    """Test all static RGB themes."""
    
    @pytest.mark.parametrize("theme", STATIC_THEMES)
    def test_static_theme(self, theme):
        """Test that static theme executes without error and display for 3 seconds."""
        try:
            print(f"\n🎨 Testing static theme: '{theme}' - displaying for 3 seconds...")
            
            result = subprocess.run(
                [sys.executable, str(MAIN_PY), "theme", theme],
                capture_output=True,
                text=True,
                timeout=10,  # Static themes should complete quickly
                cwd=PROJECT_ROOT
            )
            
            # Check that the command completed successfully
            assert result.returncode == 0, f"Theme '{theme}' failed with stderr: {result.stderr}"
            
            # Check that there's some output (theme application message)
            assert result.stdout.strip(), f"Theme '{theme}' produced no output"
            
            print(f"✓ Theme '{theme}' applied successfully: {result.stdout.strip()}")
            
            # Display the theme for 3 seconds
            print(f"   Displaying '{theme}' theme for 3 seconds...")
            time.sleep(3)
            print(f"   ✓ '{theme}' display complete")
            
        except subprocess.TimeoutExpired:
            pytest.fail(f"Theme '{theme}' timed out after 10 seconds")
        except Exception as e:
            pytest.fail(f"Theme '{theme}' failed with exception: {e}")


class TestDynamicEffects:
    """Test all dynamic RGB effects."""
    
    @pytest.mark.parametrize("effect", DYNAMIC_EFFECTS)
    def test_dynamic_effect(self, effect):
        """Test that dynamic effect starts without error and display for 3 seconds."""
        process = None
        try:
            print(f"\n✨ Testing dynamic effect: '{effect}' - displaying for 3 seconds...")
            
            # Start the dynamic effect as a subprocess
            process = subprocess.Popen(
                [sys.executable, str(MAIN_PY), "effect", effect],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=PROJECT_ROOT
            )
            
            # Let it run for 1 second to ensure it starts properly
            time.sleep(1)
            
            # Check if process is still running (dynamic effects should continue)
            if process.poll() is not None:
                # Process has terminated, check if it was an error
                stdout, stderr = process.communicate()
                if process.returncode != 0:
                    pytest.fail(f"Effect '{effect}' terminated with error: {stderr}")
                else:
                    # Some effects might complete quickly, that's OK
                    print(f"✓ Effect '{effect}' completed normally")
                    time.sleep(2)  # Still wait to show any remaining effect
                    return
            
            print(f"✓ Effect '{effect}' started successfully")
            print(f"   Displaying '{effect}' effect for 3 seconds...")
            
            # Display the effect for 3 seconds (already waited 1 second, so wait 2 more)
            time.sleep(2)
            
            # Send SIGINT (Ctrl+C) to gracefully stop the effect
            process.send_signal(signal.SIGINT)
            
            # Wait for graceful shutdown (max 5 seconds)
            try:
                stdout, stderr = process.communicate(timeout=5)
                
                # Dynamic effects should handle SIGINT gracefully
                # They might exit with code 0 (graceful) or non-zero (interrupted)
                print(f"   ✓ '{effect}' display complete - stopped gracefully")
                
            except subprocess.TimeoutExpired:
                # Force kill if graceful shutdown failed
                process.kill()
                process.communicate()
                pytest.fail(f"Effect '{effect}' did not respond to interrupt signal")
                
        except Exception as e:
            if process and process.poll() is None:
                process.kill()
                process.communicate()
            pytest.fail(f"Effect '{effect}' failed with exception: {e}")
        
        finally:
            # Ensure process is cleaned up
            if process and process.poll() is None:
                process.kill()
                try:
                    process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    pass


class TestMainPyInterface:
    """Test the main.py command-line interface."""
    
    def test_list_themes(self):
        """Test that --list-themes works."""
        result = subprocess.run(
            [sys.executable, str(MAIN_PY), "--list-themes"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0, f"--list-themes failed: {result.stderr}"
        assert "Available themes:" in result.stdout
        
        # Check that all expected themes are listed
        for theme in STATIC_THEMES:
            assert theme in result.stdout, f"Theme '{theme}' not found in --list-themes output"
    
    def test_list_effects(self):
        """Test that --list-effects works."""
        result = subprocess.run(
            [sys.executable, str(MAIN_PY), "--list-effects"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode == 0, f"--list-effects failed: {result.stderr}"
        assert "Available effects:" in result.stdout
        
        # Check that all expected effects are listed
        for effect in DYNAMIC_EFFECTS:
            assert effect in result.stdout, f"Effect '{effect}' not found in --list-effects output"
    
    def test_invalid_theme(self):
        """Test that invalid theme names are handled properly."""
        result = subprocess.run(
            [sys.executable, str(MAIN_PY), "theme", "nonexistent"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode != 0, "Invalid theme should return non-zero exit code"
        assert "Error:" in result.stdout, "Should show error message for invalid theme"
    
    def test_invalid_effect(self):
        """Test that invalid effect names are handled properly."""
        result = subprocess.run(
            [sys.executable, str(MAIN_PY), "effect", "nonexistent"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=PROJECT_ROOT
        )
        
        assert result.returncode != 0, "Invalid effect should return non-zero exit code"
        assert "Unknown effect:" in result.stdout, "Should show error message for invalid effect"


if __name__ == "__main__":
    # Run tests directly if script is executed
    pytest.main([__file__, "-v"])