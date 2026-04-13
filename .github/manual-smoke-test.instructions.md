# Manual Smoke Test Checklist

Use this checklist after UI, data model, CSV, or preferences changes.

1. Launch app and verify `data/film_tracker.db` is created.
2. Add a collection and restart app to verify persistence.
3. Add multiple shots and verify they appear in the shot table.
4. Edit one shot and verify values update.
5. Delete a shot and verify removal.
6. Delete a collection and verify associated shots are removed.
7. Open Preferences from App -> Preferences and verify the dialog appears above the app window.
8. Set camera/lens presets using the Metadata Manage dialogs and verify they appear in the collection metadata dialog.
9. Verify that canceling Preferences does not persist staged preset edits.
10. Verify that saving Preferences persists staged preset edits.
11. Export a populated collection to CSV and verify row contents.
12. Import the CSV into another collection and verify inserted row count and conflict handling.
