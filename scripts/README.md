# MIDI Mapper Scripts

This directory contains executable scripts that can be triggered by MIDI bindings.

## Security

For security reasons, only scripts located in this directory (or subdirectories) can be executed by the MIDI Mapper. The `command_root` setting in the database controls this path.

## Creating Your Own Scripts

1. Create a new script file in this directory
2. Make it executable: `chmod +x your-script.sh`
3. Reference it in a binding command (e.g., `./scripts/your-script.sh` or just `your-script.sh`)

## Example Script

See `test-command.sh` for a simple example that logs when it's executed.

## Common Use Cases

- Launching applications
- Controlling media playback
- Running system commands
- Triggering automation workflows
- Recording audio/video
- Switching workspaces

## Tips

- Scripts run in the background and don't block MIDI processing
- Use the debounce_ms setting to prevent accidental multiple triggers
- Check the backend logs for any script execution errors
- Test your scripts manually before binding them to MIDI notes
