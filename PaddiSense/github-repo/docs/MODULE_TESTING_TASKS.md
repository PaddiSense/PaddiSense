# Module Management Testing Tasks

Status as of 2026-02-07

## Completed Tasks (12/21)

- [x] #1 - Test PaddiSense Manager Card UI
- [x] #2 - Test module install flow - pre-checks
- [x] #3 - Test module install - file operations
- [x] #6 - Test module removal - pre-checks
- [x] #7 - Test module removal - file operations
- [x] #13 - Test module dependencies
- [x] #14 - Review install_module service implementation
- [x] #15 - Review remove_module service implementation
- [x] #17 - Test each module: HFM install/remove
- [x] #18 - Test each module: STR install/remove
- [x] #21 - Document module management process

## Remaining Tasks (9/21)

These tasks require Home Assistant restart to test properly:

### HA Integration Testing
- [ ] #4 - Test module install - HA integration
  - Verify entities load correctly after install
  - Check automations are registered
  - Confirm sensors have correct attributes

- [ ] #5 - Test module install - Manager Card updates
  - Verify card shows module in "Installed" section
  - Check version display is correct
  - Confirm Remove button appears

- [ ] #8 - Test module removal - HA cleanup
  - Verify entities are removed after uninstall
  - Check automations are unregistered
  - Confirm no orphaned states

- [ ] #9 - Test module removal - Manager Card updates
  - Verify card shows module in "Available" section
  - Confirm Install button appears
  - Check dependency warnings display correctly

### Data Preservation
- [ ] #10 - Test reinstall after removal
  - Remove a module with data
  - Verify local_data preserved
  - Reinstall and confirm data restored

### Error Handling
- [ ] #11 - Test error handling - install failures
  - Simulate YAML syntax error
  - Verify rollback occurs
  - Check error notification displayed

- [ ] #12 - Test error handling - removal failures
  - Simulate file permission issue
  - Verify partial removal handled
  - Check recovery path works

### Individual Module Testing
- [ ] #16 - Test each module: IPM install/remove
  - Full install cycle
  - Verify dashboard appears
  - Test product sensor
  - Full remove cycle
  - Verify data preserved

- [ ] #19 - Test each module: RTR install/remove
  - Full install cycle
  - Verify dashboard appears
  - Test RTR sensor
  - Full remove cycle

- [ ] #20 - Test each module: Weather install/remove
  - Full install cycle
  - Verify dashboard appears
  - Test weather entities
  - Full remove cycle

## Testing Procedure

1. Start from PaddiSense Manager dashboard
2. For install: Click Install → Confirm → Wait for HA restart
3. Verify dashboard appears in sidebar
4. Check entities in Developer Tools → States
5. For remove: Click Remove → Confirm → Wait for HA restart
6. Verify dashboard removed from sidebar
7. Check entities removed from States

## Notes

- All file-level validations passed
- Dependency system implemented and tested (HFM requires IPM)
- Documentation complete in MODULE_MANAGEMENT.md
- Manager Card v1.3.0 includes dependency blocking UI
